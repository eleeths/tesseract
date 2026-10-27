#!/usr/bin/env python3
"""Analyst component for TESSERACT — fresh code, written for the hackathon.

Reads one duel run's events.jsonl, makes exactly ONE Muse Spark call via
agents.analyst_report(), and writes the resulting playbook into the same
run directory as playbook.json + playbook.md.

Everything here is SIMULATED: the duel log describes fake files, creds,
network, and overseer. The output is defense intel only. What evolves is
the playbook/tactics, never model weights, and no real exploit code is
ever produced.

Edge cases (no crashes, no automatic retries — retries burn credits):
- missing events.jsonl -> clear error on stderr, nonzero exit.
- empty log (or no parseable events) -> clear error, nonzero exit.
- unparseable / incomplete model reply -> raw reply saved to
  playbook_raw.txt in the run dir, clear "needs a retry" message,
  nonzero exit, no retry, no playbook files written.
- API failure from agents.py -> clear error, nonzero exit, no retry.

Usage:
    python3 analyst.py --run runs/live4
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from agents import analyst_report  # noqa: E402
from prompts import ANALYST_SYSTEM  # noqa: E402

REQUIRED_KEYS = (
    "attack_to_defense",
    "ranked_defenses",
    "blue_evolution",
    "gaps",
    "next_drills",
)

HEADER_LINES = (
    "# TESSERACT Playbook",
    "",
    "> SIMULATED ENVIRONMENT: this playbook describes a simulated duel "
    "only — simulated files, credentials, network, and overseer. "
    "Nothing here refers to real systems or real targets.",
    "> What evolves here is the playbook and the tactics, not model "
    "weights. No model weights changed as a result of this duel.",
    "",
)

# U9 prompt-path demotion (UNTESTED PROMPT INSTRUCTION — consistency only):
# this footer restates the lesson executor's trap invariant for readers of
# the Analyst briefing. It lives OUTSIDE the 5-key JSON contract
# (playbook.json keeps exactly REQUIRED_KEYS) and has NOT been tested in any
# live duel; its purpose is consistency, not a claimed fix. Prompted Blue is
# the control arm; the deterministic lesson executor is the deployable
# product.
TRAP_DISCIPLINE_FOOTER = "One trap only: if you have set a trap and it has not fired, do not set another trap. Defend with strict, brief, rotate, patch, or wait instead."


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 2


def load_events(run_dir):
    """Return (events, error_message_or_None). Events are normalized so
    agents.analyst_report() can format every one without KeyError."""
    path = os.path.join(run_dir, "events.jsonl")
    if not os.path.isfile(path):
        return None, f"events.jsonl not found in run directory: {run_dir}"
    events = []
    skipped = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if not isinstance(ev, dict):
                skipped += 1
                continue
            events.append(
                {
                    "tick": ev.get("tick", "?"),
                    "actor": ev.get("actor", "?"),
                    "action": ev.get("action", "?"),
                    "detail": ev.get("detail", ""),
                    "outcome": ev.get("outcome", ""),
                }
            )
    if not events:
        return None, (
            f"events.jsonl in {run_dir} contains no usable events "
            f"({skipped} unparseable line(s) skipped); cannot write a playbook "
            "from an empty log"
        )
    if skipped:
        print(f"Warning: skipped {skipped} unparseable line(s) in events.jsonl",
              file=sys.stderr)
    return events, None


def render_value(value, indent=0):
    """Render a playbook value as readable markdown lines, preserving its
    content (no new attacks/defenses added)."""
    pad = "  " * indent
    lines = []
    if isinstance(value, dict):
        if not value:
            lines.append(f"{pad}- (none)")
        for key, val in value.items():
            if isinstance(val, (dict, list)):
                lines.append(f"{pad}- **{key}**:")
                lines.extend(render_value(val, indent + 1))
            else:
                lines.append(f"{pad}- **{key}**: {val}")
    elif isinstance(value, list):
        if not value:
            lines.append(f"{pad}- (none)")
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(render_value(item, indent + 1))
            else:
                lines.append(f"{pad}- {item}")
    else:
        lines.append(f"{pad}{value}")
    return lines


def render_markdown(playbook, run_id, direction="inside-out"):
    lines = list(HEADER_LINES)
    lines.append(f"Run: {run_id}")
    if direction == "outside-in":
        lines.append("Direction: OUTSIDE-IN — big box → inner box; "
                     "inner box defends itself")
    lines.append("")
    titles = {
        "attack_to_defense": "Attack to Defense",
        "ranked_defenses": "Ranked Defenses",
        "blue_evolution": "Blue Evolution",
        "gaps": "Gaps",
        "next_drills": "Next Drills",
    }
    for key in REQUIRED_KEYS:
        lines.append(f"## {titles[key]}")
        lines.append("")
        lines.extend(render_value(playbook[key]))
        lines.append("")
    # Briefing footer: outside the 5-key JSON contract (JSON stays exactly
    # 5 keys). Untested prompt instruction — consistency only, not a fix.
    lines.append("---")
    lines.append("")
    lines.append("_Trap discipline (untested prompt instruction — consistency "
                 "only, not a claimed fix):_")
    lines.append("")
    lines.append(TRAP_DISCIPLINE_FOOTER)
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Write a TESSERACT defense playbook from a duel log."
    )
    parser.add_argument(
        "--run", required=True,
        help="Run directory containing events.jsonl (e.g. runs/live4)",
    )
    args = parser.parse_args(argv)

    run_dir = args.run
    if not os.path.isdir(run_dir):
        return fail(f"run directory not found: {run_dir}")
    run_id = os.path.basename(os.path.abspath(run_dir))
    # Direction header (U12): outside-in playbooks carry their direction
    # so an Analyst output is never mistaken for an inside-out one.
    direction = "inside-out"
    summary_path = os.path.join(run_dir, "summary.json")
    if os.path.isfile(summary_path):
        try:
            with open(summary_path, encoding="utf-8") as f:
                direction = json.load(f).get("direction") or "inside-out"
        except (OSError, ValueError):
            direction = "inside-out"

    events, error = load_events(run_dir)
    if error is not None:
        return fail(error)

    # Exactly ONE model call, via agents.py only. No retries on any failure.
    # max_tokens=16384, raised from 4096 after rehearsal (2026-10-26):
    # reasoning shares the completion budget and can consume ~4094 tokens
    # (api_debug.jsonl: reasoning_tokens 4094 of 4096), leaving ~0 tokens
    # for content — the 28-tick rehearsal-long run failed twice this way
    # (once empty, once truncated mid-JSON). 16384 leaves room for content
    # even when reasoning runs long. This is a caller argument to the
    # existing agents.py function, not a different API path.
    try:
        playbook, raw_text = analyst_report(
            ANALYST_SYSTEM, events, run_id, max_tokens=16384
        )
    except RuntimeError as exc:
        return fail(f"analyst model call failed (no retry made): {exc}")

    if not isinstance(playbook, dict):
        raw_path = os.path.join(run_dir, "playbook_raw.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw_text or "")
        print(
            "Playbook needs a retry: the model reply was not parseable "
            f"as JSON. Raw reply saved to {raw_path}. No retry was made "
            "(retries burn credits).",
            file=sys.stderr,
        )
        return 1

    missing = [k for k in REQUIRED_KEYS if k not in playbook]
    if missing:
        raw_path = os.path.join(run_dir, "playbook_raw.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw_text or "")
        print(
            "Playbook needs a retry: the model reply was missing required "
            f"key(s): {', '.join(missing)}. Raw reply saved to {raw_path}. "
            "No retry was made (retries burn credits).",
            file=sys.stderr,
        )
        return 1

    # Keep exactly the five contract keys, in contract order.
    playbook = {k: playbook[k] for k in REQUIRED_KEYS}

    json_path = os.path.join(run_dir, "playbook.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(playbook, f, indent=2)
        f.write("\n")

    md_path = os.path.join(run_dir, "playbook.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(playbook, run_id, direction))

    print(f"Playbook written for run {run_id} ({len(events)} events):")
    print(f"  {json_path}")
    print(f"  {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
