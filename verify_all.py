#!/usr/bin/env python3
"""TESSERACT judge reproducibility check — 0 model calls, skip-live.

Verifies, in order:
  1. Every project .py file compiles (root, fleet/, payments/, dashboard/).
  2. A mock duel runs to a temp dir and writes summary.json.
  3. The fleet swarm replay runs and writes swarm_report.json.
  4. The money-flow verifier passes.
  5. The thin-engine fuzz smoke runs (reduced: seeds 1..3, BOTH
     directions; the full seeds 1..20 fuzz stays an explicit
     `python3 experiments/engine_fuzz.py --seeds 1-20 --ticks 500`).
  6. The claims lint passes strict over submission/dashboard/fleet.
  7. credit_log.jsonl is byte-identical before and after (no live calls).

Exit 0 only if every step passes. Prints one PASS/FAIL line per step.
Usage: python3 verify_all.py
"""
import os
import py_compile
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CREDIT_LOG = os.path.join(HERE, "credit_log.jsonl")


def step(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - report, don't crash the suite
        print(f"FAIL {name}: {exc}")
        return False
    print(f"PASS {name}")
    return True


def compile_all():
    targets = []
    for sub in ("", "fleet", "payments", "dashboard", "experiments"):
        d = os.path.join(HERE, sub) if sub else HERE
        for name in sorted(os.listdir(d)):
            if name.endswith(".py"):
                targets.append(os.path.join(d, name))
    if not targets:
        raise RuntimeError("no .py files found")
    for path in targets:
        py_compile.compile(path, doraise=True)


def mock_duel():
    with tempfile.TemporaryDirectory(prefix="tesseract-verify-") as tmp:
        out = os.path.join(tmp, "mock")
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "run_duel.py"),
             "--agent", "mock", "--mode", "sequential", "--rounds", "2",
             "--out", out],
            capture_output=True, text=True, timeout=120, cwd=HERE,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"mock duel failed: {proc.stderr.strip()[:300]}")
        if not os.path.isfile(os.path.join(out, "summary.json")):
            raise RuntimeError("mock duel wrote no summary.json")
        if not os.path.isfile(os.path.join(out, "snapshots.jsonl")):
            raise RuntimeError("mock duel wrote no snapshots.jsonl")


def swarm_replay():
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "fleet", "swarm.py")],
        capture_output=True, text=True, timeout=120, cwd=HERE,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"swarm replay failed: {proc.stderr.strip()[:300]}")
    if not os.path.isfile(os.path.join(HERE, "fleet", "swarm_report.json")):
        raise RuntimeError("swarm replay wrote no swarm_report.json")


def moneyflow_verify():
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "payments", "moneyflow.py"),
         "verify"],
        capture_output=True, text=True, timeout=60, cwd=HERE,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"moneyflow verify failed: {proc.stdout.strip()[:300]}")


def engine_fuzz_reduced():
    """U15 thin-engine proof, smoke size: seeds 1..3 at default ticks.

    In-memory only: engine_fuzz writes nothing (no runs/, no
    credit_log.jsonl, no STATUS.md, no fleet/lessons.json).
    """
    for direction in ("inside-out", "outside-in"):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "experiments", "engine_fuzz.py"),
             "--seeds", "1-3", "--direction", direction],
            capture_output=True, text=True, timeout=300, cwd=HERE,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"engine fuzz (reduced, {direction}) failed: "
                f"{(proc.stdout + proc.stderr).strip()[-500:]}")


def claims_lint():
    """U15 claims lint, strict: reports every hit; fails on violations.

    Read-only: claims_lint never modifies the scanned files (a genuine
    overstatement is reported for the coordinator, never silenced here).
    Round 4 extends the scan to marketplace/ (demo report) and
    STATUS.md; the one STATUS.md historical hit was a "combin" ->
    "combined" false positive fixed in the lint itself, not by
    rewriting history.
    """
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "experiments", "claims_lint.py"),
         "submission", "dashboard", "fleet", "marketplace", "STATUS.md",
         "--strict"],
        capture_output=True, text=True, timeout=120, cwd=HERE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claims lint failed: "
            f"{(proc.stdout + proc.stderr).strip()[-500:]}")


def marketplace_verify():
    """Round-4 marketplace ledger verification (read-only, real artifacts)."""
    proc = subprocess.run(
        [sys.executable, "-m", "marketplace.demo", "--verify"],
        capture_output=True, text=True, timeout=60, cwd=HERE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"marketplace verify failed: "
            f"{(proc.stdout + proc.stderr).strip()[-300:]}")


def marketplace_determinism():
    """Round-4 determinism: two fresh demo runs must be byte-identical.

    Temp dirs only; the real marketplace/ artifacts are never touched.
    """
    import filecmp
    names = ("marketplace_ledger.json", "roster_marketplace.json",
             "demo_manifest.json", "demo_report.md",
             os.path.join("runs", "MP-RUN-001.json"))
    with tempfile.TemporaryDirectory(prefix="tesseract-mp-a-") as a, \
            tempfile.TemporaryDirectory(prefix="tesseract-mp-b-") as b:
        for out in (a, b):
            proc = subprocess.run(
                [sys.executable, "-m", "marketplace.demo", "--out", out],
                capture_output=True, text=True, timeout=120, cwd=HERE,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"marketplace demo failed in {out}: "
                    f"{(proc.stdout + proc.stderr).strip()[-300:]}")
        for name in names:
            if not filecmp.cmp(os.path.join(a, name), os.path.join(b, name),
                               shallow=False):
                raise RuntimeError(
                    f"marketplace determinism failed on {name}")


def main():
    before = None
    if os.path.exists(CREDIT_LOG):
        with open(CREDIT_LOG, "rb") as f:
            before = f.read()
    results = [
        step("py_compile all modules", compile_all),
        step("mock duel to temp dir", mock_duel),
        step("fleet swarm replay", swarm_replay),
        step("moneyflow verify", moneyflow_verify),
        step("engine fuzz reduced (seeds 1-3)", engine_fuzz_reduced),
        step("claims lint strict", claims_lint),
        step("marketplace verify", marketplace_verify),
        step("marketplace determinism", marketplace_determinism),
    ]
    after = None
    if os.path.exists(CREDIT_LOG):
        with open(CREDIT_LOG, "rb") as f:
            after = f.read()
    if before != after:
        print("FAIL credit log untouched (skip-live violated)")
        results.append(False)
    else:
        print("PASS credit log untouched (0 new model calls)")
        results.append(True)
    if all(results):
        print("verify_all: ALL PASS")
        return 0
    print("verify_all: FAILURES PRESENT")
    return 1


if __name__ == "__main__":
    sys.exit(main())
