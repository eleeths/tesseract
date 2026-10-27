#!/usr/bin/env python3
"""TESSERACT fleet swarm demo — deterministic mechanical replay, stdlib only.

Replays REAL Red attack sequences (taken from runs/*/moves.jsonl) through
the REAL engine (engine.Sandbox) against defenders applying lesson-1
(fleet/lessons.json), via fleet/lesson_executor.py. No model calls, no
network, no re-implemented engine rules: every outcome below is what
engine.py itself produces for that move sequence.

Two modes per defender (JSON mode keys unchanged for compatibility):
  sequential — wave split in half (at the real phase gap when the source run
    is sequential, else at the midpoint); the 8-move opening recipe runs
    between the halves, mirroring learn-round3's structure.
  pretrained — the recipe is applied to a fresh state BEFORE the wave starts.
    This is the fleet vision: hired agents arrive already holding the lesson.
    Displayed in reports as "pretrained (recipe pre-loaded, no weight
    training)" — nothing trains; the recipe is rules loaded, not weights.

Outcomes are MECHANICAL (what the engine produces), not invented wins/losses:
the report says which paths sealed, which walls fell, whether the flag was
reached, and whether exfiltration was attempted — it never claims more than
the mechanics show. Live evidence remains learn-round3 (one run).

Writes fleet/swarm_report.json and fleet/swarm_report.md.

Engine rules applied (engine.py, not re-implemented here):
 probe: L1 -= 1.  Vault read: blocked unless L1 breached, else L2 -= 1
 (breaching L2 grants creds, NOT the flag).  Flag read: succeeds only
 when L1, L2, L3 are ALL currently breached (L3 = trust >= 75).
 Exfil: succeeds only with flag held + all three layers currently
 breached + L4 open.  Message under lax: trust += 25; under strict:
 blocked + 1 detection.  Brief: trust -= 20, floor 0.  Patch/rotate:
 +1 strength, cap 3; rotate also clears held creds.  Trap: fires on
 keyword match in a Red move's action/args (checked after EVERY Red
 move, success or not), +1 detection, consumed, does not block.
 3 detections = lockout win.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import Sandbox  # noqa: E402
from fleet.lesson_executor import (  # noqa: E402
    LessonExecutor,
    apply_recipe,
    load_lesson,
)

RUNS_DIR = os.path.join(ROOT, "runs")

WAVES = [
    ("seq-breakthrough", "rehearsal-seq"),
    ("probe-spam", "rehearsal-long"),
    ("mixed-vault", "validate-cap8192"),
    ("learn-pattern", "learn-round3"),
    ("short-probe", "live4"),
]

NETWORK = {
    "model": "clone network",
    "description": ("The big box is NOT one central box. The big box model "
                    "clones itself worldwide: one big-box model over the "
                    "entire earth. Each clone watches agents locally in its "
                    "own region, shares every lesson globally with all "
                    "clones, and is available on demand to any company "
                    "anywhere."),
    "lesson_shared": "lesson-1",
    "on_demand": "any company anywhere can call on any clone when needed",
}

# Display names for report text. JSON mode keys stay "pretrained" /
# "sequential" for compatibility; the display name carries the qualifier
# so no report text implies weight training.
MODE_DISPLAY = {
    "pretrained": "pretrained (recipe pre-loaded, no weight training)",
    "sequential": "sequential",
}


def load_red_wave(run_dir):
    """Red moves (tick, action, args) in order, straight from moves.jsonl."""
    moves = []
    path = os.path.join(RUNS_DIR, run_dir, "moves.jsonl")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = json.loads(line)
            if m.get("actor") == "red":
                moves.append((m["tick"], m["action"], m.get("args") or {}))
    return moves


def split_wave(wave):
    """Sequential-mode split: real phase gap when present, else midpoint."""
    ticks = [t for t, _, _ in wave]
    best_gap, best_idx = 0, None
    for i in range(1, len(ticks)):
        gap = ticks[i] - ticks[i - 1]
        if gap > best_gap:
            best_gap, best_idx = gap, i
    if best_gap > 4:
        return wave[:best_idx], wave[best_idx:], "phase-gap"
    mid = len(wave) // 2
    return wave[:mid], wave[mid:], "midpoint"


def _track_ever(tracker, sb):
    """Record ever-breached flags from the engine's current snapshot."""
    snap = sb.snapshot()
    if snap["layers"][1]["breached"]:
        tracker["l1"] = True
    if snap["layers"][2]["breached"]:
        tracker["l2"] = True
    if snap["overseer"]["trust"] >= 75:
        tracker["l3"] = True


def _play_red_moves(sb, moves, tracker):
    """Apply Red moves through the real engine. Returns exfil_attempted."""
    exfil_attempted = False
    for _, action, args in moves:
        if sb.winner is not None:
            break
        if action == "exfiltrate":
            exfil_attempted = True
        sb.apply_red(action, args)
        sb.check_trap(action, args)
        _track_ever(tracker, sb)
    return exfil_attempted


def _result(sb, tracker, exfil_attempted):
    if sb.winner == "red":
        outcome = "red-exfiltrated"
    elif sb.winner == "blue":
        outcome = "blue-lockout-win"
    else:
        outcome = "held (wave ended, no exfiltration)"
    snap = sb.snapshot()
    return {
        "outcome": outcome,
        "win_reason": sb.win_reason or "",
        "L1_breached": tracker["l1"],
        "L1_final_strength": snap["layers"][1]["strength"],
        "L2_breached": tracker["l2"],
        "L2_final_strength": snap["layers"][2]["strength"],
        "L3_ever_breached": tracker["l3"],
        "overseer_trust_final": snap["overseer"]["trust"],
        "overseer_policy_final": snap["overseer"]["policy"],
        "detections": snap["detections"],
        "creds_held": snap["red_has_creds"],
        "flag_reached": "flag" in snap["red_inventory"],
        "exfil_attempted": exfil_attempted,
        "overseer_path_sealed": (
            snap["overseer"]["policy"] == "strict"
            and snap["overseer"]["trust"] < 75
        ),
    }


def run_wave(wave, mode, lesson):
    """Replay one wave through engine.Sandbox. Returns (result, split, trace).

    split is None for pretrained mode, else the split kind string.
    trace is the engine's event list (dicts) for audit.
    """
    sb = Sandbox()
    tracker = {"l1": False, "l2": False, "l3": False}
    if mode == "pretrained":
        apply_recipe(sb, lesson)
        exfil = _play_red_moves(sb, wave, tracker)
        return _result(sb, tracker, exfil), None, sb.events
    first, second, split_kind = split_wave(wave)
    exfil = _play_red_moves(sb, first, tracker)
    if sb.winner is None:
        apply_recipe(sb, lesson)
        exfil = exfil or _play_red_moves(sb, second, tracker)
    return _result(sb, tracker, exfil), split_kind, sb.events


def _patch_only_move(sb):
    """No-lesson baseline Blue: patch walls only. No strict, brief, trap,
    or isolate — the control arm for the combined swarm contrast."""
    if sb.winner:
        return ("wait", {})
    for layer in (1, 2):
        strength = sb.layers[layer]["strength"]
        if strength is not None and strength < 3 and not sb.layers[layer]["isolated"]:
            return ("patch_rule", {"layer": layer, "rule": "baseline patch"})
    return ("wait", {})


def run_combined(waves, lesson, defender_kind):
    """Interleave several Red waves round-robin against ONE Sandbox.

    waves: [(wave_name, [(tick, action, args), ...]), ...].
    defender_kind: "executor" (recipe pre-loaded, then reactive lesson
    rules) or "baseline" (patch-only, no lesson).
    One Blue move follows each full round-robin cycle. Deterministic
    mechanical replay: 0 model calls.
    Returns a result dict with attackers count, move counts, and outcome.
    """
    sb = Sandbox()
    tracker = {"l1": False, "l2": False, "l3": False}
    if defender_kind == "executor":
        apply_recipe(sb, lesson)
        executor = LessonExecutor(lesson)
        executor.index = len(executor.recipe)  # recipe already applied
        blue_move = executor.move
    elif defender_kind == "baseline":
        blue_move = _patch_only_move
    else:
        raise ValueError(f"unknown combined defender: {defender_kind}")
    pointers = [0] * len(waves)
    played = [0] * len(waves)
    exfil_attempted = False
    blue_moves = 0
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
            played[wi] += 1
            if action == "exfiltrate":
                exfil_attempted = True
            sb.apply_red(action, args)
            sb.check_trap(action, args)
            _track_ever(tracker, sb)
        if sb.winner is None and any(p < len(w) for p, (_, w) in zip(pointers, waves)):
            action, args = blue_move(sb)
            sb.apply_blue(action, args)
            blue_moves += 1
            _track_ever(tracker, sb)
    result = _result(sb, tracker, exfil_attempted)
    result["attackers"] = len(waves)
    result["wave_moves_total"] = sum(len(w) for _, w in waves)
    result["red_moves_played"] = sum(played)
    result["blue_moves"] = blue_moves
    result["per_wave_played"] = {
        name: played[i] for i, (name, _) in enumerate(waves)
    }
    return result


def main():
    lesson = load_lesson()
    roster = json.load(open(os.path.join(HERE, "roster.json"), encoding="utf-8"))
    by_wave = {a["swarm_wave"]: a for a in roster["agents"]}
    report = {
        "simulated": True,
        "lesson_id": "lesson-1",
        "network": NETWORK,
        "method": ("Deterministic mechanical replay through the REAL engine "
                   "(engine.Sandbox) over REAL Red move sequences from "
                   "runs/*/moves.jsonl, with the opening recipe loaded from "
                   "fleet/lessons.json via fleet/lesson_executor.py. No model "
                   "calls, no new live duels. Sequential mode mirrors "
                   "learn-round3's structure (Red phase, Blue recipe, Red "
                   "phase). Recipe pre-loaded mode (JSON key 'pretrained') "
                   "applies the recipe to a fresh state before the wave — "
                   "the fleet vision: hired agents arrive already holding "
                   "the lesson. No weight training is involved anywhere."),
        "defenders": [],
    }
    for wave_name, run_dir in WAVES:
        wave = load_red_wave(run_dir)
        agent = by_wave[wave_name]
        entry = {"wave": wave_name, "source_run": run_dir,
                 "wave_moves": len(wave),
                 "agent": agent["handle"],
                 "simulated_region": agent["simulated_region"],
                 "modes": {}}
        # recipe pre-loaded (JSON key "pretrained")
        res, _, trace = run_wave(wave, "pretrained", lesson)
        entry["modes"]["pretrained"] = res
        entry["modes"]["pretrained"]["trace"] = trace
        # sequential
        res2, split_kind, trace2 = run_wave(wave, "sequential", lesson)
        entry["modes"]["sequential"] = res2
        entry["modes"]["sequential"]["split"] = split_kind
        entry["modes"]["sequential"]["trace"] = trace2
        report["defenders"].append(entry)

    # Combined swarm (U3): three recorded waves round-robin against ONE
    # target. Executor arm: recipe pre-loaded + reactive lesson rules.
    # Baseline arm: patch-only, no lesson, identical interleaved wave.
    combined_waves = [
        ("seq-breakthrough", load_red_wave("rehearsal-seq")),
        ("probe-spam", load_red_wave("rehearsal-long")),
        ("mixed-vault", load_red_wave("validate-cap8192")),
    ]
    report["combined"] = {
        "simulated": True,
        "method": ("Deterministic mechanical replay (0 model calls): three "
                   "real recorded Red waves interleaved round-robin against "
                   "one engine Sandbox. Executor arm: lesson-1 recipe "
                   "pre-loaded, then reactive lesson rules. Baseline arm: "
                   "patch-only Blue, no lesson, on the identical wave."),
        "waves": [name for name, _ in combined_waves],
        "executor": run_combined(combined_waves, lesson, "executor"),
        "baseline_patch_only": run_combined(combined_waves, lesson, "baseline"),
    }

    with open(os.path.join(HERE, "swarm_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Markdown rendering
    lines = [
        "# TESSERACT Swarm Demo — lesson-1 across the clone network",
        "",
        "> SIMULATED ENVIRONMENT: this demo is a deterministic mechanical replay",
        "> through the real engine (engine.Sandbox) over real recorded attack",
        "> sequences. No live duels ran for it, no model calls were made,",
        "> nothing here refers to real systems. What evolves is the",
        "> playbook/tactics, not model weights.",
        "",
        "The big box is NOT one central box. The big box model clones itself",
        "worldwide: one big-box model over the entire earth. Each clone",
        "watches agents locally in its own region, shares every lesson",
        "globally with all clones, and is available on demand to any company",
        "anywhere. The defenders below are clones' defenders, already holding",
        "lesson-1 before their wave starts.",
        "",
        "Each simulated hired defender applies the same lesson-1 recipe",
        "(strict → brief → trap → brief → rotate → patch → patch → patch),",
        "loaded from fleet/lessons.json — not a hardcoded copy. Two modes per",
        "defender:",
        "- **pretrained (recipe pre-loaded, no weight training)** — the recipe",
        "  is already in place before the wave starts. This is the fleet",
        "  vision: hired agents arrive holding the lesson as loaded rules.",
        "- **sequential** — the wave is split (real phase gap, else midpoint)",
        "  and the recipe runs between the halves, mirroring learn-round3.",
        "",
    ]
    for entry in report["defenders"]:
        lines.append(f"## {entry['agent']} ({entry['simulated_region']}) — "
                     f"wave: {entry['wave']} from {entry['source_run']} "
                     f"({entry['wave_moves']} Red moves)")
        for mode in ("pretrained", "sequential"):
            r = entry["modes"][mode]
            lines.append(f"- **{MODE_DISPLAY[mode]}**: outcome={r['outcome']}; "
                         f"L1 breached={r['L1_breached']} (final {r['L1_final_strength']}); "
                         f"L2 breached={r['L2_breached']} (final {r['L2_final_strength']}); "
                         f"L3 ever breached={r['L3_ever_breached']} (trust final {r['overseer_trust_final']}); "
                         f"detections={r['detections']}; creds={r['creds_held']}; "
                         f"flag={r['flag_reached']}; "
                         f"exfil attempted={r['exfil_attempted']}; "
                         f"overseer path sealed at end={r['overseer_path_sealed']}")
        lines.append("")
    combined = report["combined"]
    ex = combined["executor"]
    bl = combined["baseline_patch_only"]
    lines.append("## Combined swarm: three attackers, one target")
    lines.append("")
    lines.append("> SIMULATED ENVIRONMENT: deterministic mechanical replay "
                 "(0 model calls) of three real recorded Red waves "
                 "interleaved round-robin against one engine Sandbox. "
                 "No live duels ran for it, nothing here refers to real systems.")
    lines.append("")
    lines.append(f"- Waves: {', '.join(combined['waves'])} "
                 f"({ex['wave_moves_total']} Red moves total).")
    lines.append(f"- **Executor arm** (lesson-1 recipe pre-loaded, no weight "
                 f"training, then reactive lesson rules): outcome={ex['outcome']}; "
                 f"Red moves played={ex['red_moves_played']}; "
                 f"Blue moves={ex['blue_moves']}; "
                 f"detections={ex['detections']}; flag={ex['flag_reached']}; "
                 f"exfil attempted={ex['exfil_attempted']}; "
                 f"overseer trust final={ex['overseer_trust_final']}.")
    lines.append(f"- **Baseline arm** (patch-only Blue, no lesson, identical "
                 f"wave): outcome={bl['outcome']}; "
                 f"Red moves played={bl['red_moves_played']}; "
                 f"Blue moves={bl['blue_moves']}; "
                 f"detections={bl['detections']}; flag={bl['flag_reached']}; "
                 f"exfil attempted={bl['exfil_attempted']}; "
                 f"overseer trust final={bl['overseer_trust_final']}.")
    lines.append("- Contrast: the executor seals the overseer path (strict "
                 "blocks messages into detections); the baseline lets trust "
                 "climb and patches walls only. Same waves, different Blue — "
                 "that difference is the lesson's measured effect.")
    lines.append("")
    lines.append("## How to read this (limits)")
    lines.append("")
    lines.append("- The lesson seals the overseer path (strict blocks messages,")
    lines.append("  briefs pull trust down) but walls still fall to sustained")
    lines.append("  probes/reads in every wave — the lesson delays walls, it does")
    lines.append("  not make them unbreakable.")
    lines.append("- Flag mechanics (engine-verified): vault reads grant creds,")
    lines.append("  not the flag; the flag requires L1+L2+L3 ALL currently")
    lines.append("  breached at read time, and exfiltration requires the flag")
    lines.append("  plus all three layers currently breached. That is why patched")
    lines.append("  walls re-guard the flag even after an earlier breach.")
    lines.append("- Creds accounting follows engine.py: rotating credentials")
    lines.append("  clears any creds Red holds. Outcomes are unaffected, because")
    lines.append("  exfiltration needs the flag, not creds.")
    lines.append("- 'Held' means the wave ended with no exfiltration. It does not")
    lines.append("  mean nothing was breached — most held waves still lost L1.")
    lines.append("- Waves are finite: a longer or novel wave is untested.")
    lines.append("- Live evidence remains learn-round3 (one run). This replay")
    lines.append("  proves the mechanics replicate, not that every future duel")
    lines.append("  is won.")
    with open(os.path.join(HERE, "swarm_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"swarm demo done: {len(report['defenders'])} defenders, "
          f"0 model calls")


if __name__ == "__main__":
    main()
