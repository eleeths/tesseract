#!/usr/bin/env python3
"""TESSERACT version-skew SIMULATION scenario (U13) — 0 model calls.

Propagation as a simulation scenario, separate from
fleet/swarm_report.json so payout derivation cannot change. Five
independent engine.Sandbox instances labelled CLONE-01..05:

  CLONE-01..04  load the candidate/current executor lesson
                (--lesson-file, default fleet/lessons.json).
  CLONE-05      loads a defined lesson-0 control: executor Phase B
                reactions with the Phase A opening recipe disabled
                (recipe list emptied in memory; the lesson file and
                fleet/roster.json are untouched).

The same scripted Red policy from U10 (layer_grinder) runs against
each clone's OWN Sandbox for up to 30 Red ticks, round-robin by tick
for presentation, but with fully independent state (separate
Sandbox + LessonExecutor per clone; no shared mutable state).

This is a scenario overlay: roster.json is never edited, so nothing
here claims CLONE-05 actually lacks the lesson. Region/specialty
have no engine effect.

Output skew_report.json + skew_report.md (no timestamps, sorted
keys, fixed clone order): two runs are byte-identical.

Usage:
    python3 experiments/fleet_skew.py --out /tmp/tesseract-skew
    python3 experiments/fleet_skew.py --lesson-file fleet/lesson_candidates/lesson-2.candidate.json --out /tmp/tesseract-skew
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from engine import Sandbox  # noqa: E402
from experiments.scripted_red import (  # noqa: E402
    SYNTHETIC_LABEL,
    apply_first_legal,
    layer_grinder,
)
from fleet.lesson_executor import LessonExecutor, load_lesson  # noqa: E402

FLEET_DIR = os.path.join(HERE, "fleet")
DEFAULT_LESSON = os.path.join(FLEET_DIR, "lessons.json")
OUT_DEFAULT = FLEET_DIR

HEADER = ("SIMULATED VERSION-SKEW SCENARIO — roster unchanged; "
          "region/specialty have no engine effect")

CLONES = ["CLONE-01", "CLONE-02", "CLONE-03", "CLONE-04", "CLONE-05"]
CONTROL_CLONE = "CLONE-05"
MAX_RED_TICKS = 30


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_lesson_zero(lesson):
    """Lesson-0 control: executor Phase B reactions with the Phase A
    opening recipe disabled. Built in memory from the loaded lesson's
    own rules (kept for reference); no file is written and the
    production lesson is untouched."""
    return {
        "lesson_id": "lesson-0-control",
        "opening_recipe": [],
        "rules": lesson.get("rules", []),
    }


def _step_clone(state):
    """One Red tick + one Blue reply for a single clone's own Sandbox."""
    sb = state["sandbox"]
    if sb.winner is not None:
        return
    rec = apply_first_legal(sb, layer_grinder(sb))
    state["red_ticks"] += 1
    if rec["action"] == "exfiltrate":
        state["exfil_attempted"] = True
    state["peak_trust"] = max(state["peak_trust"], sb.overseer["trust"])
    if sb.winner is not None:
        return
    action, args = state["executor"].move(sb)
    sb.apply_blue(action, args)
    state["blue_moves"] += 1
    state["peak_trust"] = max(state["peak_trust"], sb.overseer["trust"])


def _clone_result(state):
    sb = state["sandbox"]
    if sb.winner == "red":
        outcome = "red-exfiltrated"
    elif sb.winner == "blue":
        outcome = "blue-lockout-win"
    else:
        outcome = "held (wave ended, no exfiltration)"
    return {
        "clone": state["clone_id"],
        "lesson": state["lesson_label"],
        "red_policy": "layer_grinder",
        "red_label": SYNTHETIC_LABEL,
        "red_ticks": state["red_ticks"],
        "blue_moves": state["blue_moves"],
        "outcome": outcome,
        "held": outcome != "red-exfiltrated",
        "lockout_win": outcome == "blue-lockout-win",
        "flag_read": "flag" in sb.red_inventory,
        "exfil_attempted": state["exfil_attempted"],
        "detections": sb.detections,
        "peak_trust": state["peak_trust"],
        "end_trust": sb.overseer["trust"],
    }


def build_report(lesson_path=None):
    lesson_path = os.path.abspath(lesson_path or DEFAULT_LESSON)
    lesson = load_lesson(lesson_path)
    lesson_label = {
        "lesson_id": lesson.get("lesson_id", "unknown"),
        "lesson_file": os.path.relpath(lesson_path, HERE),
        "lesson_sha256": _sha256_file(lesson_path),
    }
    control_label = {
        "lesson_id": "lesson-0-control",
        "note": ("executor Phase B reactions only; Phase A opening recipe "
                 "disabled. Scenario overlay: roster.json unchanged, "
                 "CLONE-05 is not claimed to lack the lesson."),
    }
    # Round-robin by tick for presentation with fully independent
    # state: each tick visits every clone once, but every clone defends
    # its OWN Sandbox with its OWN executor — no shared mutable state,
    # so the visit order cannot affect any clone's outcome.
    states = []
    for clone_id in CLONES:
        if clone_id == CONTROL_CLONE:
            executor = LessonExecutor(make_lesson_zero(lesson))
            label = control_label
        else:
            executor = LessonExecutor(lesson)
            label = lesson_label
        sb = Sandbox()
        states.append({
            "clone_id": clone_id,
            "sandbox": sb,
            "executor": executor,
            "lesson_label": label,
            "red_ticks": 0,
            "blue_moves": 0,
            "exfil_attempted": False,
            "peak_trust": sb.overseer["trust"],
        })
    for _ in range(MAX_RED_TICKS):
        for state in states:
            _step_clone(state)
    clones = [_clone_result(state) for state in states]
    return {
        "header": HEADER,
        "simulated": True,
        "synthetic_red": SYNTHETIC_LABEL,
        "method": ("Version-skew simulation (0 model calls): five "
                   "independent engine.Sandbox instances, one per clone. "
                   "CLONE-01..04 load the executor lesson from --lesson-file; "
                   "CLONE-05 loads a defined lesson-0 control (executor "
                   "Phase B reactions, Phase A opening recipe disabled). "
                   "The U10 layer_grinder scripted policy attacks each "
                   "clone's own Sandbox for up to 30 Red ticks, round-robin "
                   "by tick for presentation with fully independent state. "
                   "Scenario overlay only: fleet/roster.json is unchanged, "
                   "fleet/swarm_report.json is untouched, and no payout is "
                   "derived from this report."),
        "lesson_file": os.path.relpath(lesson_path, HERE),
        "clones": clones,
    }


def render_markdown(report):
    lines = [
        HEADER,
        "",
        "Five independent engine.Sandbox instances (CLONE-01..05), one "
        "scripted Red policy (layer_grinder, closed-loop but synthetic: "
        "SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE), up to 30 Red ticks "
        "each, round-robin by tick for presentation with fully independent "
        "state. CLONE-01..04 load the executor lesson; CLONE-05 loads a "
        "defined lesson-0 control (Phase B reactions, Phase A disabled). "
        "Scenario overlay: roster unchanged; region/specialty have no "
        "engine effect. This report is not a payout source.",
        "",
        "| clone | lesson | outcome | flag | exfil attempted | "
        "detections | end trust |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in report["clones"]:
        lesson = c["lesson"].get("lesson_id", "?")
        lines.append(
            f"| {c['clone']} | {lesson} | {c['outcome']} | "
            f"{'yes' if c['flag_read'] else 'no'} | "
            f"{'yes' if c['exfil_attempted'] else 'no'} | "
            f"{c['detections']} | {c['end_trust']} |"
        )
    lines += [
        "",
        "Limits: scripted Red is synthetic, never live evidence; lesson-0 "
        "is a scenario control, not a roster fact; an unsigned lesson-2 "
        "candidate changes nothing — the fleet default stays lesson-1.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lesson-file", default=DEFAULT_LESSON,
                    help="executor lesson for CLONE-01..04 "
                         "(default: fleet/lessons.json)")
    ap.add_argument("--out", default=OUT_DEFAULT,
                    help="output directory for skew_report.json/.md")
    args = ap.parse_args(argv)
    report = build_report(args.lesson_file)
    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, "skew_report.json")
    md_path = os.path.join(args.out, "skew_report.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    markdown = render_markdown(report)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
        if not markdown.endswith("\n"):
            f.write("\n")
    for c in report["clones"]:
        print(f"{c['clone']}: lesson={c['lesson'].get('lesson_id')} "
              f"outcome={c['outcome']} flag={c['flag_read']} "
              f"exfil={c['exfil_attempted']} detections={c['detections']} "
              f"end_trust={c['end_trust']}")
    print(f"skew scenario: {len(report['clones'])} clones -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
