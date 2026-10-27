#!/usr/bin/env python3
"""TESSERACT dual-carrier comparison (U9) — 0 model calls, stdlib only.

Two carriers, one lesson:

  Prompt carrier (the control arm): the five briefed runs, read from
  experiments/scoreboard.json (itself built from runs/*/moves.jsonl +
  state.json — no hand-typed outcomes here). Per-run outcome, recipe /8,
  strict tick, briefs before phase 3, trap overwrite. The aggregates MUST
  recompute to the recorded 15/40, 38%, strict-first 2/5, overwrite 4/5;
  if the source artifacts disagree, this script FAILS LOUDLY instead of
  printing a softer number.

  Executor carrier (the deployable product): the same recorded Red waves
  — extracted with the existing fleet/swarm.py wave extraction — replayed
  open-loop against the real LessonExecutor through the real engine, plus
  mock-duel executor runs (scripted Red vs executor Blue, real engine).
  Every executor row is labeled "open-loop replay" or "mock", NEVER
  "rematch": Red's recorded moves do not adapt to the executor. Generated
  output says "execution completeness", never "adherence", for the
  executor: it deterministically executes or skips under stated
  preconditions; it does not learn to follow.

Usage:
    python3 experiments/carrier_comparison.py --out /tmp/tesseract-carrier
Writes carrier_comparison.json + carrier_comparison.md (sorted keys, no
timestamps, so two runs hash identically).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
OUT_DEFAULT = os.path.dirname(os.path.abspath(__file__))

from engine import Sandbox  # noqa: E402
from fleet.lesson_executor import LessonExecutor, apply_recipe, load_lesson  # noqa: E402
from fleet.swarm import load_red_wave  # noqa: E402
from run_duel import MOCK_RED  # noqa: E402

RUNS_DIR = os.path.join(HERE, "runs")
SCOREBOARD_PATH = os.path.join(OUT_DEFAULT, "scoreboard.json")

# The five briefed runs: the prompt carrier is exactly this set. Named
# here so the set is checked; every number below still comes from the
# scoreboard artifact, never from hand-typed outcomes.
EXPECTED_BRIEFED = [
    "learn-round3",
    "learn-round3-confirm",
    "briefed-rematch-1",
    "briefed-rematch-2",
    "briefed-rematch-3",
]


def fail(message):
    print(f"CARRIER COMPARISON FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_prompt_carrier():
    """Read the five briefed rows from the scoreboard artifact and check
    the recorded aggregates. Returns (rows_in_order, aggregates)."""
    if not os.path.isfile(SCOREBOARD_PATH):
        fail(f"scoreboard artifact missing: {SCOREBOARD_PATH}")
    with open(SCOREBOARD_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    rows = {r["run"]: r for r in doc.get("rows", [])}
    briefed = [r for r in doc.get("rows", []) if r.get("briefed")]
    if sorted(r.get("run") for r in briefed) != sorted(EXPECTED_BRIEFED):
        fail(
            "briefed set is not the recorded five: got "
            f"{sorted(r.get('run') for r in briefed)}"
        )
    ordered = [rows[name] for name in EXPECTED_BRIEFED]
    for r in ordered:
        for artifact in ("moves.jsonl", "state.json"):
            path = os.path.join(RUNS_DIR, r["run"], artifact)
            if not os.path.isfile(path):
                fail(f"source artifact missing for {r['run']}: {path}")
    matched = sum(r["recipe_matched"] for r in ordered)
    possible = 8 * len(ordered)
    strict_first = sum(
        1 for r in ordered
        if r["strict_tick"] is not None and r["strict_tick"] <= 10
    )
    overwrites = sum(1 for r in ordered if r["trap_overwrite"])
    pct = matched / possible
    if matched != 15 or possible != 40 or f"{pct:.0%}" != "38%":
        fail(
            "recipe aggregate drifted: recomputed "
            f"{matched}/{possible} = {pct:.0%} (recorded 15/40 = 38%)"
        )
    if strict_first != 2:
        fail(f"strict-first drifted: recomputed {strict_first}/5 (recorded 2/5)")
    if overwrites != 4:
        fail(f"trap-overwrite drifted: recomputed {overwrites}/5 (recorded 4/5)")
    aggregates = {
        "briefed_runs": len(ordered),
        "recipe_total": f"{matched}/{possible}",
        "recipe_mean": f"{pct:.0%}",
        "strict_first": f"{strict_first}/{len(ordered)}",
        "trap_overwrite": f"{overwrites}/{len(ordered)}",
        "wins": f"{sum(1 for r in ordered if r['winner'] == 'blue')}/{len(ordered)}",
    }
    return ordered, aggregates


def _executor_outcome(sb):
    if sb.winner == "red":
        return "red-exfiltrated"
    if sb.winner == "blue":
        return "blue-lockout-win"
    return "held (wave ended, no exfiltration)"


def _completeness(executor):
    consumed = min(executor.index, len(executor.recipe))
    skipped_a = sum(1 for s in executor.skips if s.get("phase") == "A")
    executed = consumed - skipped_a
    skipped_total = len(executor.skips)
    return (
        f"{executed}/{len(executor.recipe)} recipe steps executed, "
        f"{skipped_total} skipped under trap invariant"
    )


def _replay_row(label, kind, red_moves, lesson, blue_plan="alternating"):
    """Open-loop replay of fixed Red moves vs executor Blue on a fresh
    real Sandbox. Red never adapts: kind is 'open-loop replay' or 'mock'."""
    sb = Sandbox()
    executor = LessonExecutor(lesson)
    blue_moves = []
    # An overwrite is a plant into an ARMED slot — not a re-plant after the
    # engine consumed the old trap (that is legal and expected). Tracked
    # from live engine state, not inferred from the plant count.
    overwrite = False

    def _blue(action, args):
        nonlocal overwrite
        if action == "add_detection" and sb.detection_trap is not None:
            overwrite = True
        blue_moves.append((action, args))
        sb.apply_blue(action, args)

    if blue_plan == "sequential":
        first, second = red_moves[:len(red_moves) // 2], red_moves[len(red_moves) // 2:]
        for _, action, args in first:
            if sb.winner is not None:
                break
            sb.apply_red(action, args)
            sb.check_trap(action, args)
        if sb.winner is None:
            apply_recipe(sb, lesson)
            executor.index = len(executor.recipe)
            for _, action, args in second:
                if sb.winner is not None:
                    break
                sb.apply_red(action, args)
                sb.check_trap(action, args)
                if sb.winner is not None:
                    break
                _blue(*executor.move(sb))
    else:
        for _, action, args in red_moves:
            if sb.winner is not None:
                break
            sb.apply_red(action, args)
            sb.check_trap(action, args)
            if sb.winner is not None:
                break
            _blue(*executor.move(sb))
    plants = sum(1 for a, _ in blue_moves if a == "add_detection")
    if overwrite:
        fail(f"executor overwrote its own trap in {label}")
    skips = sum(
        1 for _, args in blue_moves
        if (args or {}).get("executor_skip") == "trap_already_armed"
    )
    return {
        "row": label,
        "kind": kind,
        "red_moves": len(red_moves),
        "blue_moves": len(blue_moves),
        "outcome": _executor_outcome(sb),
        "detections": sb.detections,
        "flag_reached": "flag" in sb.red_inventory,
        "exfil_attempted": any(a == "exfiltrate" for _, a, _ in red_moves),
        "execution_completeness": _completeness(executor),
        "trap_plants": plants,
        "trap_overwrite": overwrite,
        "executor_trap_skips": skips,
    }


def build_executor_carrier(lesson):
    rows = []
    for run_id in EXPECTED_BRIEFED:
        wave = load_red_wave(run_id)
        if not wave:
            fail(f"no Red wave extractable for {run_id}")
        rows.append(_replay_row(run_id, "open-loop replay", wave, lesson))
    mock_wave = [(i + 1, action, dict(args)) for i, (action, args) in enumerate(MOCK_RED)]
    rows.append(_replay_row("mock-duel-alternating", "mock", mock_wave, lesson))
    rows.append(
        _replay_row("mock-duel-sequential", "mock", mock_wave, lesson,
                    blue_plan="sequential")
    )
    return rows


def render_markdown(prompt_rows, aggregates, executor_rows):
    lines = [
        "# TESSERACT dual-carrier comparison",
        "",
        "> SIMULATED duels and deterministic mechanical replays only. "
        "Prompt-carrier numbers are read from experiments/scoreboard.json "
        "(built from runs/*/moves.jsonl + state.json). Executor rows are "
        "open-loop replays (recorded Red moves do not adapt) or mock duels "
        "(scripted Red vs executor Blue). No live duels ran for this table, "
        "no model calls were made.",
        "",
        "## Prompt carrier (control arm): briefed Blue reads the playbook",
        "",
        "The control arm shows why prompt-carried lessons are unreliable: "
        "the lesson works when followed, and a single briefed agent does not "
        "reliably follow it.",
        "",
        f"Briefed runs: {aggregates['briefed_runs']}. "
        f"Recipe completion: {aggregates['recipe_total']} = "
        f"{aggregates['recipe_mean']}. "
        f"Strict-first: {aggregates['strict_first']}. "
        f"Trap overwrites: {aggregates['trap_overwrite']}. "
        f"Wins: {aggregates['wins']} (reported, not headlined).",
        "",
        "| run | winner | recipe | strict tick | briefs < phase 3 | trap overwrite |",
        "|---|---|---|---|---|---|",
    ]
    for r in prompt_rows:
        strict = r["strict_tick"] if r["strict_tick"] is not None else "—"
        lines.append(
            f"| {r['run']} | {r['winner']} | {r['recipe_completion']} | "
            f"{strict} | {r['briefs_before_phase_3']} | "
            f"{'YES' if r['trap_overwrite'] else 'no'} |"
        )
    lines += [
        "",
        "## Executor carrier (deployable product): lesson-1 executed "
        "deterministically",
        "",
        "The executor does not read the playbook; it executes lesson-1 "
        "mechanically (0 model calls for Blue) with the trap-state "
        "invariant: a second set_trap while armed is impossible, and blocked "
        "attempts wait with executor_skip=\"trap_already_armed\". "
        "Completeness below is execution completeness: steps executed or "
        "skipped under stated preconditions.",
        "",
        "| row | kind | red/blue moves | outcome | execution completeness | "
        "trap skips | trap overwrite |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in executor_rows:
        lines.append(
            f"| {r['row']} | {r['kind']} | {r['red_moves']}/{r['blue_moves']} | "
            f"{r['outcome']} | {r['execution_completeness']} | "
            f"{r['executor_trap_skips']} | "
            f"{'YES' if r['trap_overwrite'] else 'no'} |"
        )
    lines += [
        "",
        "## Reading this table (limits)",
        "",
        "- Prompt rows are briefed rematches (live, stochastic Red). "
        "Executor rows are open-loop replays or mocks: Red cannot adapt to "
        "executor moves, so no executor row is a rematch and none proves a "
        "future live duel is won.",
        "- The executor never overwrote its own trap in any row above "
        "(the script fails loudly if that ever happens).",
        "- What evolves is playbook/tactics, never model weights.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True,
                    help="output directory for carrier_comparison.json/.md")
    args = ap.parse_args(argv)
    lesson = load_lesson()
    prompt_rows, aggregates = load_prompt_carrier()
    executor_rows = build_executor_carrier(lesson)
    doc = {
        "simulated": True,
        "prompt_carrier": {
            "kind": "briefed rematches (live, control arm)",
            "aggregates": aggregates,
            "rows": [
                {
                    "run": r["run"],
                    "winner": r["winner"],
                    "ticks": r["ticks"],
                    "strict_tick": r["strict_tick"],
                    "briefs_before_phase_3": r["briefs_before_phase_3"],
                    "trap_overwrite": r["trap_overwrite"],
                    "recipe_completion": r["recipe_completion"],
                    "flag_read": r["flag_read"],
                    "exfil_attempted": r["exfil_attempted"],
                }
                for r in prompt_rows
            ],
        },
        "executor_carrier": executor_rows,
    }
    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, "carrier_comparison.json")
    md_path = os.path.join(args.out, "carrier_comparison.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(prompt_rows, aggregates, executor_rows))
    print(
        f"prompt carrier: {aggregates['recipe_total']} = {aggregates['recipe_mean']}, "
        f"strict-first {aggregates['strict_first']}, "
        f"overwrite {aggregates['trap_overwrite']}, wins {aggregates['wins']}"
    )
    print(f"executor carrier: {len(executor_rows)} rows "
          f"({sum(1 for r in executor_rows if r['kind'] == 'open-loop replay')} "
          "open-loop replay, "
          f"{sum(1 for r in executor_rows if r['kind'] == 'mock')} mock), "
          "trap overwrites: 0")
    print(f"carrier comparison: 2 files -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
