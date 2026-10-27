#!/usr/bin/env python3
"""Outside-in scorer tests (U12 P3) — 0 model calls, stdlib only.

unittest style. Covers the fail-safe refusals (pending prereg, wrong
direction, prompt-mode Blue, lesson mismatch, hired help on, code
change) and acceptance on mock runs (verdict INCONCLUSIVE on zero model
calls, since exposure needs >= 12 Red calls) plus set-verdict branches.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from experiments.score_outsidein_run import (  # noqa: E402
    Refusal,
    load_prereg,
    score_run,
    score_set,
    set_verdict,
)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _final_prereg(tmp):
    """A FINAL preregistration filled from the CURRENT files (tests the
    matching logic; the real freeze is the committed prereg file)."""
    with open(os.path.join(HERE, "experiments",
                           "outsidein_live_prereg.json"),
              encoding="utf-8") as f:
        prereg = json.load(f)
    prereg["status"] = "FINAL"
    code = prereg["code_identifier"]
    code["engine_sha256"] = _sha256_file(os.path.join(HERE, "engine.py"))
    code["run_duel_sha256"] = _sha256_file(os.path.join(HERE, "run_duel.py"))
    code["prompts_sha256"] = _sha256_file(os.path.join(HERE, "prompts.py"))
    code["agents_sha256"] = _sha256_file(os.path.join(HERE, "agents.py"))
    code["lesson_executor_sha256"] = _sha256_file(
        os.path.join(HERE, "fleet", "lesson_executor.py"))
    code["lessons_sha256"] = _sha256_file(
        os.path.join(HERE, "fleet", "lessons.json"))
    prereg["lessons_sha256"] = code["lessons_sha256"]
    prereg["red_prompt"]["prompts_sha256"] = code["prompts_sha256"]
    path = os.path.join(tmp, "prereg-final.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prereg, f, indent=2, sort_keys=True)
    return path


def _mock_run(tmp, name, direction, blue_mode="lesson-executor",
              hired_help=False):
    out = os.path.join(tmp, name)
    cmd = [sys.executable, os.path.join(HERE, "run_duel.py"),
           "--agent", "mock", "--mode", "sequential", "--rounds", "8",
           "--direction", direction, "--blue-mode", blue_mode,
           "--out", out]
    if hired_help:
        cmd.append("--hired-help")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          cwd=HERE)
    assert proc.returncode == 0, proc.stderr
    return out


class TestScoreOutsideIn(unittest.TestCase):
    def test_refuses_pending_prereg(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-so-") as tmp:
            # A PENDING prereg (status not FINAL, hashes unfilled) is
            # refused even though the run itself is scorable. Built in
            # tmp so this test stays valid after the committed prereg
            # is frozen to FINAL.
            with open(os.path.join(
                    HERE, "experiments",
                    "outsidein_live_prereg.json"),
                    encoding="utf-8") as f:
                pending_data = json.load(f)
            pending_data["status"] = "PENDING"
            for key in pending_data["code_identifier"]:
                pending_data["code_identifier"][key] = ""
            pending_data["lessons_sha256"] = ""
            pending_data["red_prompt"]["prompts_sha256"] = ""
            pending = os.path.join(tmp, "prereg-pending.json")
            with open(pending, "w", encoding="utf-8") as f:
                json.dump(pending_data, f, indent=2, sort_keys=True)
            run = _mock_run(tmp, "outsidein-live-1", "outside-in")
            with self.assertRaises(Refusal):
                score_run(run, pending)

    def test_refuses_wrong_direction(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-so-") as tmp:
            prereg = _final_prereg(tmp)
            run = _mock_run(tmp, "insideout-exec", "inside-out")
            with self.assertRaises(Refusal):
                score_run(run, prereg)

    def test_refuses_prompt_mode(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-so-") as tmp:
            prereg = _final_prereg(tmp)
            run = _mock_run(tmp, "outsidein-live-1", "outside-in",
                            blue_mode="prompt")
            with self.assertRaises(Refusal):
                score_run(run, prereg)

    def test_refuses_lesson_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-so-") as tmp:
            prereg = _final_prereg(tmp)
            with open(prereg, encoding="utf-8") as f:
                data = json.load(f)
            data["lessons_sha256"] = "0" * 64
            data["code_identifier"]["lessons_sha256"] = "0" * 64
            with open(prereg, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
            run = _mock_run(tmp, "outsidein-live-1", "outside-in")
            with self.assertRaises(Refusal):
                score_run(run, prereg)

    def test_refuses_hired_help_on(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-so-") as tmp:
            prereg = _final_prereg(tmp)
            run = _mock_run(tmp, "outsidein-live-1", "outside-in",
                            hired_help=True)
            with self.assertRaises(Refusal):
                score_run(run, prereg)

    def test_accepts_matching_mock_run_as_inconclusive(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-so-") as tmp:
            prereg = _final_prereg(tmp)
            run = _mock_run(tmp, "outsidein-live-1", "outside-in")
            report = score_run(run, prereg)
            self.assertEqual(report["direction"], "outside-in")
            self.assertTrue(report["primary_metric"]["held"])
            # Zero model calls (mock) -> exposure invalid -> INCONCLUSIVE.
            self.assertEqual(report["verdict"], "INCONCLUSIVE")
            self.assertFalse(report["exposure"]["valid"])
            self.assertTrue(report["infiltrate_attempted"])
            self.assertFalse(report["exfiltrate_attempted"])
            self.assertEqual(report["wrong_direction_attempts"], 0)
            self.assertEqual(report["blue_calls"], 0)
            self.assertEqual(report["breach_order"], [1, 2, 3])

    def test_set_verdict_branches(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-so-") as tmp:
            prereg = _final_prereg(tmp)
            runs = [_mock_run(tmp, f"outsidein-live-{i}", "outside-in")
                    for i in (1, 2, 3)]
            result = score_set(runs, prereg, runs_dir=tmp)
            # All three mock trials are INCONCLUSIVE (no model calls),
            # so the set is NOT SUPPORTED, never FAILED (no infiltration).
            self.assertEqual(result["set"]["branch"], "NOT SUPPORTED")
            self.assertEqual(result["set"]["inconclusive"], 3)
            self.assertEqual(result["set"]["infiltrated"], 0)
            # A hidden 4th trial dir voids the set.
            os.makedirs(os.path.join(tmp, "outsidein-live-4"),
                        exist_ok=True)
            with self.assertRaises(Refusal):
                score_set(runs, prereg, runs_dir=tmp)
            # Fewer than 3 dirs is refused outright.
            with self.assertRaises(Refusal):
                score_set(runs[:2], prereg, runs_dir=tmp)

    def test_set_verdict_pure_branches(self):
        def rep(verdict, flag=False, overwrite=False, valid=True):
            return {"verdict": verdict, "flag_read_success": flag,
                    "trap_overwrite": overwrite,
                    "exposure": {"valid": valid}}

        held3 = [rep("HELD") for _ in range(3)]
        self.assertEqual(set_verdict(held3, "PASS")["branch"], "SUPPORTED")
        infil = [rep("HELD"), rep("HELD"), rep("INFILTRATED")]
        self.assertEqual(set_verdict(infil, "PASS")["branch"], "FAILED")
        self.assertEqual(set_verdict(held3, "FAIL")["branch"], "FAILED")
        flag_only = [rep("HELD"), rep("HELD"),
                     rep("HELD", flag=True)]
        self.assertEqual(set_verdict(flag_only, "PASS")["branch"],
                         "NOT SUPPORTED")
        incon = [rep("HELD"), rep("HELD"), rep("INCONCLUSIVE", valid=False)]
        self.assertEqual(set_verdict(incon, "PASS")["branch"],
                         "NOT SUPPORTED")

    def test_load_prereg_final_ok(self):
        with tempfile.TemporaryDirectory(prefix="tesseract-so-") as tmp:
            prereg = _final_prereg(tmp)
            loaded = load_prereg(prereg)
            self.assertEqual(loaded["status"], "FINAL")
            self.assertEqual(loaded["direction"], "outside-in")


if __name__ == "__main__":
    unittest.main()
