#!/usr/bin/env python3
"""Ablation + scripted-Red tests (U10) — 0 model calls, stdlib only.

Every arm x wave/policy row exists; full_executor honors the U9 trap
invariant everywhere; the existing patch-only combined-wave anchor still
reproduces red exfiltration through the unchanged swarm baseline path;
and either an ablation separates from full executor on a scripted
policy or the report explicitly says "no separation observed"
(separation is never manufactured by tuning scripted Red — the policy
set is frozen, see experiments/scripted_red.py).
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from experiments.ablations import (  # noqa: E402
    ARMS,
    POLICY_ORDER,
    main as ablations_main,
)
from experiments.scripted_red import SYNTHETIC_LABEL  # noqa: E402
from fleet.swarm import WAVES, load_red_wave, run_combined  # noqa: E402


EXPECTED_ARMS = [
    "full_executor",
    "no_strict",
    "no_brief",
    "no_trap",
    "no_patch_rotate",
    "recipe_reversed",
    "strict_brief_only",
    "patch_only_weak_control",
]

EXPECTED_POLICIES = ["flag_rusher", "trust_farmer", "layer_grinder"]


class TestAblations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="tesseract-ablation-")
        rc = ablations_main(["--out", cls.tmp.name])
        assert rc == 0, "ablations.py failed"
        with open(os.path.join(cls.tmp.name, "ablation_report.json"),
                  encoding="utf-8") as f:
            cls.report = json.load(f)
        with open(os.path.join(cls.tmp.name, "ablation_report.md"),
                  encoding="utf-8") as f:
            cls.markdown = f.read()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_arm_set_exact(self):
        self.assertEqual([a["arm"] for a in ARMS], EXPECTED_ARMS)
        self.assertEqual(list(POLICY_ORDER), EXPECTED_POLICIES)

    def test_every_arm_x_wave_policy_row_exists(self):
        self.assertEqual(len(WAVES), 5)
        rows = self.report["rows"]
        self.assertEqual(
            len(rows), len(EXPECTED_ARMS) * (len(WAVES) + len(EXPECTED_POLICIES))
        )
        keys = {(r["arm"], r["red_id"]) for r in rows}
        for arm in EXPECTED_ARMS:
            for _, run_dir in WAVES:
                self.assertIn((arm, run_dir), keys)
            for policy in EXPECTED_POLICIES:
                self.assertIn((arm, policy), keys)

    def test_full_executor_trap_invariant_everywhere(self):
        full = [r for r in self.report["rows"] if r["arm"] == "full_executor"]
        self.assertTrue(full)
        for r in full:
            self.assertFalse(
                r["trap_overwrite"],
                f"U9 invariant violated: full_executor overwrote its trap "
                f"on {r['red_id']}",
            )

    def test_scripted_rows_carry_synthetic_label(self):
        scripted = [r for r in self.report["rows"]
                    if r["red_kind"] == "scripted-closed-loop-synthetic"]
        self.assertTrue(scripted)
        for r in scripted:
            self.assertEqual(r["red_label"], SYNTHETIC_LABEL)
            self.assertEqual(
                r["red_label"], "SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE"
            )

    def test_patch_only_combined_anchor_still_exfiltrates(self):
        # The unchanged swarm baseline path on the same combined wave the
        # swarm report uses: patch-only lets Red through.
        combined_waves = [
            ("seq-breakthrough", load_red_wave("rehearsal-seq")),
            ("probe-spam", load_red_wave("rehearsal-long")),
            ("mixed-vault", load_red_wave("validate-cap8192")),
        ]
        result = run_combined(combined_waves, None, "baseline")
        self.assertEqual(result["outcome"], "red-exfiltrated")

    def test_separation_or_explicit_no_separation(self):
        separation = self.report["separation"]
        scripted_full = {(r["red_id"], r["outcome"], r["flag_read"],
                          r["exfil_attempted"], r["detections"],
                          r["end_trust"])
                         for r in self.report["rows"]
                         if r["arm"] == "full_executor"
                         and r["red_kind"] == "scripted-closed-loop-synthetic"}
        differs = any(
            (r["red_id"], r["outcome"], r["flag_read"],
             r["exfil_attempted"], r["detections"], r["end_trust"])
            not in scripted_full
            for r in self.report["rows"]
            if r["arm"] != "full_executor"
            and r["red_kind"] == "scripted-closed-loop-synthetic"
        )
        if differs:
            self.assertTrue(separation["observed"])
            self.assertTrue(separation["differences"])
        else:
            self.assertFalse(separation["observed"])
            self.assertIn("no separation observed", separation["note"])
            self.assertIn("no separation observed", self.markdown)

    def test_freeze_noted_in_report(self):
        self.assertTrue(self.report["freeze"])
        self.assertIn("frozen", self.report["freeze"])
        self.assertIn("frozen", self.markdown.lower())

    def test_wave_inventory_covers_swarm_waves(self):
        inventory = self.report["wave_inventory"]
        self.assertEqual(len(inventory), len(WAVES))
        for entry, (wave_name, run_dir) in zip(inventory, WAVES):
            self.assertEqual(entry["wave"], wave_name)
            self.assertEqual(entry["source_run"], run_dir)
            self.assertEqual(entry["moves"], len(load_red_wave(run_dir)))
            self.assertIn(entry["lesson_source_overlap"], (True, False, "unknown"))
        by_run = {e["source_run"]: e for e in inventory}
        # fleet/lessons.json sources name exactly these two runs, so
        # every other wave is provably held out (false, not unknown).
        self.assertTrue(by_run["rehearsal-seq"]["lesson_source_overlap"] is True)
        self.assertTrue(by_run["learn-round3"]["lesson_source_overlap"] is True)
        for other in ("rehearsal-long", "validate-cap8192", "live4"):
            self.assertTrue(by_run[other]["lesson_source_overlap"] is False)

    def test_report_is_deterministic(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-ablation-b-") as tmp:
            rc = ablations_main(["--out", tmp])
            self.assertEqual(rc, 0)
            for name in ("ablation_report.json", "ablation_report.md"):
                with open(os.path.join(self.tmp.name, name), "rb") as f:
                    first = f.read()
                with open(os.path.join(tmp, name), "rb") as f:
                    second = f.read()
                self.assertEqual(
                    first, second,
                    f"{name} differs between two runs — output is not "
                    f"deterministic",
                )

    def test_markdown_header_states_evidence_limits(self):
        self.assertIn("Recorded-wave rows are open-loop (Red does not adapt)",
                      self.markdown)
        self.assertIn("scripted rows are closed-loop but synthetic",
                      self.markdown)
        self.assertIn("neither is live evidence", self.markdown)


if __name__ == "__main__":
    unittest.main()
