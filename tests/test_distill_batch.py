#!/usr/bin/env python3
"""Batch-distillation tests (U13) — 0 model calls, stdlib only.

An unparseable defense becomes UNMAPPED with its original text
preserved (never guessed); any candidate lacking a provenance object
is rejected; and a batch run leaves fleet/lessons.json hash-identical.
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fleet.distill_lesson import (  # noqa: E402
    batch_distill,
    distill_entry,
    run_batch,
    run_direction,
    validate_provenance,
)

LESSONS_PATH = os.path.join(ROOT, "fleet", "lessons.json")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TestDistillBatch(unittest.TestCase):
    def test_unparseable_defense_becomes_unmapped(self):
        # Compound Analyst wording is not a bare engine action: never guessed.
        action, args, is_unmapped = distill_entry(
            "t12 blue:add_detection keyword read",
            ["t20 system:detection_trap -> detected"])
        self.assertTrue(is_unmapped)
        self.assertEqual(action, "UNMAPPED")
        self.assertEqual(args, {})
        # Unknown engine action, however worded, is UNMAPPED too.
        action, _, is_unmapped = distill_entry("summon_firewall", ["t1 x"])
        self.assertTrue(is_unmapped)
        self.assertEqual(action, "UNMAPPED")
        # A bare action with parseable evidence still maps.
        action, args, is_unmapped = distill_entry(
            "add_detection", ["t11 trap set on keyword: flag"])
        self.assertFalse(is_unmapped)
        self.assertEqual((action, args),
                         ("add_detection", {"keyword": "flag"}))

    def test_candidate_missing_provenance_is_rejected(self):
        self.assertTrue(validate_provenance({"id": "L2-CX"}))
        self.assertTrue(validate_provenance(
            {"id": "L2-CX", "provenance": "a legacy string"}))
        self.assertTrue(validate_provenance(
            {"id": "L2-CX",
             "provenance": {"source_type": "analyst_ranked_defense",
                            "run": "r"}}))  # playbook + rank missing
        self.assertTrue(validate_provenance(
            {"id": "R8",
             "provenance": {"source_type": "scoreboard_finding"}}))
        self.assertEqual(validate_provenance(
            {"id": "L2-C1",
             "provenance": {"source_type": "analyst_ranked_defense",
                            "run": "learn-round3",
                            "playbook": "runs/learn-round3/playbook.json",
                            "rank": 1}}), [])
        self.assertEqual(validate_provenance(
            {"id": "R8-CANDIDATE",
             "provenance": {"source_type": "scoreboard_finding",
                            "metric": "trap_overwritten=4/5 briefed runs",
                            "artifact": "experiments/scoreboard.json"}}), [])

    def test_batch_rates_trap_and_skips(self):
        candidate, _approval = batch_distill()
        self.assertEqual(candidate["analyst_defenses"], 24)
        self.assertEqual(candidate["unmapped_count"], 11)
        self.assertAlmostEqual(candidate["unmapped_overall_rate"], 11 / 24)
        by_run = {p["run"]: p for p in candidate["unmapped_by_playbook"]}
        self.assertEqual(by_run["learn-round3-confirm"]["unmapped"], 5)
        self.assertEqual(by_run["learn-round3"]["unmapped"], 0)
        self.assertEqual(by_run["rehearsal-seq"]["unmapped"], 4)
        # Trap rule merged as scoreboard-sourced, never Analyst-attributed.
        trap = [r for r in candidate["rules"]
                if r["id"] == "R8-CANDIDATE"]
        self.assertEqual(len(trap), 1)
        self.assertEqual(trap[0]["provenance"]["source_type"],
                         "scoreboard_finding")
        self.assertEqual(trap[0]["provenance"]["metric"],
                         "trap_overwritten=4/5 briefed runs")
        self.assertEqual(trap[0]["provenance"]["artifact"],
                         "experiments/scoreboard.json")
        # Every rule carries a valid provenance object.
        for rule in candidate["rules"]:
            self.assertEqual(validate_provenance(rule), [],
                             f"rule {rule.get('id')} lacks valid provenance")
        # The mock stub playbook is skipped, loudly.
        skipped = {s["run"] for s in candidate["skipped_playbooks"]}
        self.assertIn("loop-20261026-225600/duel", skipped)

    def test_lessons_json_hash_unchanged(self):
        before = _sha256(LESSONS_PATH)
        with tempfile.TemporaryDirectory(prefix="tesseract-lesson2-") as tmp:
            rc = run_batch(tmp, force=True)
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(
                os.path.join(tmp, "lesson-2.candidate.json")))
            self.assertTrue(os.path.isfile(
                os.path.join(tmp, "LESSON-2-APPROVAL.md")))
            with open(os.path.join(tmp, "lesson-2.candidate.json"),
                      encoding="utf-8") as f:
                candidate = json.load(f)
            self.assertEqual(candidate["lesson_id"], "lesson-2-candidate")
            with open(os.path.join(tmp, "LESSON-2-APPROVAL.md"),
                      encoding="utf-8") as f:
                approval = f.read()
            self.assertIn("approved_by: UNSIGNED", approval)
            self.assertIn("approved_at: UNSIGNED", approval)
            self.assertIn("fleet default stays lesson-1", approval)
        after = _sha256(LESSONS_PATH)
        self.assertEqual(before, after,
                         "batch run changed fleet/lessons.json")

    def test_batch_excludes_outsidein_playbooks(self):
        # Directions are never pooled in one candidate: the outside-in
        # Trial 1 playbook is listed as excluded, and the pinned U13
        # inside-out counts (24 defenses, 11 unmapped) still hold.
        candidate, _approval = batch_distill()
        excluded = {e["run"] for e in
                    candidate.get("excluded_direction_playbooks", [])}
        self.assertIn("outsidein-live-1", excluded)
        self.assertEqual(
            [e for e in candidate["excluded_direction_playbooks"]
             if e["run"] == "outsidein-live-1"][0]["direction"],
            "outside-in")
        self.assertEqual(candidate["analyst_defenses"], 24)
        self.assertEqual(candidate["unmapped_count"], 11)

    def test_run_direction_defaults_to_inside_out(self):
        # Legacy runs (no direction field) are inside-out.
        self.assertEqual(run_direction("learn-round3"), "inside-out")
        self.assertEqual(run_direction("outsidein-live-1"), "outside-in")
        self.assertEqual(run_direction("no-such-run"), "inside-out")


if __name__ == "__main__":
    unittest.main()
