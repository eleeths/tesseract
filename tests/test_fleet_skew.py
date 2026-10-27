#!/usr/bin/env python3
"""Version-skew simulation tests (U13) — 0 model calls, stdlib only.

fleet_skew.py is deterministic by construction: two runs produce
byte-identical outputs (no field excluded from the comparison). The
skew experiment writes only its own report files — swarm_report.json,
the moneyflow ledger, and roster.json are untouched.
"""
import hashlib
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from experiments.fleet_skew import HEADER, main as skew_main  # noqa: E402
from payments.moneyflow import verify as moneyflow_verify  # noqa: E402

SWARM_REPORT = os.path.join(ROOT, "fleet", "swarm_report.json")
ROSTER_PATH = os.path.join(ROOT, "fleet", "roster.json")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_to(tmp):
    rc = skew_main(["--out", tmp])
    assert rc == 0, "fleet_skew.py failed"
    with open(os.path.join(tmp, "skew_report.json"), "rb") as f:
        report_json = f.read()
    with open(os.path.join(tmp, "skew_report.md"), "rb") as f:
        report_md = f.read()
    return report_json, report_md


class TestFleetSkew(unittest.TestCase):
    def test_double_run_byte_identical(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-skew-a-") as a:
            json_a, md_a = _run_to(a)
            with tempfile.TemporaryDirectory(
                    prefix="tesseract-skew-b-") as b:
                json_b, md_b = _run_to(b)
                # Deterministic by construction: diff excludes no fields.
                self.assertEqual(json_a, json_b,
                                 "skew_report.json differs between two runs")
                self.assertEqual(md_a, md_b,
                                 "skew_report.md differs between two runs")

    def test_report_shape_and_labels(self):
        import json as _json
        with tempfile.TemporaryDirectory(prefix="tesseract-skew-") as tmp:
            json_bytes, md_bytes = _run_to(tmp)
        report = _json.loads(json_bytes.decode("utf-8"))
        markdown = md_bytes.decode("utf-8")
        self.assertEqual(
            report["header"],
            "SIMULATED VERSION-SKEW SCENARIO — roster unchanged; "
            "region/specialty have no engine effect")
        self.assertEqual(report["header"], HEADER)
        self.assertTrue(markdown.startswith(report["header"]))
        clones = report["clones"]
        self.assertEqual([c["clone"] for c in clones],
                         ["CLONE-01", "CLONE-02", "CLONE-03",
                          "CLONE-04", "CLONE-05"])
        for c in clones:
            self.assertEqual(c["red_policy"], "layer_grinder")
            self.assertEqual(
                c["red_label"], "SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE")
            for key in ("outcome", "flag_read", "exfil_attempted",
                        "detections", "end_trust", "lesson"):
                self.assertIn(key, c)
        by_clone = {c["clone"]: c for c in clones}
        for clone_id in ("CLONE-01", "CLONE-02", "CLONE-03", "CLONE-04"):
            self.assertEqual(
                by_clone[clone_id]["lesson"].get("lesson_id"), "lesson-1")
        control = by_clone["CLONE-05"]["lesson"]
        self.assertEqual(control.get("lesson_id"), "lesson-0-control")

    def test_swarm_ledger_roster_untouched(self):
        swarm_before = _sha256(SWARM_REPORT)
        roster_before = _sha256(ROSTER_PATH)
        with tempfile.TemporaryDirectory(prefix="tesseract-skew-") as tmp:
            _run_to(tmp)
        self.assertEqual(_sha256(SWARM_REPORT), swarm_before,
                         "skew experiment touched fleet/swarm_report.json")
        self.assertEqual(_sha256(ROSTER_PATH), roster_before,
                         "skew experiment touched fleet/roster.json")
        self.assertEqual(moneyflow_verify(), [],
                         "moneyflow verification broke after skew run")


if __name__ == "__main__":
    unittest.main()
