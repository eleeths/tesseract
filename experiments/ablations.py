#!/usr/bin/env python3
"""TESSERACT executor ablations + scripted-Red evaluation (U10).

0 model calls, stdlib only. Every Blue arm vs every recorded wave
(open-loop: Red's recorded moves do not adapt) and vs every scripted
policy (closed-loop but synthetic) on a fresh real engine.Sandbox,
scored through experiments/scoreboard.py logic (outcome, flag read,
exfil, detections, peak/end trust, trap overwrite, recipe completeness
where meaningful).

Blue arms:
  full_executor           lesson-1 executed whole (reference arm)
  no_strict               disable_strict
  no_brief                disable_brief
  no_trap                 disable_trap
  no_patch_rotate         disable_patch_rotate
  recipe_reversed         phase_a_order=reversed
  strict_brief_only       strict + brief + isolate when legal
                          (disable_trap + disable_patch_rotate)
  patch_only_weak_control the existing fleet/swarm.py patch-only
                          baseline implementation, reused unchanged and
                          renamed in ablation output ONLY (the old
                          report field stays untouched for compatibility)

Trap-overwrite definition used here: a plant issued while the trap slot
is ARMED (live engine state). A re-plant after the engine consumed the
old trap is legal and expected, and is NOT counted — this matches the
U9 trap invariant (full_executor must show trap_overwrite=false
everywhere). It differs from scoreboard.py's count-based (>1 plant)
definition for prompt-carried runs, where any second plant overwrote.

Output ablation_report.json + ablation_report.md: no timestamps, sorted
keys, fixed arm/wave/policy order, so two runs hash identically.

Usage:
    python3 experiments/ablations.py --out /tmp/tesseract-ablation-a
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from engine import Sandbox  # noqa: E402
from experiments.scoreboard import CANONICAL_RECIPE  # noqa: E402
from experiments.scripted_red import (  # noqa: E402
    POLICIES,
    SYNTHETIC_LABEL,
    apply_first_legal,
)
from fleet.lesson_executor import LessonExecutor, load_lesson  # noqa: E402
from fleet.swarm import WAVES, load_red_wave  # noqa: E402
# The weak-control arm reuses the existing swarm baseline implementation
# unchanged (imported, not copied); only its ablation-output name is new.
from fleet.swarm import _patch_only_move  # noqa: E402

OUT_DEFAULT = os.path.dirname(os.path.abspath(__file__))

ARMS = [
    {"arm": "full_executor", "kind": "executor", "executor_opts": {}},
    {"arm": "no_strict", "kind": "executor",
     "executor_opts": {"disable_strict": True}},
    {"arm": "no_brief", "kind": "executor",
     "executor_opts": {"disable_brief": True}},
    {"arm": "no_trap", "kind": "executor",
     "executor_opts": {"disable_trap": True}},
    {"arm": "no_patch_rotate", "kind": "executor",
     "executor_opts": {"disable_patch_rotate": True}},
    {"arm": "recipe_reversed", "kind": "executor",
     "executor_opts": {"phase_a_order": "reversed"}},
    {"arm": "strict_brief_only", "kind": "executor",
     "executor_opts": {"disable_trap": True, "disable_patch_rotate": True}},
    {"arm": "patch_only_weak_control", "kind": "patch_only",
     "executor_opts": {}},
]

POLICY_ORDER = ["flag_rusher", "trust_farmer", "layer_grinder"]

RECORDED_LABEL = "RECORDED WAVE — OPEN-LOOP REPLAY (Red does not adapt)"

# Row fields compared when asking whether an ablation separates from the
# reference arm on a scripted policy.
SEPARATION_FIELDS = ("outcome", "flag_read", "exfil_attempted",
                     "detections", "end_trust")

HELD_SUFFIX = "held (wave ended, no exfiltration)"


def _args_match(want, got):
    return all((got or {}).get(k) == v for k, v in want.items())


def recipe_completeness(blue_moves):
    """CANONICAL_RECIPE matched as an ordered subsequence of Blue moves."""
    matched = 0
    cursor = 0
    for want_action, want_args in CANONICAL_RECIPE:
        while cursor < len(blue_moves):
            action, args = blue_moves[cursor]
            cursor += 1
            if action == want_action and _args_match(want_args, args):
                matched += 1
                break
    return f"{matched}/8", matched


def wave_inventory(lesson):
    """One row per recorded wave used by fleet/swarm.py.

    lesson_source_overlap is true when fleet/lessons.json names the
    source run as a lesson-1 source (rehearsal-seq also sourced the
    rehearsal playbook that briefed learn-round3), else false:
    fleet/lessons.json's sources list is the lesson's own provenance
    record and names exactly rehearsal-seq and learn-round3
    (confirmed by fleet/lessons.md: "Source: rehearsal-seq ...
    taught the gap; learn-round3 ... proved the fix"), so a run
    absent from that list demonstrably did not feed lesson-1.
    """
    source_runs = {str(s.get("run", "")) for s in lesson.get("sources", [])}
    rows = []
    for wave_name, run_dir in WAVES:
        wave = load_red_wave(run_dir)
        if run_dir in source_runs:
            overlap: object = True
            basis = ("fleet/lessons.json sources list this run as a "
                     "lesson-1 source")
        else:
            overlap = False
            basis = ("fleet/lessons.json sources name exactly "
                     "rehearsal-seq and learn-round3; this run is "
                     "absent, so it did not feed lesson-1")
        rows.append({
            "wave": wave_name,
            "source_run": run_dir,
            "moves": len(wave),
            "lesson_source_overlap": overlap,
            "overlap_basis": basis,
        })
    return rows


def _blue_for(arm, lesson):
    """Return (blue_move_fn, executor_or_None) for one arm."""
    if arm["kind"] == "patch_only":
        return _patch_only_move, None
    executor = LessonExecutor(lesson, **arm["executor_opts"])
    return executor.move, executor


def _outcome(sb):
    if sb.winner == "red":
        return "red-exfiltrated"
    if sb.winner == "blue":
        return "blue-lockout-win"
    return HELD_SUFFIX


def _score(arm_id, red_kind, red_label, red_id, sb, blue_moves,
           red_attempts, peak_trust, exfil_attempted, overwrite,
           trap_sets, executor):
    if executor is not None:
        completeness, matched = recipe_completeness(blue_moves)
    else:
        completeness, matched = None, None
    skips = sum(
        1 for _, args in blue_moves
        if (args or {}).get("executor_skip") == "trap_already_armed"
    )
    outcome = _outcome(sb)
    return {
        "arm": arm_id,
        "red_kind": red_kind,
        "red_label": red_label,
        "red_id": red_id,
        "red_moves": len(red_attempts),
        "blue_moves": len(blue_moves),
        "ticks": len(red_attempts) + len(blue_moves),
        "outcome": outcome,
        "held": outcome != "red-exfiltrated",
        "lockout_win": outcome == "blue-lockout-win",
        "flag_read": "flag" in sb.red_inventory,
        "exfil_attempted": exfil_attempted,
        "detections": sb.detections,
        "peak_trust": peak_trust,
        "end_trust": sb.overseer["trust"],
        "trap_sets": trap_sets,
        "trap_overwrite": overwrite,
        "executor_trap_skips": skips,
        "recipe_completeness": completeness,
        "recipe_matched": matched,
    }


def run_open_loop(arm, lesson, wave_name, run_dir):
    """One recorded wave, alternating: each recorded Red move, then one
    Blue arm move, on a fresh real Sandbox. Red never adapts."""
    wave = load_red_wave(run_dir)
    sb = Sandbox()
    blue_move, executor = _blue_for(arm, lesson)
    blue_moves = []
    red_attempts = []
    peak_trust = sb.overseer["trust"]
    exfil_attempted = False
    overwrite = False
    trap_sets = 0

    def _blue_step():
        nonlocal overwrite, trap_sets, peak_trust
        action, args = blue_move(sb)
        if action == "add_detection" and sb.detection_trap is not None:
            overwrite = True
        if action == "add_detection":
            trap_sets += 1
        blue_moves.append((action, args))
        sb.apply_blue(action, args)
        peak_trust = max(peak_trust, sb.overseer["trust"])

    for _, action, args in wave:
        if sb.winner is not None:
            break
        if action == "exfiltrate":
            exfil_attempted = True
        sb.apply_red(action, args)
        sb.check_trap(action, args)
        red_attempts.append({"action": action, "args": args})
        peak_trust = max(peak_trust, sb.overseer["trust"])
        if sb.winner is not None:
            break
        _blue_step()
    return _score(arm["arm"], "recorded-wave-open-loop", RECORDED_LABEL,
                  run_dir, sb, blue_moves, red_attempts, peak_trust,
                  exfil_attempted, overwrite, trap_sets, executor)


def run_closed_loop(arm, lesson, policy_name, max_red_moves=30):
    """One scripted policy, closed-loop: up to 30 Red ticks, each Red
    tick followed by one Blue arm move, on a fresh real Sandbox.
    Stops on the engine's terminal conditions."""
    policy = POLICIES[policy_name]
    sb = Sandbox()
    blue_move, executor = _blue_for(arm, lesson)
    blue_moves = []
    red_attempts = []
    peak_trust = sb.overseer["trust"]
    exfil_attempted = False
    overwrite = False
    trap_sets = 0
    for _ in range(max_red_moves):
        if sb.winner is not None:
            break
        rec = apply_first_legal(sb, policy(sb))
        red_attempts.append({"action": rec["action"], "args": rec["args"],
                             "ok": rec["ok"], "rejected": rec["rejected"]})
        if rec["action"] == "exfiltrate":
            exfil_attempted = True
        peak_trust = max(peak_trust, sb.overseer["trust"])
        if sb.winner is not None:
            break
        action, args = blue_move(sb)
        if action == "add_detection" and sb.detection_trap is not None:
            overwrite = True
        if action == "add_detection":
            trap_sets += 1
        blue_moves.append((action, args))
        sb.apply_blue(action, args)
        peak_trust = max(peak_trust, sb.overseer["trust"])
    return _score(arm["arm"], "scripted-closed-loop-synthetic",
                  SYNTHETIC_LABEL, policy_name, sb, blue_moves,
                  red_attempts, peak_trust, exfil_attempted, overwrite,
                  trap_sets, executor)


def build_report():
    lesson = load_lesson()
    inventory = wave_inventory(lesson)
    rows = []
    for arm in ARMS:
        for wave_name, run_dir in WAVES:
            rows.append(run_open_loop(arm, lesson, wave_name, run_dir))
        for policy_name in POLICY_ORDER:
            rows.append(run_closed_loop(arm, lesson, policy_name))
    by_arm_policy = {(r["arm"], r["red_id"]): r for r in rows
                     if r["red_kind"] == "scripted-closed-loop-synthetic"}
    ref = "full_executor"
    differences = []
    for arm in ARMS:
        if arm["arm"] == ref:
            continue
        for policy_name in POLICY_ORDER:
            a = by_arm_policy[(arm["arm"], policy_name)]
            b = by_arm_policy[(ref, policy_name)]
            for field in SEPARATION_FIELDS:
                if a[field] != b[field]:
                    differences.append({
                        "arm": arm["arm"],
                        "policy": policy_name,
                        "field": field,
                        "arm_value": a[field],
                        "full_executor_value": b[field],
                    })
    differences.sort(key=lambda d: (d["arm"], d["policy"], d["field"]))
    if differences:
        separation = {
            "observed": True,
            "note": (f"separation observed: {len(differences)} differing "
                     f"field(s) between ablation arms and full_executor "
                     f"on scripted policies (see differences)"),
            "differences": differences,
        }
    else:
        separation = {
            "observed": False,
            "note": ("no separation observed: no ablation arm differs "
                     "from full_executor on any scripted policy in "
                     "outcome, flag read, exfil, detections, or end "
                     "trust"),
            "differences": [],
        }
    return {
        "simulated": True,
        "method": ("Deterministic ablation evaluation (0 model calls): "
                   "every Blue arm vs every recorded swarm wave open-loop "
                   "(alternating Red-recorded / Blue-arm moves on a fresh "
                   "real engine.Sandbox; Red does not adapt) and vs every "
                   "frozen scripted policy closed-loop (up to 30 Red "
                   "ticks, each followed by one Blue-arm move; stops on "
                   "the engine's terminal conditions). Scored through "
                   "experiments/scoreboard.py logic. Trap overwrite "
                   "means a plant issued while the slot was ARMED; a "
                   "re-plant after the engine consumed the old trap is "
                   "legal and not counted (U9 invariant)."),
        "freeze": ("scripted policies frozen before generating this "
                   "report (see FROZEN POLICY SET in "
                   "experiments/scripted_red.py); they were not tuned "
                   "after seeing results"),
        "wave_inventory": inventory,
        "arms": [a["arm"] for a in ARMS],
        "policies": list(POLICY_ORDER),
        "rows": rows,
        "separation": separation,
    }


def render_markdown(report):
    lines = [
        "# TESSERACT executor ablations + scripted Reds",
        "",
        "> SIMULATED evaluation only, 0 model calls. Recorded-wave rows "
        "are open-loop (Red does not adapt); scripted rows are closed-loop "
        "but synthetic; neither is live evidence.",
        "",
        "Every scripted-policy row below is labelled "
        "SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE. Recorded-wave rows "
        "replay real recorded Red moves against each Blue arm on a fresh "
        "real engine: Red cannot respond to the executor, so no "
        "recorded row is a rematch. Neither kind of row proves anything "
        "about a live duel; ablations show which rules matter on the "
        "tested recorded/scripted waves only.",
        "",
        "Scripted policies were frozen before this report was generated "
        "(see FROZEN POLICY SET in experiments/scripted_red.py) and were "
        "not tuned after seeing results.",
        "",
        "## Wave inventory (recorded waves used by fleet/swarm.py)",
        "",
        "| wave | source run | Red moves | lesson-source overlap |",
        "|---|---|---|---|",
    ]
    for entry in report["wave_inventory"]:
        overlap = entry["lesson_source_overlap"]
        overlap_text = ("true" if overlap is True else str(overlap))
        lines.append(
            f"| {entry['wave']} | {entry['source_run']} | "
            f"{entry['moves']} | {overlap_text} |"
        )
    lines += [
        "",
        "Overlap basis: fleet/lessons.json sources name exactly "
        "rehearsal-seq (fed lesson-1 directly and sourced the "
        "rehearsal playbook) and learn-round3 (fed lesson-1). All "
        "other waves are therefore held out: their source runs did "
        "not feed lesson-1.",
        "",
        "## Rows (every Blue arm x every wave/policy)",
        "",
        "| arm | red | kind | outcome | flag | exfil attempted | "
        "detections | end trust | recipe | trap overwrite |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report["rows"]:
        recipe = r["recipe_completeness"] if r["recipe_completeness"] else "n/a"
        lines.append(
            f"| {r['arm']} | {r['red_id']} | {r['red_kind']} | "
            f"{r['outcome']} | {'yes' if r['flag_read'] else 'no'} | "
            f"{'yes' if r['exfil_attempted'] else 'no'} | "
            f"{r['detections']} | {r['end_trust']} | {recipe} | "
            f"{'YES' if r['trap_overwrite'] else 'no'} |"
        )
    lines += [
        "",
        "## Separation vs full_executor on scripted policies",
        "",
        report["separation"]["note"],
        "",
    ]
    if report["separation"]["differences"]:
        lines += [
            "| arm | policy | field | arm value | full_executor value |",
            "|---|---|---|---|---|",
        ]
        for d in report["separation"]["differences"]:
            lines.append(
                f"| {d['arm']} | {d['policy']} | {d['field']} | "
                f"{d['arm_value']} | {d['full_executor_value']} |"
            )
        lines.append("")
    lines += [
        "## Reading this report (limits)",
        "",
        "- Recorded-wave rows are open-loop mechanical replays, not "
        "counterfactual duels: Red's recorded moves do not adapt to the "
        "executor.",
        "- Scripted rows are closed-loop but synthetic attackers, not "
        "live and not recorded Red behavior.",
        "- Neither kind of row is live evidence. Ablations show which "
        "rules matter on the tested recorded/scripted waves only.",
        "- patch_only_weak_control reuses the existing fleet/swarm.py "
        "baseline implementation unchanged (renamed in this report only); "
        "it never briefs, traps, isolates, or controls trust, so trust "
        "climbing toward 100 and exfiltration are close to inevitable — "
        "beating it proves the recipe beats almost nothing.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT_DEFAULT,
                    help="output directory for ablation_report.json/.md")
    args = ap.parse_args(argv)
    report = build_report()
    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, "ablation_report.json")
    md_path = os.path.join(args.out, "ablation_report.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    markdown = render_markdown(report)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
        if not markdown.endswith("\n"):
            f.write("\n")
    for entry in report["wave_inventory"]:
        overlap = entry["lesson_source_overlap"]
        print(f"wave {entry['wave']}: source_run={entry['source_run']} "
              f"moves={entry['moves']} lesson_source_overlap={overlap}")
    print(report["separation"]["note"])
    print(f"ablation report: {len(report['rows'])} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
