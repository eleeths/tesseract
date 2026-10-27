#!/usr/bin/env python3
"""TESSERACT mixed-direction wave series — 0 model calls, stdlib only.

Attacks do not come one direction at a time. This series defends 8
waves in EXACTLY this order: in, out, out, in, in, out, out, in
(in = outside-in attack, out = inside-out attack), with the direction
labeled on every wave and every result row.

Structure (deterministic mechanical replay, same precedent as the U3
combined arm): one fresh Sandbox per wave (a single Sandbox cannot hold
two directions), defended by the lesson-1 executor answering after each
Red move. In-waves get hired-defender help enabled (inner-box
self-defense PLUS hired help, per the outside-in design); out-waves do
not (hired help is the inner box's defense — the engine gates it to
outside-in regardless).

Wave sources (recorded live Red sequences, loaded via
fleet/swarm.py:load_red_wave, plus one synthetic):
  1 in  — runs/outsidein-live-1 (live outside-in Red)
  2 out — runs/rehearsal-seq (live inside-out Red win)
  3 out — runs/learn-round3-confirm (live inside-out Red win)
  4 in  — runs/outsidein-live-2 (live outside-in Red)
  5 in  — runs/outsidein-live-3 (live outside-in Red)
  6 out — runs/briefed-rematch-2 (live inside-out Red win)
  7 out — runs/briefed-rematch-3 (live inside-out Red win)
  8 in  — scripted flag_rusher, terminal swapped (SYNTHETIC SCRIPTED —
          NOT RECORDED, NOT LIVE; only 3 live outside-in trials exist)

Out-waves are deliberately the strongest recorded inside-out attackers
(all Red wins): the series tests the full defense, not a soft sample.
Outcome "held" means the wave ended with no terminal success (the same
primary-metric definition as the live trials); winner "undecided" means
the wave was exhausted with no terminal and no lockout (this loop
applies no Duel timeout rule).

Output is deterministic (no timestamps, sorted keys); rerunning must be
byte-identical.

Usage:
    python3 experiments/mixed_directions.py [--out-dir experiments]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from engine import Sandbox  # noqa: E402
from experiments.scripted_red import (  # noqa: E402
    POLICIES,
    SYNTHETIC_LABEL,
    apply_first_legal,
)
from fleet.lesson_executor import LessonExecutor, load_lesson  # noqa: E402
from fleet.swarm import load_red_wave  # noqa: E402

OUT_DEFAULT = os.path.dirname(os.path.abspath(__file__))

# (wave number, direction, source kind, source id)
# direction "in" = outside-in, "out" = inside-out. Order is Emmanuel's
# verbatim: in, out, out, in, in, out, out, in.
SERIES = [
    (1, "in", "run", "outsidein-live-1"),
    (2, "out", "run", "rehearsal-seq"),
    (3, "out", "run", "learn-round3-confirm"),
    (4, "in", "run", "outsidein-live-2"),
    (5, "in", "run", "outsidein-live-3"),
    (6, "out", "run", "briefed-rematch-2"),
    (7, "out", "run", "briefed-rematch-3"),
    (8, "in", "scripted", "flag_rusher"),
]


def _scripted_wave(policy_name, max_moves=30):
    """Fixed Red move list from a frozen policy, unopposed (no Blue).

    The policy runs against a fresh outside-in Sandbox with the
    terminal swapped, recording accepted moves until terminal or the
    move budget. Deterministic; the list is then replayed like a
    recorded wave. Labeled synthetic everywhere it appears.
    """
    policy = POLICIES[policy_name]
    sb = Sandbox(direction="outside-in")
    wave = []
    for _ in range(max_moves):
        if sb.winner is not None:
            break
        sb.tick += 1
        cands = [("infiltrate", args) if action == "exfiltrate" else (action, args)
                 for action, args in policy(sb)]
        rec = apply_first_legal(sb, cands)
        wave.append((sb.tick, rec["action"], rec["args"]))
    return wave


def _run_wave(n, direction, kind, source_id, lesson):
    """Defend one wave. Returns the result row dict."""
    engine_direction = "outside-in" if direction == "in" else "inside-out"
    hired_help = direction == "in"
    if kind == "run":
        wave = load_red_wave(os.path.join(HERE, "runs", source_id))
        source_label = source_id
        synthetic = False
    else:
        wave = _scripted_wave(source_id)
        source_label = f"scripted {source_id} (synthetic)"
        synthetic = True
    if not wave:
        raise RuntimeError(f"wave {n} ({source_label}): no Red moves loaded")
    sb = Sandbox(direction=engine_direction, hired_help=hired_help)
    executor = LessonExecutor(lesson)
    peak_trust = sb.overseer["trust"]
    overwrite = False
    trap_sets = 0
    red_played = 0
    blue_played = 0
    for _tick, action, args in wave:
        if sb.winner is not None:
            break
        sb.tick += 1
        sb.apply_red(action, args)
        sb.check_trap(action, args)
        red_played += 1
        peak_trust = max(peak_trust, sb.overseer["trust"])
        if sb.winner is not None:
            break
        hired = sb.hired_step()
        if sb.winner is not None:
            break
        sb.tick += 1
        b_action, b_args = executor.move(sb)
        if b_action == "add_detection" and sb.detection_trap is not None:
            overwrite = True
        if b_action == "add_detection":
            trap_sets += 1
        sb.apply_blue(b_action, b_args)
        blue_played += 1
        peak_trust = max(peak_trust, sb.overseer["trust"])
        hired = sb.hired_step()
    terminal_action = "infiltrate" if direction == "in" else "exfiltrate"
    terminal_attempted = any(a == terminal_action for _, a, _ in wave[:red_played])
    if sb.winner == "red":
        outcome = "infiltrated" if direction == "in" else "exfiltrated"
    else:
        outcome = "held"
    if direction == "in":
        if sb.hired_arrived_tick is not None:
            hired_label = (f"called t{sb.hired_called_tick}, arrived "
                           f"t{sb.hired_arrived_tick}, {sb.hired_patches} patches")
        elif sb.hired_called_tick is not None:
            hired_label = f"called t{sb.hired_called_tick}, not arrived"
        else:
            hired_label = "not called"
    else:
        hired_label = "n/a (outside-in only)"
    return {
        "n": n,
        "direction": direction,
        "direction_label": "IN (outside-in)" if direction == "in" else "OUT (inside-out)",
        "source": source_label,
        "synthetic": synthetic,
        "synthetic_label": SYNTHETIC_LABEL if synthetic else None,
        "outcome": outcome,
        "winner": sb.winner if sb.winner is not None else "undecided",
        "flag": "acquired" if "flag" in sb.red_inventory else "no",
        "terminal": (f"{terminal_action} attempted"
                     if terminal_attempted else f"{terminal_action} not attempted"),
        "hired": hired_label,
        "detections": sb.detections,
        "peak_trust": peak_trust,
        "end_trust": sb.overseer["trust"],
        "breach_order": list(sb.breach_order),
        "trap_overwrite": overwrite,
        "trap_sets": trap_sets,
        "red_moves": red_played,
        "blue_moves": blue_played,
        "hired_called_tick": sb.hired_called_tick,
        "hired_arrived_tick": sb.hired_arrived_tick,
        "hired_actions": sb.hired_actions,
        "hired_patches": sb.hired_patches,
    }


def build_report(out_dir):
    lesson = load_lesson()
    rows = [_run_wave(n, direction, kind, source_id, lesson)
            for n, direction, kind, source_id in SERIES]
    order = [r["direction"] for r in rows]
    assert order == ["in", "out", "out", "in", "in", "out", "out", "in"], order
    held = sum(1 for r in rows if r["outcome"] == "held")
    report = {
        "simulated": True,
        "structure": ("deterministic mechanical replay, 0 model calls: "
                      "one fresh Sandbox per wave, lesson executor "
                      "answering after each Red move; hired help enabled "
                      "on in-waves only"),
        "order": order,
        "held": held,
        "waves": rows,
        "framing": ("Rogue waves attack from both directions; controlled "
                    "defenders (inner-box self-defense plus hired help on "
                    "in-waves) defend every wave."),
    }
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "mixed_directions.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    md_path = os.path.join(out_dir, "mixed_directions.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report))
    return report, json_path, md_path


def render_markdown(report):
    lines = [
        "# TESSERACT mixed-direction wave series",
        "",
        "> SIMULATED, deterministic mechanical replay, 0 model calls. "
        "Direction is labeled on every wave and every result row.",
        "",
        "## Framing",
        "",
        report["framing"],
        "",
        "## Order (verbatim): in, out, out, in, in, out, out, in",
        "",
        "in = outside-in attack (big outer box inward); out = inside-out "
        "attack (small agent inside breaking out). One fresh Sandbox per "
        "wave; lesson executor defends every wave; hired help enabled on "
        "in-waves only (hired help is the inner box's defense). Out-waves "
        "are the strongest recorded inside-out attackers (all Red wins). "
        "Wave 8 is SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE (only 3 "
        "live outside-in trials exist).",
        "",
        "| wave | direction | source wave | defender | outcome | flag | "
        "terminal | hired help | detections | peak/end trust | breach order |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for w in report["waves"]:
        defender = ("self-defense + hired help"
                    if w["direction"] == "in" else "self-defense (executor)")
        lines.append(
            f"| {w['n']} | {w['direction_label']} | {w['source']} | "
            f"{defender} | {w['outcome']} | {w['flag']} | {w['terminal']} | "
            f"{w['hired']} | {w['detections']} | "
            f"{w['peak_trust']}/{w['end_trust']} | "
            f"{','.join(str(n) for n in w['breach_order']) or '—'} |")
    lines += [
        "",
        f"Held: {report['held']}/8 waves (raw count, never a reliability "
        "percentage). Outcome \"held\" means the wave ended with no "
        "terminal success.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=OUT_DEFAULT,
                    help="output directory (default: experiments/)")
    args = ap.parse_args(argv)
    report, json_path, md_path = build_report(args.out_dir)
    print(f"mixed series: held {report['held']}/8, "
          f"order {' '.join(report['order'])}")
    for w in report["waves"]:
        print(f"wave {w['n']} {w['direction_label']}: {w['source']} -> "
              f"{w['outcome']} (flag {w['flag']}, {w['terminal']}, "
              f"hired: {w['hired']})")
    print(f"mixed report -> {json_path}, {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
