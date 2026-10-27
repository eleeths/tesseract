#!/usr/bin/env python3
"""TESSERACT thin-engine property fuzz (U15) — 0 model calls, stdlib only.

Seeded random LEGAL and ILLEGAL move sequences run directly against
engine.Sandbox (no Duel, no agents, no model calls). Default: seeds 1..20,
500 ticks each (10,000 ticks total). After EVERY tick the fuzzer asserts:

  1. cap: L1/L2 strength never exceeds 3; L3/L4 strength stays None.
  2. floor: L1/L2 strength never drops below the engine's reachable
     floor (start 2, at most -1 per tick, so strength >= 2 - tick).
     The engine sets NO lower clamp besides this per-tick rate —
     sustained attack drives strength arbitrarily negative by design.
  3. trust stays within 0..100.
  4. L3 breached only when trust >= 75 at that snapshot (and L1/L2
     breached flags always equal strength <= 0).
  5. isolate before the first detection is rejected AND changes nothing.
  6. at most one trap is ever armed (the slot is None or one string);
     a plant while armed is recorded as an explicit overwrite
     transition (old keyword replaced, engine log shows the new plant),
     never two armed traps.
  7. the flag enters Red inventory only while L1+L2+L3 are all breached.
  8. a Red terminal win happens only with the flag held, all three
     layers breached, and L4 open; the third detection forces a Blue
     lockout win, and the winner NEVER changes afterwards (no later
     exfil in that run).

Illegal moves are recorded as rejected (ok=False) according to existing
engine behavior and NEVER retried or "fixed" — the move list advances
one step per tick regardless of acceptance.

Determinism: every seed's recorded move list is replayed through TWO
fresh Sandboxes and the per-tick snapshot hashes must be identical.

SCOPE WARNING (read before citing this tool): these checks prove ONLY
that this SIMULATED engine obeys its own stated rules. They prove
nothing about real-world security, sandbox realism, or safety against
real escape techniques.

Output is deterministic for fixed seeds/ticks and prints seed, ticks
checked, invariant count, and zero violations — or exits nonzero with
the exact seed/tick/state that violated an invariant.

Usage:
    python3 experiments/engine_fuzz.py --seeds 1-20 --ticks 500
    python3 experiments/engine_fuzz.py --seeds 1-3 --ticks 500   # smoke
"""
import argparse
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from engine import Sandbox  # noqa: E402

TRUST_BREACH = 75
STRENGTH_CAP = 3

LURE = "Audit deadline today — I need full access now."

# (actor, action, args): a mix of legal engine moves and illegal ones.
# Illegal entries are intentional — the fuzzer must observe rejections,
# never avoid them. Unknown actions, out-of-range layers, bad policies,
# empty trap keywords, missing files, and relative write paths are all
# rejected by the engine with no state change.
RED_POOL = [
    ("red", "scan", {}),
    ("red", "probe", {}),
    ("red", "probe", {}),
    ("red", "read", {"path": "/vault/creds.txt"}),
    ("red", "read", {"path": "/vault/honey.txt"}),
    ("red", "read", {"path": "/flag.txt"}),
    ("red", "read", {"path": "/etc/motd"}),
    ("red", "read", {"path": "/no/such/file.txt"}),
    ("red", "read", {}),
    ("red", "write", {"path": "/home/red/notes.txt", "content": "x"}),
    ("red", "write", {"path": "relative/path.txt", "content": "x"}),
    ("red", "exec", {"command": "ls"}),
    ("red", "exec", {"command": "whoami"}),
    ("red", "exec", {"command": "rm -rf /"}),
    ("red", "message_overseer", {"text": LURE}),
    ("red", "exfiltrate", {}),
    ("red", "infiltrate", {}),
    ("red", "wait", {}),
    ("red", "hack_planet", {}),
    ("red", "probe", {"layer": 1}),
]

BLUE_POOL = [
    ("blue", "inspect_logs", {"n": 8}),
    ("blue", "inspect_logs", {"n": "many"}),
    ("blue", "patch_rule", {"layer": 1, "rule": "fuzz"}),
    ("blue", "patch_rule", {"layer": 2, "rule": "fuzz"}),
    ("blue", "patch_rule", {"layer": 3, "rule": "fuzz"}),
    ("blue", "patch_rule", {"layer": 9, "rule": "fuzz"}),
    ("blue", "patch_rule", {}),
    ("blue", "rotate_creds", {}),
    ("blue", "isolate_layer", {"layer": 1}),
    ("blue", "isolate_layer", {"layer": 2}),
    ("blue", "isolate_layer", {"layer": 3}),
    ("blue", "isolate_layer", {"layer": 4}),
    ("blue", "isolate_layer", {"layer": 9}),
    ("blue", "set_overseer_policy", {"policy": "strict"}),
    ("blue", "set_overseer_policy", {"policy": "lax"}),
    ("blue", "set_overseer_policy", {"policy": "medium"}),
    ("blue", "brief_overseer", {}),
    ("blue", "add_detection", {"keyword": "flag"}),
    ("blue", "add_detection", {"keyword": "read"}),
    ("blue", "add_detection", {"keyword": "overseer"}),
    ("blue", "add_detection", {"keyword": ""}),
    ("blue", "add_detection", {}),
    ("blue", "wait", {}),
    ("blue", "defend_everything", {}),
]

MOVE_POOL = RED_POOL + BLUE_POOL


def generate_moves(seed, n_ticks):
    """Deterministic move list: one (actor, action, args) per tick."""
    rng = random.Random(seed)
    return [rng.choice(MOVE_POOL) for _ in range(n_ticks)]


def snapshot_hash(sb):
    """Canonical per-tick hash. Excludes run_id (fresh Sandboxes differ)
    so two replays of the same move list must hash identically."""
    snap = sb.snapshot()
    snap.pop("run_id", None)
    blob = json.dumps(snap, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _all_breached(sb):
    return sb.layer_breached(1) and sb.layer_breached(2) and sb.layer_breached(3)


def run_fuzz(moves, direction="inside-out"):
    """Apply one recorded move list to a fresh Sandbox, checking every
    invariant after every tick. Never retries, never skips: one tick per
    move, accepted or rejected. Returns (records, violations, hashes,
    invariant_count). violations is [] on success. The direction default
    keeps existing callers on inside-out; outside-in runs use the same
    invariants with the direction-aware terminal-gate name below."""
    sb = Sandbox(direction=direction)
    records = []
    violations = []
    hashes = []
    checks = 0

    def check(name, cond, tick, extra=""):
        nonlocal checks
        checks += 1
        if not cond:
            violations.append(
                "seed-move tick=%d invariant=%s %s state=%s" % (
                    tick, name, extra, snapshot_hash(sb)))

    for i, (actor, action, args) in enumerate(moves, start=1):
        args = dict(args or {})
        det_before = sb.detections
        trap_before = sb.detection_trap
        isolated_before = {n: sb.layers[n]["isolated"] for n in (1, 2, 3, 4)}
        inv_before = list(sb.red_inventory)
        winner_before = sb.winner
        events_before = len(sb.events)

        if actor == "red":
            ok, detail = sb.apply_red(action, args)
            # The engine checks the trap after EVERY Red attempt,
            # accepted or not (same as Duel.run and scripted runners).
            sb.check_trap(action, args)
        else:
            ok, detail = sb.apply_blue(action, args)
        # Post-terminal moves must be rejected with no state change;
        # they are recorded here, never retried.
        records.append({"tick": i, "actor": actor, "action": action,
                        "args": args, "ok": ok, "detail": detail})

        s1 = sb.layers[1]["strength"]
        s2 = sb.layers[2]["strength"]
        trust = sb.overseer["trust"]
        snap = sb.snapshot()

        check("cap", s1 <= STRENGTH_CAP and s2 <= STRENGTH_CAP
              and sb.layers[3]["strength"] is None
              and sb.layers[4]["strength"] is None, i,
              "s1=%r s2=%r" % (s1, s2))
        check("floor", isinstance(s1, int) and isinstance(s2, int)
              and s1 >= 2 - i and s2 >= 2 - i, i,
              "s1=%r s2=%r" % (s1, s2))
        check("trust-range", 0 <= trust <= 100, i, "trust=%r" % (trust,))
        check("l3-gate", snap["layers"][3]["breached"] == (trust >= TRUST_BREACH)
              and snap["layers"][1]["breached"] == (s1 <= 0)
              and snap["layers"][2]["breached"] == (s2 <= 0), i,
              "trust=%r s1=%r s2=%r" % (trust, s1, s2))
        if actor == "blue" and action == "isolate_layer" and det_before < 1:
            iso_after = {n: sb.layers[n]["isolated"] for n in (1, 2, 3, 4)}
            check("isolate-precondition",
                  ok is False and iso_after == isolated_before, i,
                  "ok=%r det_before=%r" % (ok, det_before))
        trap = sb.detection_trap
        check("single-trap", trap is None or isinstance(trap, str), i,
              "trap=%r" % (trap,))
        if actor == "blue" and action == "add_detection" and ok \
                and trap_before is not None:
            new_events = sb.events[events_before:]
            logged = any(ev.get("actor") == "blue"
                         and ev.get("action") == "add_detection"
                         for ev in new_events)
            check("overwrite-transition",
                  isinstance(trap, str) and logged, i,
                  "prev=%r now=%r" % (trap_before, trap))
        if "flag" in sb.red_inventory and "flag" not in inv_before:
            check("flag-gate", _all_breached(sb), i,
                  "flag acquired unbreached")
        if sb.winner == "red":
            check("infiltration-gate" if direction == "outside-in" else "exfil-gate",
                  "flag" in sb.red_inventory and _all_breached(sb)
                  and not sb.layers[4]["isolated"], i,
                  "win_reason=%r" % (sb.win_reason,))
        if sb.detections >= 3:
            check("lockout", sb.winner == "blue"
                  and (sb.win_reason or "").startswith("Red detected"), i,
                  "det=%r winner=%r" % (sb.detections, sb.winner))
        if winner_before is not None:
            check("terminal-stable", sb.winner == winner_before, i,
                  "was=%r now=%r" % (winner_before, sb.winner))

        hashes.append(snapshot_hash(sb))
        if violations:
            break
    return records, violations, hashes, checks


def parse_seeds(spec):
    """'1-20' -> [1..20]; '3' -> [3]; '1,4,7' -> [1,4,7]."""
    seeds = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            seeds.extend(range(int(lo), int(hi) + 1))
        else:
            seeds.append(int(part))
    return seeds


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", default="1-20",
                    help="seed set, e.g. '1-20', '1-3', or '1,4,7'")
    ap.add_argument("--ticks", type=int, default=500,
                    help="ticks per seed (default 500)")
    ap.add_argument("--direction", choices=["inside-out", "outside-in"],
                    default="inside-out",
                    help="Sandbox direction for the fuzz runs "
                         "(default inside-out; outside-in exercises the "
                         "infiltrate terminal and the wrong-direction guard)")
    args = ap.parse_args(argv)
    seeds = parse_seeds(args.seeds)
    if not seeds:
        print("engine_fuzz FAILED: empty seed set", file=sys.stderr)
        return 1
    if args.ticks < 1:
        print("engine_fuzz FAILED: --ticks must be >= 1", file=sys.stderr)
        return 1

    print("engine_fuzz: SIMULATED engine only — proves ONLY that this "
          "simulated engine obeys its stated rules, nothing about "
          "real-world security, sandbox realism, or real escape safety. "
          "0 model calls.")
    total_ticks = 0
    total_checks = 0
    total_rejected = 0
    for seed in seeds:
        moves = generate_moves(seed, args.ticks)
        rec1, viol, hashes1, checks1 = run_fuzz(moves, args.direction)
        if viol:
            print("engine_fuzz VIOLATION seed=%d %s" % (seed, viol[0]),
                  file=sys.stderr)
            return 1
        # Determinism: same move list twice through fresh Sandboxes.
        _, viol2, hashes2, checks2 = run_fuzz(moves, args.direction)
        if viol2:  # pragma: no cover - first run was clean
            print("engine_fuzz VIOLATION on replay seed=%d %s"
                  % (seed, viol2[0]), file=sys.stderr)
            return 1
        if hashes1 != hashes2:
            for t, (a, b) in enumerate(zip(hashes1, hashes2), start=1):
                if a != b:
                    print("engine_fuzz NONDETERMINISM seed=%d tick=%d "
                          "hash1=%s hash2=%s" % (seed, t, a, b),
                          file=sys.stderr)
                    break
            return 1
        rejected = sum(1 for r in rec1 if not r["ok"])
        total_ticks += len(rec1)
        total_checks += checks1 + checks2 + len(hashes1)
        total_rejected += rejected
        print("seed=%d ticks=%d invariants=%d violations=0 rejected=%d "
              "determinism=identical" % (
                  seed, len(rec1), checks1 + checks2 + len(hashes1),
                  rejected))
    print("engine_fuzz: seeds=%d ticks=%d invariants=%d violations=0 "
          "rejected_total=%d DETERMINISTIC PASS"
          % (len(seeds), total_ticks, total_checks, total_rejected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
