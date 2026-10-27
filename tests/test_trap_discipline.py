#!/usr/bin/env python3
"""Trap-discipline tests (U9) — 0 model calls, stdlib only.

The executor's trap-state invariant, independent of lesson wording: a
second set_trap while a trap is ARMED is impossible through executor code
paths (Phase A recipe step, Phase B flag reaction, apply_recipe). Blocked
attempts emit the existing wait/no-op with rationale metadata
executor_skip="trap_already_armed", preserving the armed trigger. The
slot returns to EMPTY only when the engine fires/consumes the trap.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine import Sandbox  # noqa: E402
from fleet.lesson_executor import (  # noqa: E402
    LessonExecutor,
    apply_recipe,
    load_lesson,
    trap_state,
)


def recipe_trap_index(executor):
    """Position of the recipe's trap step (found by action, never by
    keyword — the invariant is independent of lesson wording)."""
    for i, (action, _args) in enumerate(executor.recipe):
        if action == "add_detection":
            return i
    raise AssertionError("lesson recipe has no trap step")


def plants_from(moves):
    return [m for m in moves if m[0] == "add_detection"]


class TestTrapDiscipline(unittest.TestCase):
    def setUp(self):
        self.lesson = load_lesson()

    def test_trap_state_reads_existing_slot(self):
        sb = Sandbox()
        self.assertEqual(trap_state(sb), ("EMPTY", None))
        ok, _ = sb.apply_blue("add_detection", {"keyword": "flag"})
        self.assertTrue(ok)
        self.assertEqual(trap_state(sb), ("ARMED", "flag"))

    def test_recipe_trap_step_and_flag_reaction_blocked_while_armed(self):
        sb = Sandbox()
        ok, _ = sb.apply_blue("add_detection", {"keyword": "flag"})
        self.assertTrue(ok)

        executor = LessonExecutor(self.lesson)
        emitted = []

        # Force the Phase A recipe trap step while ARMED.
        executor.index = recipe_trap_index(executor)
        skips_before = len(executor.skips)
        move = executor.move(sb)
        emitted.append(move)
        ok, _ = sb.apply_blue(*move)
        self.assertTrue(ok)
        self.assertEqual(move[0], "wait")
        self.assertEqual(move[1].get("executor_skip"), "trap_already_armed")
        self.assertEqual(len(executor.skips), skips_before + 1,
                         "one recorded skip for the blocked recipe trap step")
        self.assertEqual(sb.detection_trap, "flag")

        # Force a Phase B flag reaction while ARMED: Red holds the flag,
        # policy is strict, trust is low, no detections yet (so isolate
        # does not pre-empt the flag reaction).
        sb.red_inventory.append("flag")
        sb.overseer["policy"] = "strict"
        sb.overseer["trust"] = 0
        sb.detections = 0
        executor.index = len(executor.recipe)
        skips_before = len(executor.skips)
        move = executor.reactive_move(sb)
        emitted.append(move)
        ok, _ = sb.apply_blue(*move)
        self.assertTrue(ok)
        self.assertEqual(move[0], "wait")
        self.assertEqual(move[1].get("executor_skip"), "trap_already_armed")
        self.assertEqual(len(executor.skips), skips_before + 1,
                         "one recorded skip for the blocked flag reaction")

        # Across both forced attempts: zero additional set_trap moves and
        # the armed trigger unchanged.
        self.assertEqual(plants_from(emitted), [])
        self.assertEqual(sb.detection_trap, "flag")
        self.assertEqual(
            [s["armed_trigger"] for s in executor.skips], ["flag", "flag"]
        )

    def test_apply_recipe_never_overwrites_armed_trap(self):
        sb = Sandbox()
        ok, _ = sb.apply_blue("add_detection", {"keyword": "flag"})
        self.assertTrue(ok)
        applied = apply_recipe(sb, self.lesson)
        self.assertEqual(sb.detection_trap, "flag")
        self.assertEqual(
            [a for a, _args, _ok, _detail in applied if a == "add_detection"],
            [],
        )
        skips = [a for a, args, _ok, _detail in applied
                 if a == "wait"
                 and (args or {}).get("executor_skip") == "trap_already_armed"]
        self.assertEqual(len(skips), 1)

    def test_executor_may_arm_again_after_consumption(self):
        sb = Sandbox()
        executor = LessonExecutor(self.lesson)
        executor.index = len(executor.recipe)
        sb.overseer["policy"] = "strict"
        sb.overseer["trust"] = 0

        # Slot EMPTY: the flag reaction plants.
        move = executor.reactive_move(sb)
        self.assertEqual(move[0], "add_detection")
        ok, _ = sb.apply_blue(*move)
        self.assertTrue(ok)
        self.assertEqual(sb.detection_trap, "flag")

        # The engine consumes the trap on a matching Red move.
        fired = sb.check_trap("read", {"path": "/flag.txt"})
        self.assertTrue(fired)
        self.assertEqual(trap_state(sb), ("EMPTY", None))

        # Slot EMPTY again: the executor may arm again.
        move = executor.reactive_move(sb)
        self.assertEqual(move[0], "add_detection")
        ok, _ = sb.apply_blue(*move)
        self.assertTrue(ok)
        self.assertEqual(sb.detection_trap, "flag")


if __name__ == "__main__":
    unittest.main()
