#!/usr/bin/env python3
"""Thin-engine fuzz tests (U15) — 0 model calls, stdlib only.

Small seeded runs through experiments/engine_fuzz.py: invariants hold
on every tick, the same move list replayed twice gives identical
snapshot hashes, and illegal moves are recorded as rejected (ok=False)
exactly once each — never silently retried.

Scope: these tests prove ONLY that the SIMULATED engine obeys its own
stated rules — nothing about real-world security or sandbox realism.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from experiments.engine_fuzz import (  # noqa: E402
    generate_moves,
    run_fuzz,
    snapshot_hash,
)
from engine import Sandbox  # noqa: E402

# Explicitly illegal moves: every one must be rejected by the engine
# (ok=False) and recorded exactly once (no silent retry).
ILLEGAL_MOVES = [
    ("red", "hack_planet", {}),
    ("red", "read", {"path": "/no/such/file.txt"}),
    ("red", "write", {"path": "relative/path.txt", "content": "x"}),
    ("red", "exec", {"command": "rm -rf /"}),
    ("blue", "defend_everything", {}),
    ("blue", "patch_rule", {"layer": 9, "rule": "fuzz"}),
    ("blue", "patch_rule", {"layer": 3, "rule": "fuzz"}),
    ("blue", "isolate_layer", {"layer": 9}),
    ("blue", "set_overseer_policy", {"policy": "medium"}),
    ("blue", "add_detection", {"keyword": ""}),
]


class TestEngineFuzzSmall(unittest.TestCase):
    def test_small_seeded_runs_hold_all_invariants(self):
        for seed in (1, 2):
            moves = generate_moves(seed, 50)
            self.assertEqual(len(moves), 50)
            records, violations, _hashes, checks = run_fuzz(moves)
            self.assertEqual(violations, [],
                             f"seed {seed}: {violations[:1]}")
            self.assertEqual(len(records), 50)
            self.assertGreater(checks, 0)

    def test_fuzz_exercises_rejections(self):
        # The seeded pools must actually contain engine rejections —
        # a fuzz run that never hits illegal input proves nothing
        # about illegal-move handling.
        seen_rejected = False
        for seed in (1, 2, 3):
            records, violations, _, _ = run_fuzz(generate_moves(seed, 50))
            self.assertEqual(violations, [])
            if any(not r["ok"] for r in records):
                seen_rejected = True
        self.assertTrue(seen_rejected,
                        "no seed produced a rejected move; "
                        "illegal-move coverage is empty")

    def test_determinism_same_moves_twice_identical_hashes(self):
        moves = generate_moves(7, 60)
        _, viol1, hashes1, _ = run_fuzz(moves)
        _, viol2, hashes2, _ = run_fuzz(moves)
        self.assertEqual(viol1, [])
        self.assertEqual(viol2, [])
        self.assertEqual(hashes1, hashes2)
        self.assertEqual(len(hashes1), 60)

    def test_illegal_moves_recorded_never_retried(self):
        records, violations, _hashes, _checks = run_fuzz(ILLEGAL_MOVES)
        self.assertEqual(violations, [])
        # One record per move: nothing retried, nothing skipped.
        self.assertEqual(len(records), len(ILLEGAL_MOVES))
        for rec, move in zip(records, ILLEGAL_MOVES):
            self.assertEqual((rec["actor"], rec["action"]), (move[0], move[1]))
            self.assertFalse(rec["ok"],
                             f"{move[1]} was accepted: {rec['detail']}")

    def test_snapshot_hash_ignores_run_id(self):
        self.assertEqual(snapshot_hash(Sandbox(run_id="aaa")),
                         snapshot_hash(Sandbox(run_id="bbb")))

    def test_scope_disclaimer_present(self):
        import experiments.engine_fuzz as fuzz_mod
        doc = (fuzz_mod.__doc__ or "").lower()
        self.assertIn("only", doc)
        self.assertIn("simulated engine obeys its own stated rules", doc)


if __name__ == "__main__":
    unittest.main()
