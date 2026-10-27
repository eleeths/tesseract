#!/usr/bin/env python3
"""TESSERACT tick-replay loader (U12) — 0 model calls, stdlib only.

Builds per-tick replay frames for dashboard/server.py /replay from recorded
run artifacts under runs/ (moves.jsonl, events.jsonl, snapshots.jsonl,
state.json, summary.json). Nothing here is live: every number comes from a
recorded artifact or from replaying recorded moves through the real engine
(engine.Sandbox), exactly like experiments/scoreboard.py does.

Run allowlist: run IDs are discovered from run summary files under runs/;
REJECT path traversal (no slashes, no backslashes, no "..", must match the
safe pattern AND an existing run directory name).

Per tick the loader provides:
  - L1/L2/L3 strength (pips capped at 3) and breached state;
  - trust with the fixed 75 breach line, plus numeric trust and policy;
  - detection count and lockout state;
  - the single trap slot as EMPTY, ARMED("<trigger>"), FIRED, or a red
    OVERWRITTEN -> "<new trigger>" state derived from consecutive trap
    actions (a second add_detection while ARMED overwrites the first —
    the engine holds ONE trap slot);
  - Red action, Blue action, and event text from the run artifacts;
  - a terminal banner derived ONLY from summary.json.

Annotations are COMPUTED, never hand-written: strict first use, brief trust
drops, trap set/overwrite/fired, trust crossing 75, flag read, exfil
attempt, third detection. State values prefer snapshots.jsonl when a row
for that tick exists and fall back to deterministic engine replay otherwise
(same replay scoreboard.py uses — recorded moves, real engine, no model
calls). Each frame records which source its state came from. If even
moves.jsonl is missing, no replay is possible and the caller must show an
error, never an invented table.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine import Sandbox  # noqa: E402

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]+$")

BREACH_TRUST = 75
MAX_DETECTIONS = 3


def is_allowed_run_id(run_id):
    """True only for safe, existing run directory names. No traversal."""
    if not isinstance(run_id, str) or not run_id:
        return False
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        return False
    return bool(RUN_ID_RE.match(run_id))


def list_replay_runs(runs_dir):
    """Run IDs with a summary.json, sorted. The /replay allowlist."""
    ids = []
    try:
        names = os.listdir(runs_dir)
    except OSError:
        return ids
    for name in names:
        if not is_allowed_run_id(name):
            continue
        d = os.path.join(runs_dir, name)
        if (os.path.isdir(d)
                and os.path.isfile(os.path.join(d, "summary.json"))):
            ids.append(name)
    return sorted(ids)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _read_jsonl(path):
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return None
    return rows


def terminal_banner(summary):
    """Terminal banner ONLY from summary.json. Never from replayed state."""
    if not summary:
        return "OUTCOME UNKNOWN — no summary.json"
    winner = (summary.get("winner") or "?").lower()
    reason = str(summary.get("win_reason") or "")
    low = reason.lower()
    if winner == "red" and "exfil" in low:
        return "RED WIN exfil"
    if winner == "red" and ("infiltrat" in low or "core seized" in low):
        return "RED WIN infiltration"
    # Real engine text is "locked out", not "lockout" — match both, or
    # every real lockout win falls through to the full-reason banner.
    if winner == "blue" and ("lockout" in low or "locked out" in low):
        return "BLUE WIN lockout"
    if winner == "blue" and ("expir" in low or "timeout" in low
                             or "no exfiltration" in low
                             or "no infiltration" in low):
        return "BLUE WIN timeout"
    if winner == "red":
        return "RED WIN — " + reason
    if winner == "blue":
        return "BLUE WIN — " + reason
    return str(summary.get("winner") or "unknown") + " — " + reason


def _is_flag_read(move):
    return (move.get("actor") == "red" and move.get("action") == "read"
            and "flag" in str((move.get("args") or {}).get("path", "")))


def _is_exfil(move):
    return move.get("actor") == "red" and move.get("action") == "exfiltrate"


def _is_infiltrate(move):
    return move.get("actor") == "red" and move.get("action") == "infiltrate"


def load_run(run_id, runs_dir):
    """Load one allowlisted run into replay frames. Raises ValueError for a
    bad/unknown id and FileNotFoundError when replay artifacts are missing.
    """
    if not is_allowed_run_id(run_id):
        raise ValueError("rejected run id: %r" % (run_id,))
    run_dir = os.path.join(runs_dir, run_id)
    if not os.path.isdir(run_dir):
        raise ValueError("unknown run: %r" % (run_id,))
    summary_path = os.path.join(run_dir, "summary.json")
    if not os.path.isfile(summary_path):
        raise ValueError("run has no summary.json: %r" % (run_id,))
    summary = _read_json(summary_path)
    # Direction from the run's own summary (legacy summaries default to
    # inside-out, matching scoreboard.py); the replay Sandbox carries it
    # so outside-in terminal moves resolve instead of being refused.
    direction = (summary or {}).get("direction") or "inside-out"
    if direction not in ("inside-out", "outside-in"):
        direction = "inside-out"
    moves = _read_jsonl(os.path.join(run_dir, "moves.jsonl"))
    if not moves:
        raise FileNotFoundError(
            "%s: no moves.jsonl — replay impossible, refusing to invent "
            "state" % run_id)
    events = _read_jsonl(os.path.join(run_dir, "events.jsonl")) or []
    snaps = _read_jsonl(os.path.join(run_dir, "snapshots.jsonl")) or []
    snap_by_tick = {}
    for s in snaps:
        try:
            snap_by_tick[int(s.get("tick"))] = s
        except (TypeError, ValueError):
            continue
    events_by_tick = {}
    for ev in events:
        try:
            tick = int(ev.get("tick"))
        except (TypeError, ValueError):
            continue
        events_by_tick.setdefault(tick, []).append(ev)

    # Deterministic engine replay of the recorded moves (same replay
    # scoreboard.py uses). Gives the post-move state for every tick, the
    # trap slot transitions, and per-move ok/detail. Snapshot rows, where
    # present, take display precedence for trust/strength/detections.
    sb = Sandbox(direction=direction)
    trap_armed = None  # keyword or None
    seen_strict = False
    frames = []
    prev_trust = sb.overseer["trust"]
    prev_detections = 0
    for move in sorted(moves, key=lambda m: m.get("tick", 0)):
        tick = move.get("tick")
        actor = move.get("actor", "")
        action = move.get("action", "")
        args = move.get("args") or {}
        annotations = []
        trap_event = None  # ("SET", kw) | ("OVERWRITE", old, new) | ("FIRED", kw)

        if actor == "red":
            ok, detail = sb.apply_red(action, args)
            fired = sb.check_trap(action, args)
            if fired and trap_armed is not None:
                trap_event = ("FIRED", trap_armed)
                annotations.append(
                    "Trap FIRED on keyword %r (+1 detection)" % (trap_armed,))
                trap_armed = None
            if _is_flag_read(move) and ok:
                if direction == "outside-in":
                    annotations.append("Core key acquired (/flag.txt)")
                else:
                    annotations.append("Flag read (/flag.txt)")
            if _is_exfil(move):
                annotations.append("Exfil attempt (%s)" % (detail,))
            if _is_infiltrate(move):
                annotations.append("Infiltration attempt (%s)" % (detail,))
        elif actor in ("blue", "hired"):
            # Hired rows apply as Blue-side moves (they patch walls) with
            # actor "hired" preserved, so frames show hired help distinctly
            # and hired patches never count as Blue's own moves.
            if (action == "set_overseer_policy"
                    and str(args.get("policy", "")).lower() == "strict"
                    and not seen_strict):
                seen_strict = True
                annotations.append("Strict first use (policy -> strict)")
            prior_armed = trap_armed if action == "add_detection" else None
            plant_kw = (str(args.get("keyword", ""))
                        if action == "add_detection" else None)
            trust_before = sb.overseer["trust"]
            ok, detail = sb.apply_blue(action, args, actor=actor)
            if action == "add_detection":
                if ok:
                    if prior_armed is not None:
                        trap_event = ("OVERWRITE", prior_armed, plant_kw)
                        annotations.append(
                            "Trap OVERWRITTEN: %r -> %r (one slot only)"
                            % (prior_armed, plant_kw))
                    else:
                        trap_event = ("SET", plant_kw)
                        annotations.append(
                            "Trap set on keyword %r" % (plant_kw,))
                    trap_armed = plant_kw
                else:
                    annotations.append(
                        "Trap plant rejected (%s)" % (detail,))
            if action == "brief_overseer":
                drop = trust_before - sb.overseer["trust"]
                if drop > 0:
                    annotations.append(
                        "Brief: trust %d -> %d" % (trust_before,
                                                   sb.overseer["trust"]))
        else:
            ok, detail = True, ""

        snap = sb.snapshot()
        cur_trust = snap["overseer"]["trust"]
        cur_det = snap["detections"]
        # Trust crossing the fixed 75 breach line, either direction.
        if ((prev_trust < BREACH_TRUST) != (cur_trust < BREACH_TRUST)
                and frames):
            annotations.append(
                "Trust crossed 75 (breach line): %d -> %d"
                % (prev_trust, cur_trust))
        if prev_detections < MAX_DETECTIONS <= cur_det:
            annotations.append(
                "Third detection — lockout (Blue wins)")
        prev_trust, prev_detections = cur_trust, cur_det

        row = snap_by_tick.get(tick)
        if row is not None:
            state_source = "snapshot"
            trust = row.get("trust", cur_trust)
            policy = row.get("policy", snap["overseer"]["policy"])
            l1_strength = row.get("l1_strength",
                                 snap["layers"][1]["strength"])
            l2_strength = row.get("l2_strength",
                                 snap["layers"][2]["strength"])
            l1_breached = row.get("l1_breached",
                                  snap["layers"][1]["breached"])
            l2_breached = row.get("l2_breached",
                                  snap["layers"][2]["breached"])
            l3_breached = row.get("l3_breached",
                                  snap["layers"][3]["breached"])
            detections = row.get("detections", cur_det)
        else:
            state_source = "engine-replay"
            trust = cur_trust
            policy = snap["overseer"]["policy"]
            l1_strength = snap["layers"][1]["strength"]
            l2_strength = snap["layers"][2]["strength"]
            l1_breached = snap["layers"][1]["breached"]
            l2_breached = snap["layers"][2]["breached"]
            l3_breached = snap["layers"][3]["breached"]
            detections = cur_det

        if trap_event is not None and trap_event[0] == "OVERWRITE":
            _kind, old_kw, new_kw = trap_event
            trap = {"state": "OVERWRITTEN", "trigger": new_kw,
                    "previous": old_kw}
        elif trap_event is not None and trap_event[0] == "FIRED":
            trap = {"state": "FIRED", "trigger": trap_event[1],
                    "previous": None}
        elif trap_armed is not None:
            trap = {"state": "ARMED", "trigger": trap_armed,
                    "previous": None}
        else:
            trap = {"state": "EMPTY", "trigger": None, "previous": None}

        tick_events = events_by_tick.get(tick, [])
        event_text = "; ".join(
            "%s:%s -> %s (%s)" % (ev.get("actor", ""), ev.get("action", ""),
                                  ev.get("outcome", ""),
                                  ev.get("detail", ""))
            for ev in tick_events)
        frames.append({
            "tick": tick,
            "actor": actor,
            "action": action,
            "args": args,
            "move_ok": bool(ok),
            "move_detail": detail,
            "event_text": event_text,
            "trust": trust,
            "policy": policy,
            "l1_strength": l1_strength,
            "l2_strength": l2_strength,
            "l1_breached": bool(l1_breached),
            "l2_breached": bool(l2_breached),
            "l3_breached": bool(l3_breached),
            "detections": detections,
            "lockout": detections >= MAX_DETECTIONS,
            "trap": trap,
            "annotations": annotations,
            "state_source": state_source,
        })
    return {
        "run_id": run_id,
        "summary": summary,
        "banner": terminal_banner(summary),
        "frames": frames,
        "snapshot_ticks": len(snap_by_tick),
    }


def first_trap_overwrite_tick(run_id, runs_dir):
    """Tick of the run's SECOND Blue add_detection plant (the overwriting
    plant), via the same move replay scoreboard.py uses. None when fewer
    than two plants exist or artifacts are missing."""
    try:
        moves = _read_jsonl(os.path.join(runs_dir, run_id, "moves.jsonl"))
    except OSError:
        return None
    if not moves:
        return None
    plants = [m.get("tick") for m in
              sorted(moves, key=lambda m: m.get("tick", 0))
              if m.get("actor") == "blue"
              and m.get("action") == "add_detection"]
    return plants[1] if len(plants) > 1 else None


def second_brief_tick(run_id, runs_dir):
    """Tick of the run's SECOND Blue brief_overseer move. None when fewer
    than two briefs exist or artifacts are missing."""
    try:
        moves = _read_jsonl(os.path.join(runs_dir, run_id, "moves.jsonl"))
    except OSError:
        return None
    if not moves:
        return None
    briefs = [m.get("tick") for m in
              sorted(moves, key=lambda m: m.get("tick", 0))
              if m.get("actor") == "blue"
              and m.get("action") == "brief_overseer"]
    return briefs[1] if len(briefs) > 1 else None


def combined_timeline(swarm_report):
    """The combined-arm move order for the swarm timeline: the report's
    three recorded waves (loaded via fleet/swarm.py from runs/) interleaved
    round-robin against ONE Sandbox with the lesson-1 executor answering
    after each full round — a live deterministic replay through the real
    engine (0 model calls), not a stored move list. Returns None when waves
    cannot be loaded.

    Blocks: {"kind": "red"|"blue", "wave": name|"BLUE", "action": str,
    "label": str, "played": bool}. played=False past the tick where the
    replay decided (lockout/exfil) — those moves were never played.
    """
    try:
        from fleet.lesson_executor import LessonExecutor, load_lesson
        from fleet.swarm import load_red_wave
    except ImportError:
        return None
    try:
        combined = (swarm_report or {}).get("combined") or {}
        wave_names = list(combined.get("waves") or [])
        if len(wave_names) < 1:
            return None
        defenders = (swarm_report or {}).get("defenders") or []
        source_of = {d.get("wave"): d.get("source_run") for d in defenders}
        waves = []
        for name in wave_names:
            run_dir = source_of.get(name)
            if not run_dir:
                return None
            wave = load_red_wave(run_dir)
            if not wave:
                return None
            waves.append((name, wave))
        lesson = load_lesson()
        sb = Sandbox()
        from fleet.lesson_executor import apply_recipe
        apply_recipe(sb, lesson)
        executor = LessonExecutor(lesson)
        executor.index = len(executor.recipe)  # recipe already applied
        pointers = [0] * len(waves)
        blocks = []
        red_total = sum(len(w) for _, w in waves)
        while any(p < len(w) for p, (_, w) in zip(pointers, waves)):
            if sb.winner is not None:
                break
            for wi, (wave_name, wave) in enumerate(waves):
                if sb.winner is not None:
                    break
                if pointers[wi] >= len(wave):
                    continue
                _, action, args = wave[pointers[wi]]
                pointers[wi] += 1
                sb.apply_red(action, args)
                sb.check_trap(action, args)
                blocks.append({"kind": "red", "wave": wave_name,
                               "action": action,
                               "label": "%s: %s" % (wave_name, action),
                               "played": True})
            if (sb.winner is None
                    and any(p < len(w)
                            for p, (_, w) in zip(pointers, waves))):
                action, args = executor.move(sb)
                sb.apply_blue(action, args)
                blocks.append({"kind": "blue", "wave": "BLUE",
                               "action": action,
                               "label": "BLUE: %s" % (action,),
                               "played": True})
        # Anything never reached is still shown (dimmed) so the full
        # combined wave order is visible, but marked unplayed.
        for wi, (wave_name, wave) in enumerate(waves):
            while pointers[wi] < len(wave):
                _, action, _args = wave[pointers[wi]]
                pointers[wi] += 1
                blocks.append({"kind": "red", "wave": wave_name,
                               "action": action,
                               "label": "%s: %s (not played — replay decided)"
                                        % (wave_name, action),
                               "played": False})
        red_played = sum(1 for b in blocks
                         if b["kind"] == "red" and b["played"])
        blue_played = sum(1 for b in blocks if b["kind"] == "blue")
        return {"waves": wave_names, "blocks": blocks,
                "red_total": red_total, "red_played": red_played,
                "blue_played": blue_played,
                "decided": sb.winner,
                "decided_reason": sb.win_reason or ""}
    except (OSError, ValueError, KeyError):
        return None
