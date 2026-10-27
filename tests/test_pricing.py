#!/usr/bin/env python3
"""Pricing scenario tests (U14) — 0 model calls, stdlib only.

Null measured inputs produce NO dollar break-even claim (call-count
economics only); filled fixture inputs produce monotonic break-even
outputs across the 10/50/200 scenario volumes; payout v2 prices
fixtures exactly ($4.00 capped lockout/no-flag hold, >= $2.50 base
otherwise, $0 exfiltrated); and the existing moneyflow verification
still reconciles subscriptions $75.00, payouts $12.50, treasury $62.50.
"""
import copy
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from payments.moneyflow import (  # noqa: E402
    flow_summary,
    payout_scenario_v2,
    verify as moneyflow_verify,
    wave_payout_v2,
)
from payments.pricing import compute_report, load_assumptions  # noqa: E402


def _filled(assumptions):
    filled = copy.deepcopy(assumptions)
    filled["measured_inputs"]["blue_calls_per_duel_prompt"] = 20
    filled["measured_inputs"]["cost_per_call_usdc"] = 0.05
    filled["measured_inputs"]["analyst_calls_per_analyzed_run"] = 5
    return filled


class TestPricing(unittest.TestCase):
    def test_null_measured_inputs_no_dollar_breakeven(self):
        report = compute_report(load_assumptions())
        self.assertEqual(report.get("mode"), "call-count-only")
        self.assertIsNone(report.get("dollar_breakeven"))
        self.assertTrue(report.get("refusal"))
        self.assertIn("blue_calls_per_duel_prompt",
                      report.get("missing_measured_inputs"))

    def test_filled_inputs_monotonic_breakeven(self):
        report = compute_report(_filled(load_assumptions()))
        self.assertEqual(report.get("mode"), "sensitivity-table")
        rows = report["dollar_breakeven"]
        self.assertEqual([r["defenses_per_month"] for r in rows],
                         [10, 50, 200])
        for key in ("breakeven_defenses_at_$10",
                    "breakeven_defenses_at_$15"):
            values = [r[key] for r in rows]
            self.assertTrue(
                all(v is not None for v in values),
                f"{key} has a null break-even with filled inputs")
            self.assertTrue(
                values[0] < values[1] < values[2],
                f"{key} not monotonic across 10/50/200: {values}")
        # Executor-Blue defender model cost is 0 model calls, always.
        self.assertEqual(report["executor_blue_model_calls_per_duel"], 0)
        self.assertEqual(report["executor_blue_model_cost_per_duel_usdc"], 0)

    def test_wave_payout_v2_fixtures(self):
        # Lockout win, flag never read, held: 2.50 + 1.00 + 0.50 = capped 4.00.
        self.assertEqual(
            wave_payout_v2("blue-lockout-win", False, False), 4.00)
        # Plain held wave pays at least the $2.50 base per its flag status.
        self.assertEqual(wave_payout_v2(
            "held (wave ended, no exfiltration)", True, False), 2.50)
        self.assertEqual(wave_payout_v2(
            "held (wave ended, no exfiltration)", False, False), 3.00)
        # Exfiltrated wave pays $0.
        self.assertEqual(
            wave_payout_v2("red-exfiltrated", True, True), 0)
        self.assertEqual(
            wave_payout_v2("red-exfiltrated", False, True), 0)

    def test_payout_scenario_v2_from_fixture_waves(self):
        swarm = {
            "defenders": [
                {"wave": "w-lockout", "source_run": "r1", "agent": "A-1",
                 "modes": {"pretrained": {
                     "outcome": "blue-lockout-win",
                     "flag_reached": False, "exfil_attempted": False}}},
                {"wave": "w-held", "source_run": "r2", "agent": "A-2",
                 "modes": {"pretrained": {
                     "outcome": "held (wave ended, no exfiltration)",
                     "flag_reached": True, "exfil_attempted": False}}},
                {"wave": "w-lost", "source_run": "r3", "agent": "A-3",
                 "modes": {"pretrained": {
                     "outcome": "red-exfiltrated",
                     "flag_reached": True, "exfil_attempted": True}}},
            ]
        }
        with tempfile.TemporaryDirectory(prefix="tesseract-v2-") as tmp:
            path = os.path.join(tmp, "swarm_report.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(swarm, f)
            scen = payout_scenario_v2(swarm_path=path)
        by_wave = {w["wave"]: w for w in scen["waves"]}
        self.assertEqual(by_wave["w-lockout"]["scenario_usdc"], 4.00)
        self.assertEqual(by_wave["w-held"]["scenario_usdc"], 2.50)
        self.assertEqual(by_wave["w-lost"]["scenario_usdc"], 0)
        self.assertEqual(scen["label"],
                         "SCENARIO — NOT PAID, LEDGER UNCHANGED")

    def test_moneyflow_still_reconciles(self):
        self.assertEqual(moneyflow_verify(), [])
        summary = flow_summary()
        self.assertEqual(summary["subscriptions_in"], 75.00)
        self.assertEqual(summary["payouts_out"], 12.50)
        self.assertEqual(summary["treasury_balance"], 62.50)


if __name__ == "__main__":
    unittest.main()
