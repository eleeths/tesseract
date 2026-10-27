#!/usr/bin/env python3
"""TESSERACT loop orchestrator (U6) — closes the loop in code.

Pipeline: duel -> analyst -> rematch (briefed with the new playbook)
-> scoreboard row. Writes loop_report.json in the loop directory.

Modes:
- live: real model calls (duel turns + exactly 1 analyst call). Spends
  free credits only; the caller owns the budget.
- mock: 0 model calls. The analyst step writes a clearly labeled MOCK
  STUB playbook (never presented as model output) so the pipeline shape
  can be verified without spending anything. The rematch then briefs
  with the stub; mock Blue ignores briefing text anyway.

The distilled-lesson step is deliberately NOT automatic: see
fleet/distill_lesson.py, which writes a candidate a human must approve
before it becomes a lesson. loop.py never writes lessons.json.

Usage:
    python3 loop.py --agent mock --mode sequential --rounds 8
    python3 loop.py --agent live --mode sequential --rounds 8 --out runs/loop-live1
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from experiments.scoreboard import row_for  # noqa: E402

MOCK_PLAYBOOK = {
    "attack_to_defense": "MOCK STUB — deterministic placeholder, not model output.",
    "ranked_defenses": [],
    "blue_evolution": "MOCK STUB — no model was called.",
    "gaps": ["MOCK STUB"],
    "next_drills": ["MOCK STUB"],
}


def run(cmd, label):
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=600, cwd=HERE)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{label} failed (exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:400]}")
    return proc.stdout


def main():
    ap = argparse.ArgumentParser(description="TESSERACT loop orchestrator")
    ap.add_argument("--agent", choices=["mock", "live"], default="mock")
    ap.add_argument("--mode", choices=["duel", "sequential"],
                    default="sequential")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--out", default=None,
                    help="loop directory (default runs/loop-<stamp>)")
    args = ap.parse_args()

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or os.path.join(HERE, "runs", f"loop-{stamp}")
    duel_dir = os.path.join(out_dir, "duel")
    rematch_dir = os.path.join(out_dir, "rematch")

    run([sys.executable, os.path.join(HERE, "run_duel.py"),
         "--agent", args.agent, "--mode", args.mode,
         "--rounds", str(args.rounds), "--out", duel_dir], "duel")

    if args.agent == "live":
        run([sys.executable, os.path.join(HERE, "analyst.py"),
             "--run", duel_dir], "analyst")
        analyst_kind = "live (1 call)"
        playbook_md = os.path.join(duel_dir, "playbook.md")
    else:
        with open(os.path.join(duel_dir, "playbook.json"), "w",
                  encoding="utf-8") as f:
            json.dump(MOCK_PLAYBOOK, f, indent=2)
        playbook_md = os.path.join(duel_dir, "playbook.md")
        with open(playbook_md, "w", encoding="utf-8") as f:
            f.write("# TESSERACT Playbook (MOCK STUB)\n\n"
                    "> MOCK STUB — deterministic placeholder written by "
                    "loop.py in mock mode. No model was called and this "
                    "is not a real playbook.\n")
        analyst_kind = "mock-stub (0 calls)"

    run([sys.executable, os.path.join(HERE, "run_duel.py"),
         "--agent", args.agent, "--mode", args.mode,
         "--rounds", str(args.rounds),
         "--blue-briefing", playbook_md, "--out", rematch_dir], "rematch")

    report = {
        "simulated": True,
        "agent": args.agent,
        "mode": args.mode,
        "rounds": args.rounds,
        "duel": duel_dir,
        "rematch": rematch_dir,
        "analyst": analyst_kind,
        "scoreboard_rows": [
            row_for(duel_dir, briefed=False),
            row_for(rematch_dir, briefed=True),
        ],
        "note": ("Candidate lessons are NOT auto-promoted: run "
                 "fleet/distill_lesson.py on the duel playbook, review the "
                 "candidate, and promote it by hand. loop.py never writes "
                 "lessons.json."),
    }
    with open(os.path.join(out_dir, "loop_report.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"loop done: duel={duel_dir}")
    print(f"loop done: rematch={rematch_dir} analyst={analyst_kind}")
    for row in report["scoreboard_rows"]:
        print(f"  {row['run']}: winner={row['winner']} "
              f"recipe={row['recipe_completion']} strict={row['strict_tick']}")
    print(f"loop_report: {os.path.join(out_dir, 'loop_report.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
