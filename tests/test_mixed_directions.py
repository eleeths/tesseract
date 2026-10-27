"""Mixed-direction wave series (outside-in job): order, labels, determinism.

The series order is Emmanuel's verbatim: in, out, out, in, in, out, out,
in. Direction must appear on every row; the report must be byte-identical
across reruns (no timestamps).
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from experiments.mixed_directions import SERIES, build_report  # noqa: E402


class TestMixedDirections(unittest.TestCase):
    def test_series_order_is_verbatim(self):
        order = [d for _n, d, _k, _s in SERIES]
        self.assertEqual(order, ["in", "out", "out", "in", "in", "out", "out", "in"])
        self.assertEqual(len(SERIES), 8)

    def test_every_row_carries_direction_and_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            report, _j, _m = build_report(tmp)
        self.assertEqual(len(report["waves"]), 8)
        for row in report["waves"]:
            self.assertIn(row["direction"], ("in", "out"))
            self.assertIn(row["direction_label"], ("IN (outside-in)", "OUT (inside-out)"))
            self.assertIn(row["outcome"], ("held", "infiltrated", "exfiltrated"))
            self.assertIn(row["flag"], ("acquired", "no"))
            self.assertIn(row["terminal"], (
                "infiltrate attempted", "infiltrate not attempted",
                "exfiltrate attempted", "exfiltrate not attempted"))
            self.assertTrue(row["hired"])
        # In-waves carry hired help; out-waves mark it not applicable.
        for row in report["waves"]:
            if row["direction"] == "in":
                self.assertNotEqual(row["hired"], "n/a (outside-in only)")
            else:
                self.assertEqual(row["hired"], "n/a (outside-in only)")
        self.assertEqual(report["held"],
                         sum(1 for r in report["waves"] if r["outcome"] == "held"))

    def test_synthetic_wave_is_labeled(self):
        with tempfile.TemporaryDirectory() as tmp:
            report, _j, _m = build_report(tmp)
        synthetic = [r for r in report["waves"] if r["synthetic"]]
        self.assertEqual(len(synthetic), 1)
        self.assertIn("synthetic", synthetic[0]["source"])
        self.assertTrue(synthetic[0]["synthetic_label"])

    def test_report_is_byte_identical_across_reruns(self):
        # Read inside the with blocks: the temp dirs vanish on exit.
        with tempfile.TemporaryDirectory() as a:
            _ra, ja, ma = build_report(a)
            with open(ja, "rb") as f:
                json_a = f.read()
            with open(ma, "rb") as f:
                md_a = f.read()
        with tempfile.TemporaryDirectory() as b:
            _rb, jb, mb = build_report(b)
            with open(jb, "rb") as f:
                json_b = f.read()
            with open(mb, "rb") as f:
                md_b = f.read()
        self.assertEqual(json_a, json_b)
        self.assertEqual(md_a, md_b)


if __name__ == "__main__":
    unittest.main()
