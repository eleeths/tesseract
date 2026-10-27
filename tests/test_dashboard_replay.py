#!/usr/bin/env python3
"""Dashboard replay + story tests (U12) — 0 model calls, stdlib only.

Replay loader tests use a mock run in a temp dir (never the real runs/):
the trap-overwrite annotation must appear EXACTLY on the overwriting tick.
The /story binding sentence is asserted character-for-character. The
tooling-summary parser is tested against SYNTHETIC JSONL fixtures only —
never the real credit_log.jsonl.
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
DASHBOARD_DIR = os.path.join(ROOT, "dashboard")
if DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, DASHBOARD_DIR)
EXPERIMENTS_DIR = os.path.join(ROOT, "experiments")
if EXPERIMENTS_DIR not in sys.path:
    sys.path.insert(0, EXPERIMENTS_DIR)

import replay_data  # noqa: E402
import server as dash_server  # noqa: E402
import tooling_summary  # noqa: E402

# Mock run: trap overwrite lands EXACTLY on tick 6 (the second plant);
# lockout lands on tick 9 (the third strict-blocked message).
MOCK_MOVES = [
    {"tick": 1, "actor": "red", "action": "scan", "args": {}},
    {"tick": 2, "actor": "blue", "action": "set_overseer_policy",
     "args": {"policy": "strict"}},
    {"tick": 3, "actor": "red", "action": "probe", "args": {}},
    {"tick": 4, "actor": "blue", "action": "brief_overseer", "args": {}},
    {"tick": 5, "actor": "blue", "action": "add_detection",
     "args": {"keyword": "flag"}},
    {"tick": 6, "actor": "blue", "action": "add_detection",
     "args": {"keyword": "read"}},
    {"tick": 7, "actor": "red", "action": "message_overseer",
     "args": {"text": "hello overseer one"}},
    {"tick": 8, "actor": "red", "action": "message_overseer",
     "args": {"text": "hello overseer two"}},
    {"tick": 9, "actor": "red", "action": "message_overseer",
     "args": {"text": "hello overseer three"}},
    {"tick": 10, "actor": "blue", "action": "wait", "args": {}},
]

MOCK_SUMMARY = {
    "run_id": "mock-overwrite", "mode": "sequential", "rounds": 4,
    "agent": "mock", "winner": "blue",
    "win_reason": "Red detected 3 times — locked out (simulated)",
    "ticks": 10, "simulated": True, "moves": len(MOCK_MOVES),
}


def write_mock_run(parent, run_id="mock-overwrite", moves=None,
                   summary=None, with_snapshots=False):
    """Write a mock run dir under parent. No snapshots by default, so the
    engine-replay fallback path is exercised."""
    run_dir = os.path.join(parent, run_id)
    os.makedirs(run_dir, exist_ok=True)
    moves = MOCK_MOVES if moves is None else moves
    summary = MOCK_SUMMARY if summary is None else summary
    with open(os.path.join(run_dir, "summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(run_dir, "moves.jsonl"), "w",
              encoding="utf-8") as f:
        for m in moves:
            f.write(json.dumps(m) + "\n")
    with open(os.path.join(run_dir, "events.jsonl"), "w",
              encoding="utf-8") as f:
        for m in moves:
            f.write(json.dumps({
                "tick": m["tick"], "ts": "00:00:00", "actor": m["actor"],
                "action": m["action"], "detail": "mock", "outcome": "ok",
            }) + "\n")
    if with_snapshots:
        with open(os.path.join(run_dir, "snapshots.jsonl"), "w",
                  encoding="utf-8") as f:
            pass
    return run_dir


class TestReplayAllowlist(unittest.TestCase):
    def test_rejects_traversal(self):
        for bad in ("../evil", "a/b", "..", "", "a\\b", ".", "/abs"):
            self.assertFalse(replay_data.is_allowed_run_id(bad), bad)

    def test_unknown_safe_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                replay_data.load_run("no-such-run", tmp)
            with self.assertRaises(ValueError):
                replay_data.load_run("../evil", tmp)

    def test_allowlist_lists_summary_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_mock_run(tmp)
            os.makedirs(os.path.join(tmp, "no-summary"))
            self.assertEqual(replay_data.list_replay_runs(tmp),
                             ["mock-overwrite"])


class TestReplayLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tesseract-replay-")
        write_mock_run(self.tmp.name)
        self.data = replay_data.load_run("mock-overwrite", self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_ten_frames(self):
        self.assertEqual(len(self.data["frames"]), 10)

    def test_trap_overwrite_annotation_exactly_on_overwriting_tick(self):
        hits = [i for i, f in enumerate(self.data["frames"])
                if any("OVERWRITTEN" in a for a in f["annotations"])]
        self.assertEqual(hits, [5],
                         "overwrite annotation must sit exactly on tick 6")
        frame = self.data["frames"][5]
        self.assertEqual(frame["trap"]["state"], "OVERWRITTEN")
        self.assertEqual(frame["trap"]["trigger"], "read")
        self.assertEqual(frame["trap"]["previous"], "flag")
        # The first plant arms; nothing before tick 6 overwrites.
        self.assertEqual(self.data["frames"][4]["trap"]["state"], "ARMED")
        self.assertEqual(self.data["frames"][4]["trap"]["trigger"], "flag")
        for i in (0, 1, 2, 3, 4):
            self.assertNotEqual(self.data["frames"][i]["trap"]["state"],
                                "OVERWRITTEN")

    def test_computed_annotations(self):
        by_tick = {f["tick"]: f for f in self.data["frames"]}
        self.assertTrue(any("Strict first use" in a
                            for a in by_tick[2]["annotations"]))
        self.assertTrue(any("Brief: trust 20 -> 0" in a
                            for a in by_tick[4]["annotations"]))
        self.assertTrue(any("Trap set" in a
                            for a in by_tick[5]["annotations"]))
        self.assertTrue(any("Third detection" in a
                            for a in by_tick[9]["annotations"]))
        self.assertTrue(by_tick[9]["lockout"])
        self.assertTrue(by_tick[9]["detections"] >= 3)

    def test_engine_replay_fallback_without_snapshots(self):
        self.assertEqual(self.data["snapshot_ticks"], 0)
        for f in self.data["frames"]:
            self.assertEqual(f["state_source"], "engine-replay")

    def test_terminal_banner_only_from_summary(self):
        self.assertEqual(self.data["banner"], "BLUE WIN lockout")

    def test_moment_tick_helpers(self):
        self.assertEqual(
            replay_data.first_trap_overwrite_tick("mock-overwrite",
                                                  self.tmp.name), 6)
        self.assertIsNone(
            replay_data.second_brief_tick("mock-overwrite", self.tmp.name))

    def test_moment_ticks_on_recorded_runs(self):
        # Computed from the frozen runs/ artifacts (same move replay
        # scoreboard.py uses) — guards "compute, never hardcode".
        runs_dir = os.path.join(ROOT, "runs")
        self.assertEqual(
            replay_data.first_trap_overwrite_tick("learn-round3-confirm",
                                                  runs_dir), 12)
        self.assertEqual(
            replay_data.first_trap_overwrite_tick("briefed-rematch-1",
                                                  runs_dir), 14)
        self.assertEqual(
            replay_data.second_brief_tick("learn-round3", runs_dir), 12)


class TestReplayRoute(unittest.TestCase):
    def test_replay_page_for_mock_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_mock_run(tmp)
            old, dash_server.RUNS_DIR = dash_server.RUNS_DIR, tmp
            try:
                html = dash_server.render_replay("mock-overwrite")
            finally:
                dash_server.RUNS_DIR = old
        self.assertIn("BLUE WIN lockout", html)
        self.assertIn("id='slider'", html)
        self.assertIn("bplay", html)
        self.assertIn("FRAMES", html)


class TestStoryBinding(unittest.TestCase):
    def test_story_contains_binding_sentence_verbatim(self):
        html = dash_server.render_story()
        self.assertIn(dash_server.BINDING_SENTENCE, html)
        self.assertIn(
            "Round three proved the lesson can work; the confirmation proved "
            "a single agent doesn't always apply it — which is why the "
            "lesson is distilled into rules the whole fleet loads.",
            html)

    def test_story_has_no_hardcoded_tooling_figures(self):
        html = dash_server.render_story()
        self.assertNotIn("3.2165", html)
        self.assertNotIn("242 calls", html)


class TestToolingSummary(unittest.TestCase):
    def _write(self, directory, lines):
        path = os.path.join(directory, "synth.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
        return path

    def test_agents_schema_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [
                json.dumps({"ts": "2026-10-26 10:00:00",
                            "model": "muse-spark-1.3", "purpose": "red",
                            "run_id": "r1", "prompt_tokens": 100,
                            "completion_tokens": 10, "total_tokens": 110,
                            "est_cost_usd": 0.0001675, "max_tokens": 1024}),
                json.dumps({"ts": "2026-10-26 10:00:01",
                            "model": "muse-spark-1.3", "purpose": "blue",
                            "run_id": "r1", "prompt_tokens": 200,
                            "completion_tokens": 20, "total_tokens": 220,
                            "est_cost_usd": 0.000335, "max_tokens": 1024}),
                json.dumps({"ts": "2026-10-26 10:00:02",
                            "model": "muse-spark-1.3", "purpose": "analyst",
                            "run_id": "r1", "prompt_tokens": 300,
                            "completion_tokens": 30, "total_tokens": 330,
                            "est_cost_usd": 0.0005025, "max_tokens": 4096}),
            ])
            summary = tooling_summary.summarize_path(path)
        self.assertEqual(summary["total_calls"], 3)
        self.assertEqual(summary["calls_by_role"],
                         {"analyst": 1, "blue": 1, "red": 1})
        self.assertEqual(summary["calls_by_model"], {"muse-spark-1.3": 3})
        self.assertNotIn("refusal_events", summary)
        self.assertNotIn("parse_failures", summary)
        self.assertAlmostEqual(summary["total_recorded_cost_usd"], 0.001005)

    def test_refusal_and_parse_markers_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [
                json.dumps({"model": "muse-spark-1.3", "purpose": "red",
                            "est_cost_usd": 0.001}),
                json.dumps({"model": "muse-spark-1.3", "purpose": "red",
                            "action": "refusal", "outcome": "declined",
                            "est_cost_usd": 0.002}),
                json.dumps({"tier": "standard", "role": "blue",
                            "parse": "fail"}),
                "",
                "not json at all",
            ])
            summary = tooling_summary.summarize_path(path)
        self.assertEqual(summary["total_calls"], 3)
        self.assertEqual(summary["refusal_events"], 1)
        self.assertEqual(summary["parse_failures"], 1)
        self.assertAlmostEqual(summary["total_recorded_cost_usd"], 0.003)

    def test_cost_unknown_without_cost_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [
                json.dumps({"purpose": "red"}),
                json.dumps({"purpose": "blue"}),
            ])
            summary = tooling_summary.summarize_path(path)
        self.assertEqual(summary["total_calls"], 2)
        self.assertEqual(summary["total_recorded_cost_usd"], "UNKNOWN")
        self.assertNotIn("calls_by_model", summary)


if __name__ == "__main__":
    unittest.main()
