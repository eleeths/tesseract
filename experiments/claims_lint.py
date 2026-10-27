#!/usr/bin/env python3
"""TESSERACT claims lint (U15) — 0 model calls, stdlib only, read-only.

Scans submission/, dashboard/, fleet/*.md, and generated report Markdown
for risky overstatement patterns, with an allowlist for negations,
labels, and the binding verbatim sentence. NEVER edits the scanned
files: a genuine overstatement is REPORTED (file, line, text) for the
coordinator to adjudicate — silencing the lint by rewriting submission
text without a coordinator decision is forbidden.

Risky patterns (case-insensitive; a hit is a violation UNLESS an
allowlist rule below clears it):
  pretrained | live swarm | swarm wins | Blue learned to win |
  reliably + verb | guaranteed | real customers | revenue |
  worldwide clones | trained weights | fully automated loop
  (+ bare "automated loop" without the human-gate words nearby).
Plus two structural checks:
  combined-label: a report using combined-arm numbers must carry the
    words "mechanical replay" in the same file.
  payout-basis: payout text must not cite the combined arm as the
    payout basis (a combined mention in payout context is a violation
    unless the same block says the combined arm is excluded).

Allowlist (each hit is still PRINTED with its classification so the
coordinator can adjudicate):
  - qualified-pretrained: the block carries "recipe pre-loaded" AND
    "no weight training".
  - shorthand-in-file: bare "pretrained" where the same file carries
    the full qualifier (mode-label shorthand, qualifier present).
  - field-name: JSON keys / code string literals named "pretrained"
    (e.g. `"pretrained":`, mode == "pretrained") are field names,
    not claims.
  - negation: the block carries never/not/no/none/without/n't,
    "Banned lines", or equivalent — "We do not claim ...", "never ...",
    "NOT reliably", "not customers, revenue, or orders" all pass.
  - binding-sentence: the verbatim line "distilled into rules the
    whole fleet loads" passes.
  - labelled-synthetic: blocks carrying SYNTHETIC SCRIPTED /
    SIMULATED / mechanical replay / SCENARIO / PROPOSED / ASSUMPTION
    pass for the pattern they label (they are the required labels).
  - human-gate: "automated loop" passes only when the same block
    names the human lesson-approval gate (human/approval/gate).
  - payout-excluded: payout + combined passes only with an explicit
    exclusion in the same block: "exclud..." (combined arm excluded
    from payouts) OR "never the combined arm" (per-wave artifacts
    only, never the combined arm). Both wordings unambiguously deny
    the combined arm as the payout basis.

Every hit prints: file + line + classification (violation vs
allowlisted + reason). Exit 0 with --strict only when zero violations
remain; without --strict, violations are reported but exit stays 0
(adjudication mode).

Usage:
    python3 experiments/claims_lint.py submission dashboard fleet --strict
    (paths are files or dirs; relative paths resolve against the repo
    root. Dirs contribute *.md recursively, plus *.py under dashboard/
    for user-facing panel strings. *.json data files are never claims
    and are skipped.)
"""
import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BINDING_FRAGMENT = "distilled into rules the whole fleet loads"
QUALIFIER_A = "recipe pre-loaded"
QUALIFIER_B = "no weight training"

# (pattern-name, compiled regex). All case-insensitive.
RISKY = [
    ("pretrained", re.compile(r"\bpretrain\w*", re.IGNORECASE)),
    ("live swarm", re.compile(r"\blive[-\s]?swarm", re.IGNORECASE)),
    ("swarm wins", re.compile(r"\bswarm\s+wins?\b", re.IGNORECASE)),
    ("Blue learned to win",
     re.compile(r"\bblue\s+(learned|learns|learnt|has\s+learned)\s+to\s+win",
                re.IGNORECASE)),
    ("reliably defends",
     re.compile(r"\breliab\w*\s+[a-z]+", re.IGNORECASE)),
    ("guaranteed", re.compile(r"\bguarantee\w*", re.IGNORECASE)),
    ("real customers", re.compile(r"\breal\s+customers?", re.IGNORECASE)),
    ("revenue", re.compile(r"\brevenue\b", re.IGNORECASE)),
    ("worldwide clones",
     re.compile(r"\bworldwide\s+clones?", re.IGNORECASE)),
    ("trained weights",
     re.compile(r"\btrained\s+weights?", re.IGNORECASE)),
    ("fully automated loop",
     re.compile(r"\b(fully\s+)?automated\s+loop", re.IGNORECASE)),
    # Round-4 marketplace patterns: the executor never learns/adapts
    # (it deterministically executes rules); real-money / live-market
    # words must always be negated; held results must never be
    # percentages.
    ("executor learns",
     re.compile(r"\bexecutor\s+(learns?|learnt|learned|adapts?|adapted)\b",
                re.IGNORECASE)),
    ("real USDC", re.compile(r"\breal\s+USDC\b", re.IGNORECASE)),
    ("live marketplace",
     re.compile(r"\blive\s+marketplace\b", re.IGNORECASE)),
    ("mainnet", re.compile(r"\bmainnet\b", re.IGNORECASE)),
    ("held percentage",
     re.compile(r"\bheld\b[^.\n]{0,40}\d+\s*%|\d+\s*%\s+held\b",
                re.IGNORECASE)),
]

NEGATION_RE = re.compile(
    r"\b(never|not|no|none|without|banned|cannot|can't|don't|doesn't|"
    r"isn't|aren't|wasn't|weren't|won't|n't|false|myth)\b"
    r"|never say|do not claim|we do not",
    re.IGNORECASE)
LABEL_RE = re.compile(
    r"SYNTHETIC SCRIPTED|SIMULATED|mechanical replay|SCENARIO|PROPOSED|"
    r"ASSUMPTION|DEMO-MODE|demo-mode|no live|not live|NOT LIVE|"
    r"NOT PAID|LEDGER UNCHANGED|open-loop",
    re.IGNORECASE)
GATE_RE = re.compile(r"human|approval|gate", re.IGNORECASE)
FIELD_KEY_RE = re.compile(r"""["']pretrain\w*["']\s*:|:\s*["']pretrain\w*["']"""
                           r"""|==\s*["']pretrain\w*["']"""
                           r"""|["']pretrain\w*["']\s*[,}\]]""")
PAYOUT_RE = re.compile(r"payout|per wave|paid\b", re.IGNORECASE)


def split_blocks(text):
    """Paragraph blocks (blank-line separated) with 1-based line spans."""
    blocks = []
    start = None
    buf = []
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        if line.strip():
            if start is None:
                start = i
            buf.append(line)
        else:
            if buf:
                blocks.append((start, i - 1, "\n".join(buf)))
                buf = []
                start = None
    if buf:
        blocks.append((start, len(lines), "\n".join(buf)))
    return blocks


def classify(name, match_text, block, line, whole_file):
    """Return (classification, reason). classification is 'violation'
    or 'allowlisted'."""
    low_block = block.lower()
    if BINDING_FRAGMENT in line:
        return ("allowlisted", "binding verbatim sentence")
    if name == "pretrained":
        if QUALIFIER_A in low_block and QUALIFIER_B in low_block:
            return ("allowlisted", "qualified: recipe pre-loaded, "
                    "no weight training")
        if FIELD_KEY_RE.search(line):
            return ("allowlisted", 'field name / code literal, not a claim')
        low_file = whole_file.lower()
        if QUALIFIER_A in low_file and QUALIFIER_B in low_file:
            return ("allowlisted", "mode-label shorthand; full qualifier "
                    "present in file")
    if name == "fully automated loop" and GATE_RE.search(block):
        return ("allowlisted", "human lesson-approval gate named in block")
    if NEGATION_RE.search(block):
        return ("allowlisted", "negation / banned-lines context")
    if LABEL_RE.search(block) and name not in (
            "pretrained", "revenue", "fully automated loop",
            "real USDC", "live marketplace", "mainnet"):
        return ("allowlisted", "required label present in block")
    if LABEL_RE.search(block) and name in (
            "revenue", "real USDC", "live marketplace", "mainnet"):
        # "assumptions only — not customers, revenue" style labels still
        # need the negation; a bare label is not enough for money words.
        if NEGATION_RE.search(block):
            return ("allowlisted", "negation / assumption label")
    return ("violation", "unqualified risky wording")


def lint_text(text, path="<string>"):
    """Lint one document. Returns a list of finding dicts with keys:
    file, line, pattern, classification, reason, excerpt."""
    findings = []
    for start, _end, block in split_blocks(text):
        lines = block.split("\n")
        for name, rx in RISKY:
            for m in rx.finditer(block):
                # 1-based line of the match start within the file.
                lineno = start + block[:m.start()].count("\n")
                line_text = lines[block[:m.start()].count("\n")]
                cls, reason = classify(name, m.group(0), block,
                                       line_text, text)
                findings.append({
                    "file": path,
                    "line": lineno,
                    "pattern": name,
                    "classification": cls,
                    "reason": reason,
                    "excerpt": line_text.strip()[:160],
                })
    # Structural: combined-arm numbers require the mechanical-replay label
    # somewhere in the same file. Match the word "combined" (the arm
    # name), not the substring "combin": the verb "combines" (as in "no
    # ancestor combines ... in one system") is not the combined arm and
    # must not trip this check (STATUS.md false positive, round 4).
    if "combined" in text.lower():
        markers = ("red moves" in text.lower()
                   or "moves total" in text.lower()
                   or "trust final" in text.lower()
                   or "detections=" in text
                   or "outcome=" in text
                   or "exfil attempted=" in text)
        if markers and "mechanical replay" not in text.lower():
            lineno = next(
                (i for i, l in enumerate(text.splitlines(), start=1)
                 if "combined" in l.lower()), 1)
            findings.append({
                "file": path,
                "line": lineno,
                "pattern": "combined without mechanical-replay label",
                "classification": "violation",
                "reason": "page/report uses combined-arm numbers but "
                          "carries no 'mechanical replay' label",
                "excerpt": "combined-arm numbers present; "
                           "'mechanical replay' absent",
            })
    # Round-4 structural: a marketplace hold must never be presented as
    # a U11/U12 live-trial result. A block that mentions the
    # marketplace together with U11/U12 and a held count is a
    # violation unless it states the separation (separately, never
    # merged, not included, apart, different configuration).
    for start, _end, block in split_blocks(text):
        low = block.lower()
        if ("marketplace" in low and ("u11" in low or "u12" in low)
                and "held" in low
                and not any(w in low for w in (
                    "separat", "never merged", "not included",
                    "not merged", "apart", "different configuration",
                    "kept out", "not part of"))):
            findings.append({
                "file": path,
                "line": start,
                "pattern": "marketplace hold as live trial",
                "classification": "violation",
                "reason": "marketplace held result mentioned with U11/U12 "
                          "without stating the separation",
                "excerpt": block.split("\n")[0].strip()[:160],
            })
    # Structural: payout text must not cite the combined arm as basis.
    for start, _end, block in split_blocks(text):
        low = block.lower()
        if PAYOUT_RE.search(block) and "combined" in low \
                and "exclud" not in low \
                and "never the combined arm" not in low:
            lineno = start
            findings.append({
                "file": path,
                "line": lineno,
                "pattern": "payout cites combined arm",
                "classification": "violation",
                "reason": "payout context mentions the combined arm "
                          "without excluding it as the payout basis",
                "excerpt": block.split("\n")[0].strip()[:160],
            })
    findings.sort(key=lambda f: (f["file"], f["line"], f["pattern"]))
    return findings


def collect_files(roots):
    """Expand CLI roots to scanned files: *.md everywhere (recursive),
    *.py only under dashboard/ (user-facing panel strings). *.json and
    everything else is skipped (data, not claims)."""
    files = []
    for root in roots:
        path = root if os.path.isabs(root) else os.path.join(REPO_ROOT, root)
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for dirpath, _dirnames, filenames in os.walk(path):
                for name in sorted(filenames):
                    full = os.path.join(dirpath, name)
                    if name.endswith(".md"):
                        files.append(full)
                    elif name.endswith(".py") and os.path.basename(
                            os.path.abspath(path)) == "dashboard":
                        # Only dashboard .py (panel strings); other dirs'
                        # .py is code, not claims text.
                        rel = os.path.relpath(full, REPO_ROOT)
                        if rel.split(os.sep)[0] == "dashboard":
                            files.append(full)
        else:
            print("claims_lint WARNING: path not found: %s" % root,
                  file=sys.stderr)
    return sorted(set(files))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+",
                    help="files/dirs to scan (e.g. submission dashboard "
                         "fleet)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when any violation remains (for "
                         "verify_all.py); without it, report only")
    args = ap.parse_args(argv)
    files = collect_files(args.paths)
    if not files:
        print("claims_lint FAILED: no scannable files", file=sys.stderr)
        return 1
    all_findings = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            print("claims_lint WARNING: cannot read %s: %s" % (path, exc),
                  file=sys.stderr)
            continue
        rel = os.path.relpath(path, REPO_ROOT)
        all_findings.extend(lint_text(text, rel))
    violations = [f for f in all_findings
                  if f["classification"] == "violation"]
    allowed = [f for f in all_findings
               if f["classification"] == "allowlisted"]
    for f in all_findings:
        print("%s:%d: [%s] %s (%s): %s" % (
            f["file"], f["line"], f["classification"].upper(), f["pattern"],
            f["reason"], f["excerpt"]))
    print("claims_lint: files=%d hits=%d allowlisted=%d violations=%d" % (
        len(files), len(all_findings), len(allowed), len(violations)))
    if violations:
        print("claims_lint: VIOLATIONS PRESENT — coordinator adjudicates "
              "(fix the text, or refine the allowlist for a false "
              "positive). Scanned files were NOT modified.")
    else:
        print("claims_lint: CLEAN — no unqualified claims; scanned files "
              "were NOT modified.")
    if args.strict and violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
