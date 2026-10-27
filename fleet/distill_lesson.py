#!/usr/bin/env python3
"""Deterministic lesson distiller (U6, extended U13) — 0 model calls.

Single mode (U6, unchanged): reads one playbook.json (ranked_defenses +
gaps) and writes a CANDIDATE lesson in the lessons.json schema to
fleet/candidates/candidate-<run>.json.

Batch mode (U13): walks the INSIDE-OUT Analyst playbooks already
present in the project's run artifacts (runs/**/playbook.json), maps
every ranked defense to either a candidate rule in lessons schema or
UNMAPPED with the original text preserved, merges the U9 trap-discipline
rule as a SCOREBOARD-sourced candidate (never attributed to the
Analyst), and writes fleet/lesson_candidates/lesson-2.candidate.json
plus fleet/lesson_candidates/LESSON-2-APPROVAL.md. Direction scope is
deliberate, not an oversight: pooling inside-out and outside-in Analyst
defenses into one candidate without a direction column would hide which
direction each rule came from, so outside-in playbooks are EXCLUDED from
this corpus and listed in the candidate as
excluded_direction_playbooks (a separate outside-in distillation, if
ever built, gets its own candidate). The U13 exact-reproduction claim
(24 defenses, 11 unmapped) holds for the inside-out corpus only.

Mapping is mechanical, never invented (shared by both modes):
- defense names ARE engine action names (the Analyst writes them that
  way); args are parsed from the defense's own evidence strings.
- a defense whose args cannot be parsed, or whose name is not a known
  engine action, becomes a rule with action "UNMAPPED" and is EXCLUDED
  from any opening recipe. It is counted, never guessed.
- gaps become limits material.

Provenance (U13): every batch candidate rule carries a provenance
OBJECT; the distiller REJECTS (nonzero exit, no output) any candidate
lacking one:
- source_type "analyst_ranked_defense": run/playbook identifier + rank.
- source_type "scoreboard_finding": the trap-discipline candidate with
  metric trap_overwritten=4/5 briefed runs and the scoreboard artifact.

HUMAN APPROVAL GATE: this tool NEVER writes fleet/lessons.json (any
--out resolving to it is refused). Batch mode additionally asserts the
production lessons file hash is identical before and after the run.
Promoting lesson-2 is manual: the coordinator signs
LESSON-2-APPROVAL.md (approved_by / approved_at). Unsigned means the
fleet default stays lesson-1 everywhere.

Usage:
    python3 fleet/distill_lesson.py --playbook runs/learn-round3/playbook.json
    python3 fleet/distill_lesson.py --playbook runs/X/playbook.json --force
    python3 fleet/distill_lesson.py --batch --out /tmp/tesseract-lesson2
    python3 fleet/distill_lesson.py --batch   # writes fleet/lesson_candidates/
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLEET = os.path.join(HERE, "fleet")
RUNS_DIR = os.path.join(HERE, "runs")
LESSONS_PATH = os.path.join(FLEET, "lessons.json")
TRAP_CANDIDATE_PATH = os.path.join(FLEET, "trap_discipline.candidate.json")
BATCH_DEFAULT_OUT = os.path.join(FLEET, "lesson_candidates")
CANDIDATE_NAME = "lesson-2.candidate.json"
APPROVAL_NAME = "LESSON-2-APPROVAL.md"

KNOWN_ACTIONS = {
    "set_overseer_policy", "brief_overseer", "add_detection",
    "rotate_creds", "patch_rule", "isolate_layer", "inspect_logs",
}

ALLOWED_SOURCE_TYPES = ("analyst_ranked_defense", "scoreboard_finding")
SCOREBOARD_ARTIFACT = "experiments/scoreboard.json"
TRAP_METRIC = "trap_overwritten=4/5 briefed runs"


def parse_args_for(defense, evidence):
    """Derive engine args from a defense's evidence strings, or None."""
    text = " ".join(evidence or [])
    if defense == "set_overseer_policy":
        if "strict" in text:
            return {"policy": "strict"}
        return None
    if defense in ("brief_overseer", "rotate_creds", "isolate_layer",
                   "inspect_logs"):
        return {}
    if defense == "add_detection":
        m = re.search(r"keyword:\s*(\S+)", text)
        return {"keyword": m.group(1)} if m else None
    if defense == "patch_rule":
        m = re.search(r"\bL([12])\b", text)
        return {"layer": int(m.group(1))} if m else None
    return None


def normalize_evidence(evidence):
    """Evidence as a list of strings; a lone string becomes one entry."""
    if evidence is None:
        return []
    if isinstance(evidence, str):
        return [evidence]
    if isinstance(evidence, list):
        return [e if isinstance(e, str) else json.dumps(e, sort_keys=True)
                for e in evidence]
    return [str(evidence)]


def distill_entry(defense, evidence):
    """Shared mechanical mapping: (action, args, is_unmapped). Never guesses."""
    parsed = (parse_args_for(defense, evidence)
              if defense in KNOWN_ACTIONS else None)
    if defense in KNOWN_ACTIONS and parsed is not None:
        return defense, parsed, False
    return "UNMAPPED", {}, True


def validate_provenance(rule):
    """Problems with a candidate rule's provenance object (empty = valid)."""
    problems = []
    prov = rule.get("provenance")
    if not isinstance(prov, dict):
        return [f"rule {rule.get('id')}: missing provenance object"]
    source_type = prov.get("source_type")
    if source_type not in ALLOWED_SOURCE_TYPES:
        problems.append(
            f"rule {rule.get('id')}: bad source_type {source_type!r}")
        return problems
    if source_type == "analyst_ranked_defense":
        for key in ("run", "playbook", "rank"):
            if prov.get(key) in (None, ""):
                problems.append(
                    f"rule {rule.get('id')}: analyst provenance missing {key!r}")
    else:
        for key in ("metric", "artifact"):
            if prov.get(key) in (None, ""):
                problems.append(
                    f"rule {rule.get('id')}: scoreboard provenance missing {key!r}")
    return problems


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_playbooks(runs_dir=None):
    """All runs/**/playbook.json paths, sorted. Run id is the dir path
    under runs/ (e.g. 'learn-round3', or 'loop-.../duel' for nested)."""
    runs_dir = os.path.abspath(runs_dir or RUNS_DIR)
    found = []
    for root, _dirs, files in os.walk(runs_dir):
        if "playbook.json" in files:
            found.append(os.path.join(root, "playbook.json"))
    found.sort()
    return found


def run_id_for(playbook_path, runs_dir=None):
    rel = os.path.relpath(os.path.abspath(playbook_path),
                          os.path.abspath(runs_dir or RUNS_DIR))
    run_id = os.path.dirname(rel).replace(os.sep, "/") or rel
    return run_id


def run_direction(run_id, runs_dir=None):
    """Direction of a run's duel, from its summary.json.

    Legacy runs (no summary.json, or no direction field) default to
    inside-out — every pre-outside-in run was inside-out. Used to keep
    the batch corpus direction-pure: outside-in playbooks are excluded
    from the inside-out lesson-2 candidate, never silently pooled.
    """
    summary_path = os.path.join(
        os.path.abspath(runs_dir or RUNS_DIR), run_id, "summary.json")
    try:
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)
    except (OSError, ValueError):
        return "inside-out"
    direction = summary.get("direction")
    return direction if direction in ("inside-out", "outside-in") else "inside-out"


def distill_playbook(playbook_path, runs_dir=None):
    """Distill one playbook file. Returns (run_id, rules, mapped, unmapped)."""
    run_id = run_id_for(playbook_path, runs_dir)
    rel = os.path.relpath(os.path.abspath(playbook_path), HERE)
    with open(playbook_path, encoding="utf-8") as f:
        playbook = json.load(f)
    ranked = playbook.get("ranked_defenses") or []
    rules = []
    mapped = 0
    unmapped = 0
    for i, entry in enumerate(ranked, start=1):
        defense = entry.get("defense", "") if isinstance(entry, dict) else ""
        evidence = normalize_evidence(
            entry.get("evidence") if isinstance(entry, dict) else None)
        action, args, is_unmapped = distill_entry(defense, evidence)
        if is_unmapped:
            unmapped += 1
            rules.append({
                "id": None,  # numbered by the batch pass (L2-C<n>)
                "trigger": defense,
                "action": "UNMAPPED",
                "effect": ("UNMAPPED — no mechanical mapping exists; human "
                           "mapping required; original text preserved"),
                "evidence": evidence,
                "unmapped_reason": (
                    "defense name is not a known engine action, or its args "
                    "could not be parsed from its own evidence; not guessed"),
                "provenance": {
                    "source_type": "analyst_ranked_defense",
                    "run": run_id,
                    "playbook": rel,
                    "rank": i,
                },
            })
        else:
            mapped += 1
            rules.append({
                "id": None,  # numbered by the batch pass (L2-C<n>)
                "trigger": defense,
                "action": action,
                "args": args,
                "effect": ("candidate — derived deterministically from "
                           "playbook, unreviewed"),
                "evidence": evidence,
                "provenance": {
                    "source_type": "analyst_ranked_defense",
                    "run": run_id,
                    "playbook": rel,
                    "rank": i,
                },
            })
    return run_id, rules, mapped, unmapped


def load_trap_rule():
    """U9 trap-discipline candidate as a SCOREBOARD-sourced rule.

    Merged, never attributed to the Analyst: the recorded trap finding
    is scoreboard evidence (overwritten in 4 of 5 briefed runs), and no
    Analyst artifact is claimed to have named it.
    """
    with open(TRAP_CANDIDATE_PATH, encoding="utf-8") as f:
        trap = json.load(f)
    return {
        "id": "R8-CANDIDATE",
        "trigger": trap.get("trigger", "own trap is armed"),
        "action": trap.get("action",
                           "do_not_set_trap_until_trap_fired_or_consumed"),
        "effect": ("candidate — do not set another trap while your own "
                   "trap is armed; awaiting coordinator approval, "
                   "NOT fleet-deployed"),
        "evidence": [trap.get("evidence",
                              "scoreboard: trap overwritten in 4/5 briefed runs")],
        "applies_to_lessons": trap.get("applies_to_lessons", ["lesson-1"]),
        "status": trap.get("status", "awaiting_coordinator_approval"),
        "provenance": {
            "source_type": "scoreboard_finding",
            "metric": TRAP_METRIC,
            "artifact": SCOREBOARD_ARTIFACT,
        },
    }


def batch_distill(runs_dir=None):
    """Distill the INSIDE-OUT Analyst playbooks. Returns (candidate, approval_md).

    Outside-in playbooks are excluded (listed, never pooled): see the
    module docstring. The exclusion keeps the U13 candidate's
    exact-reproduction claim (24 defenses, 11 unmapped) intact.
    """
    playbook_paths = discover_playbooks(runs_dir)
    per_playbook = []
    rules = []
    mapping_counts = {}
    total_mapped = 0
    total_unmapped = 0
    skipped = []
    excluded = []
    counter = 0
    for path in playbook_paths:
        run_id_peek = run_id_for(path, runs_dir)
        direction_peek = run_direction(run_id_peek, runs_dir)
        if direction_peek != "inside-out":
            excluded.append({
                "run": run_id_peek,
                "playbook": os.path.relpath(os.path.abspath(path), HERE),
                "direction": direction_peek,
                "reason": ("outside-in playbook excluded from the "
                           "inside-out lesson-2 candidate; directions are "
                           "never pooled in one candidate"),
            })
            continue
        run_id, prules, mapped, unmapped = distill_playbook(path, runs_dir)
        total = mapped + unmapped
        if total == 0:
            skipped.append({
                "run": run_id,
                "playbook": os.path.relpath(os.path.abspath(path), HERE),
                "reason": "no ranked_defenses (mock stub, not an Analyst playbook)",
            })
            continue
        for rule in prules:
            counter += 1
            rule["id"] = f"L2-C{counter}"
            target = rule["action"]
            mapping_counts[target] = mapping_counts.get(target, 0) + 1
            rules.append(rule)
        total_mapped += mapped
        total_unmapped += unmapped
        per_playbook.append({
            "run": run_id,
            "playbook": os.path.relpath(os.path.abspath(path), HERE),
            "defenses": total,
            "mapped": mapped,
            "unmapped": unmapped,
            "unmapped_rate": unmapped / total if total else None,
        })
    trap_rule = load_trap_rule()
    rules.append(trap_rule)
    mapping_counts[trap_rule["action"]] = (
        mapping_counts.get(trap_rule["action"], 0) + 1)
    total = total_mapped + total_unmapped
    candidate = {
        "lesson_id": "lesson-2-candidate",
        "name": ("Candidate distilled from inside-out Analyst playbooks "
                 "(UNREVIEWED)"),
        "status": ("candidate — human approval required before it becomes "
                   "a lesson; NOT fleet-deployed"),
        "simulated": True,
        "description": ("Deterministic batch distill of every INSIDE-OUT "
                        "Analyst playbook's ranked defenses into lesson "
                        "schema, plus the scoreboard-sourced trap-discipline "
                        "candidate. No model call was made. UNMAPPED rules "
                        "need a human mapping; fleet default stays lesson-1 "
                        "until the coordinator signs LESSON-2-APPROVAL.md. "
                        "Outside-in playbooks are excluded (see "
                        "excluded_direction_playbooks) and never pooled "
                        "into this candidate."),
        "sources": [{"run": p["run"], "playbook": p["playbook"]}
                    for p in per_playbook],
        "skipped_playbooks": skipped,
        "excluded_direction_playbooks": excluded,
        "opening_recipe": [],
        "recipe_note": ("No opening recipe is proposed: the batch spans "
                        "several playbooks with conflicting orders and a "
                        "high unmapped rate. A human assigns the recipe on "
                        "promotion."),
        "rules": rules,
        "trap_rule_note": ("R8-CANDIDATE is merged from "
                           "fleet/trap_discipline.candidate.json as a "
                           "scoreboard finding, NOT attributed to the "
                           "Analyst."),
        "mapping_counts": mapping_counts,
        "unmapped_by_playbook": [
            {"run": p["run"], "defenses": p["defenses"],
             "unmapped": p["unmapped"],
             "unmapped_rate": p["unmapped_rate"]}
            for p in per_playbook
        ],
        "unmapped_count": total_unmapped,
        "mapped_count": total_mapped,
        "analyst_defenses": total,
        "unmapped_overall_rate": (total_unmapped / total
                                  if total else None),
        "limits": ["Batch distill inherits every source playbook's gaps; "
                   "see the individual playbook.json files."],
        "distribution": None,
    }
    problems = []
    for rule in rules:
        problems.extend(validate_provenance(rule))
    if problems:
        raise ValueError("candidate rejected — provenance problems:\n"
                         + "\n".join(problems))
    approval = render_approval(candidate, per_playbook, skipped, excluded)
    return candidate, approval


def render_approval(candidate, per_playbook, skipped, excluded=None):
    """Coordinator checklist. No timestamps: output is deterministic."""
    lines = [
        "# LESSON-2 CANDIDATE — COORDINATOR APPROVAL CHECKLIST",
        "",
        "Status: CANDIDATE — NOT DEPLOYED. The fleet default stays lesson-1",
        "everywhere until this file is signed. Never present lesson-2, trap",
        "discipline R8, or any candidate rule as fleet-deployed or effective",
        "until the coordinator signs below AND a named test has run against it.",
        "",
        "## 1. Candidate diff summary",
        "",
        f"Rules: {len(candidate['rules'])} "
        f"({len(candidate['rules']) - 1} from Analyst playbooks + "
        "1 scoreboard-sourced trap rule R8-CANDIDATE).",
        f"Mapping counts: {json.dumps(candidate['mapping_counts'], sort_keys=True)}.",
        "Opening recipe: none proposed (see recipe_note in the candidate).",
        "Skipped (not Analyst playbooks): "
        + (json.dumps(skipped, sort_keys=True) if skipped else "none"),
        "Excluded by direction (outside-in playbooks, never pooled): "
        + (json.dumps(excluded, sort_keys=True) if excluded else "none"),
        "",
        "## 2. Unmapped rate (NEVER guessed — UNMAPPED preserves original text)",
        "",
        f"Overall: {candidate['unmapped_count']} unmapped of "
        f"{candidate['analyst_defenses']} "
        f"Analyst defenses = {candidate['unmapped_overall_rate']:.4f}.",
        "",
        "| playbook | defenses | unmapped | unmapped_rate |",
        "|---|---|---|---|",
    ]
    for p in per_playbook:
        lines.append(
            f"| {p['run']} | {p['defenses']} | {p['unmapped']} | "
            f"{p['unmapped_rate']:.4f} |"
        )
    lines += [
        "",
        "## 3. Trap-rule evidence",
        "",
        "R8-CANDIDATE is scoreboard evidence, NOT an Analyst quotation:",
        f"metric {TRAP_METRIC}, artifact {SCOREBOARD_ARTIFACT}.",
        "Do not say the Analyst discovered the trap problem unless a specific",
        "Analyst artifact actually says so.",
        "",
        "## 4. Executor test result",
        "",
        "NOT RUN in this distill step. Before signing, the coordinator runs:",
        "",
        "    python -m unittest tests.test_distill_batch tests.test_fleet_skew -v",
        '    python run_duel.py --agent mock --blue-mode lesson-executor \\',
        "        --lesson-file fleet/lesson_candidates/lesson-2.candidate.json \\",
        "        --out /tmp/tesseract-lesson2-executor",
        "",
        "and records the result here. The candidate lesson file is not",
        "executor-loadable until promotion assigns an opening recipe and",
        "R1-R7 coverage; a load failure before promotion is expected, not",
        "a fleet result.",
        "",
        "## 5. Approval (unsigned means lesson-1 stays the fleet default)",
        "",
        "approved_by: UNSIGNED",
        "approved_at: UNSIGNED",
        "",
    ]
    return "\n".join(lines)


def run_batch(out_dir, force=False):
    lessons_before = _sha256_file(LESSONS_PATH)
    candidate, approval = batch_distill()
    candidate_path = os.path.abspath(os.path.join(out_dir, CANDIDATE_NAME))
    approval_path = os.path.abspath(os.path.join(out_dir, APPROVAL_NAME))
    for path in (candidate_path, approval_path):
        if os.path.realpath(path) == os.path.realpath(LESSONS_PATH):
            print("REFUSED: distill_lesson.py never writes lessons.json. "
                  "Candidates require human approval and a manual promotion.",
                  file=sys.stderr)
            return 2
        if os.path.exists(path) and not force:
            print(f"REFUSED: {path} already exists (pass --force to replace).",
                  file=sys.stderr)
            return 2
    os.makedirs(os.path.abspath(out_dir), exist_ok=True)
    with open(candidate_path, "w", encoding="utf-8") as f:
        json.dump(candidate, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(approval_path, "w", encoding="utf-8") as f:
        f.write(approval)
        if not approval.endswith("\n"):
            f.write("\n")
    lessons_after = _sha256_file(LESSONS_PATH)
    if lessons_before != lessons_after:
        print("REFUSED: fleet/lessons.json changed during the batch run; "
              "production lesson file must be hash-identical before and "
              "after.", file=sys.stderr)
        return 2
    print(f"candidate: {candidate_path}")
    print(f"rules: {len(candidate['rules'])}, "
          f"unmapped: {candidate['unmapped_count']}, "
          f"overall unmapped_rate: {candidate['unmapped_overall_rate']:.4f}")
    for p in candidate["unmapped_by_playbook"]:
        print(f"  {p['run']}: {p['unmapped']}/{p['defenses']} unmapped "
              f"(rate {p['unmapped_rate']:.4f})")
    print(f"approval checklist: {approval_path} (UNSIGNED — fleet default "
          "stays lesson-1)")
    print("APPROVAL REQUIRED: review the candidate, fix UNMAPPED rules, "
          "assign an opening recipe, run the executor test, and sign. "
          "This tool never writes lessons.json.")
    return 0


def run_single(playbook_path, out_path=None, force=False):
    playbook_path = os.path.abspath(playbook_path)
    with open(playbook_path, encoding="utf-8") as f:
        playbook = json.load(f)
    run_id = os.path.basename(os.path.dirname(playbook_path))

    out_path = out_path or os.path.join(
        FLEET, "candidates", f"candidate-{run_id}.json")
    out_path = os.path.abspath(out_path)
    if os.path.realpath(out_path) == os.path.realpath(LESSONS_PATH):
        print("REFUSED: distill_lesson.py never writes lessons.json. "
              "Candidates require human approval and a manual promotion.",
              file=sys.stderr)
        return 2
    if os.path.exists(out_path) and not force:
        print(f"REFUSED: {out_path} already exists (pass --force to replace).",
              file=sys.stderr)
        return 2

    ranked = playbook.get("ranked_defenses") or []
    rules = []
    recipe = []
    unmapped = 0
    for i, entry in enumerate(ranked, start=1):
        defense = entry.get("defense", "")
        evidence = entry.get("evidence") or []
        parsed = parse_args_for(defense, evidence) if defense in KNOWN_ACTIONS else None
        if defense in KNOWN_ACTIONS and parsed is not None:
            action, action_args = defense, parsed
        else:
            action, action_args = "UNMAPPED", {}
            unmapped += 1
        rules.append({
            "id": f"C{i}",
            "trigger": defense,
            "action": action,
            "effect": ("candidate — derived deterministically from playbook, "
                       "unreviewed"),
            "evidence": evidence,
            "provenance": f"playbook {run_id} ranked_defenses",
        })
        if action != "UNMAPPED":
            recipe.append({
                "step": len(recipe) + 1,
                "action": action,
                "args": action_args,
                "learn_tick": None,
            })

    candidate = {
        "lesson_id": f"candidate-{run_id}",
        "name": f"Candidate distilled from {run_id} (UNREVIEWED)",
        "status": ("candidate — human approval required before it becomes "
                   "a lesson"),
        "simulated": True,
        "description": ("Deterministic distill of a playbook's ranked "
                        "defenses into lesson schema. No model call was "
                        "made. UNMAPPED rules need a human mapping; "
                        "learn_ticks are assigned on promotion."),
        "sources": [{"run": run_id, "run_id": run_id}],
        "opening_recipe": recipe,
        "rules": rules,
        "limits": playbook.get("gaps") or [],
        "unmapped_count": unmapped,
        "distribution": None,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(candidate, f, indent=2)
    print(f"candidate: {out_path}")
    print(f"rules: {len(rules)}, recipe steps: {len(recipe)}, "
          f"unmapped: {unmapped}")
    print("APPROVAL REQUIRED: review the candidate, fix UNMAPPED rules, "
          "assign learn_ticks, and promote it by hand. This tool never "
          "writes lessons.json.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Distill a candidate lesson")
    ap.add_argument("--playbook", default=None,
                    help="path to a playbook.json (single mode)")
    ap.add_argument("--batch", action="store_true",
                    help="batch mode: distill ALL Analyst playbooks in runs/ "
                         "into a lesson-2 candidate")
    ap.add_argument("--out", default=None,
                    help="single mode: candidate output path (default "
                         "fleet/candidates/candidate-<run>.json); batch mode: "
                         "output directory (default fleet/lesson_candidates/)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing output file(s)")
    args = ap.parse_args(argv)

    if args.batch:
        out_dir = args.out or BATCH_DEFAULT_OUT
        return run_batch(out_dir, force=args.force)
    if not args.playbook:
        print("error: --playbook is required in single mode (or pass --batch).",
              file=sys.stderr)
        return 2
    return run_single(args.playbook, out_path=args.out, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
