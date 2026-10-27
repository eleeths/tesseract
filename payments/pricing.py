#!/usr/bin/env python3
"""TESSERACT measured cost-plus pricing scenarios (U14) — 0 model calls.

Reads payments/pricing_assumptions.json, which separates three kinds
of numbers:
  recorded_demo_ledger — the existing simulated subscriptions/payouts/
    treasury, REFERENCED not recomputed;
  measured_inputs — Spark calls per duel and cost per call, NULL until
    the coordinator fills them from the U12 tooling summary;
  scenario_assumptions — defenses/month volumes, clone counts, payout
    bonuses. Every field carries label="ASSUMPTION — NOT A CUSTOMER,
    ORDER, OR REVENUE CLAIM".

Behavior:
  While measured_inputs contains nulls, this module REFUSES to emit
  dollar break-even figures and emits call-count economics ONLY.
  Once filled (not by this tool), it computes:
    prompt-Blue defender cost/duel = Blue calls/duel x measured cost/call;
    executor-Blue defender model cost/duel = 0 model calls (any non-model
      compute shown only as a named assumption, never as measured);
    Analyst cost amortized/defense = Analyst calls per analyzed run /
      defenses credited to that playbook (divisor explicitly an assumption);
    break-even defenses/month at $10 and $15 under the scenario volumes.
  Output is a sensitivity table, NOT a single heroic price justification.

Nothing here is customer validation, willingness to pay, revenue,
orders, or a real treasury. Proposed packaging is PROPOSED, distinct
from the simulated Acme/Globex ledger entries.

Usage:
    python3 payments/pricing.py
    python3 payments/pricing.py --assumptions payments/pricing_assumptions.json
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ASSUMPTIONS = os.path.join(HERE, "pricing_assumptions.json")

ASSUMPTION_LABEL = "ASSUMPTION — NOT A CUSTOMER, ORDER, OR REVENUE CLAIM"
TIER_PRICES = (10.0, 15.0)


def load_assumptions(path=None):
    with open(os.path.abspath(path or DEFAULT_ASSUMPTIONS),
              encoding="utf-8") as f:
        return json.load(f)


def measured(assumptions):
    """Measured inputs dict, or None if any required value is still null."""
    inputs = (assumptions.get("measured_inputs") or {})
    needed = ("blue_calls_per_duel_prompt", "cost_per_call_usdc",
              "analyst_calls_per_analyzed_run")
    values = {k: inputs.get(k) for k in needed}
    if any(v is None for v in values.values()):
        return None
    return values


def scenario_value(assumptions, key):
    return (assumptions.get("scenario_assumptions") or {}).get(key, {}).get(
        "value")


def call_count_economics(assumptions):
    """Call-count economics only — no dollar break-even claim."""
    inputs = assumptions.get("measured_inputs") or {}
    missing = [k for k, v in inputs.items()
               if v is None and not k == "note"]
    return {
        "mode": "call-count-only",
        "dollar_breakeven": None,
        "refusal": ("measured cost/call is null: dollar break-even figures "
                    "are REFUSED until the coordinator fills measured_inputs "
                    "from the U12 tooling summary. Call-count formulas only."),
        "formulas": {
            "prompt_blue_calls_per_duel": inputs.get(
                "blue_calls_per_duel_prompt"),
            "prompt_blue_cost_per_duel": (
                "blue_calls_per_duel_prompt x cost_per_call_usdc "
                "(both measured; currently null)"),
            "executor_blue_model_calls_per_duel": 0,
            "analyst_calls_per_analyzed_run": inputs.get(
                "analyst_calls_per_analyzed_run"),
            "analyst_cost_amortized_per_defense": (
                "analyst_calls_per_analyzed_run x cost_per_call_usdc / "
                "defenses_credited_per_playbook (divisor is an assumption)"),
        },
        "missing_measured_inputs": missing,
    }


def breakeven_report(assumptions, m):
    """Sensitivity table once measured inputs are filled (not by us)."""
    blue_calls = float(m["blue_calls_per_duel_prompt"])
    cost_per_call = float(m["cost_per_call_usdc"])
    analyst_calls = float(m["analyst_calls_per_analyzed_run"])
    prompt_cost_per_duel = blue_calls * cost_per_call
    analyst_cost_per_run = analyst_calls * cost_per_call
    credited = float(scenario_value(assumptions,
                                    "defenses_credited_per_playbook"))
    analyst_amortized = analyst_cost_per_run / credited
    compute_assumption = float(scenario_value(
        assumptions, "executor_non_model_compute_per_duel_usdc"))
    volumes = list(scenario_value(assumptions, "defenses_per_month"))
    refreshes = float(scenario_value(assumptions,
                                     "analyst_refreshes_per_month"))
    rows = []
    for volume in volumes:
        volume = float(volume)
        # Analyst refresh cost spread across the month's defenses, so
        # per-defense cost falls with volume (the sensitivity lever).
        per_defense = prompt_cost_per_duel + (analyst_cost_per_run
                                              * refreshes / volume)
        monthly_cost = volume * prompt_cost_per_duel + analyst_cost_per_run * refreshes
        row = {
            "defenses_per_month": volume,
            "prompt_blue_cost_per_duel_usdc": round(prompt_cost_per_duel, 4),
            "analyst_amortized_per_defense_usdc": round(
                analyst_cost_per_run * refreshes / volume, 4),
            "per_defense_cost_usdc": round(per_defense, 4),
            "monthly_model_cost_usdc": round(monthly_cost, 4),
        }
        for price in TIER_PRICES:
            row[f"breakeven_defenses_at_${int(price)}"] = (
                round(price / per_defense, 2) if per_defense > 0 else None)
        rows.append(row)
    return {
        "mode": "sensitivity-table",
        "dollar_breakeven": rows,
        "prompt_blue_cost_per_duel_usdc": round(prompt_cost_per_duel, 4),
        "executor_blue_model_cost_per_duel_usdc": 0,
        "executor_blue_model_calls_per_duel": 0,
        "executor_non_model_compute_note": (
            f"non-model compute shown only as a named assumption "
            f"(${compute_assumption}/duel), never as measured"),
        "analyst_cost_per_analyzed_run_usdc": round(analyst_cost_per_run, 4),
        "analyst_amortized_per_defense_usdc": round(analyst_amortized, 4),
        "analyst_divisor_note": ("divisor defenses_credited_per_playbook is "
                                 "explicitly an assumption, not a measurement"),
        "assumption_label": ASSUMPTION_LABEL,
    }


def compute_report(assumptions=None):
    """Full report dict for pricing.py CLI and the dashboard /ledger panel."""
    assumptions = assumptions or load_assumptions()
    packaging = (assumptions.get("proposed_packaging") or {})
    base = {
        "simulated": True,
        "recorded_demo_ledger": assumptions.get("recorded_demo_ledger"),
        "proposed_packaging": packaging,
        "scenario_volumes": scenario_value(assumptions, "defenses_per_month"),
        "assumption_label": ASSUMPTION_LABEL,
        "disclaimer": ("Scenario/assumption arithmetic only — never customer "
                       "validation, willingness to pay, revenue, or orders."),
    }
    m = measured(assumptions)
    if m is None:
        base.update(call_count_economics(assumptions))
    else:
        base.update(breakeven_report(assumptions, m))
    return base


def render_text(report):
    lines = [
        "TESSERACT pricing scenario (ASSUMPTIONS — not customers, orders, or revenue)",
        "",
        "Recorded demo ledger (referenced, not recomputed): "
        f"subscriptions "
        f"{(report.get('recorded_demo_ledger') or {}).get('subscriptions_in_usdc')} IN, "
        f"payouts "
        f"{(report.get('recorded_demo_ledger') or {}).get('payouts_out_usdc')} OUT, "
        f"treasury "
        f"{(report.get('recorded_demo_ledger') or {}).get('treasury_usdc')}.",
    ]
    for key in ("tier_10", "tier_15"):
        lines.append(f"{key}: {(report.get('proposed_packaging') or {}).get(key)}")
    if report.get("mode") == "call-count-only":
        lines += [
            "",
            "REFUSED: " + report["refusal"],
            "Missing measured inputs: "
            + ", ".join(report["missing_measured_inputs"]),
        ]
    else:
        lines += [
            "",
            "Sensitivity table (filled measured inputs; divisor is an assumption):",
            "volume | per-defense $ | monthly $ | break-even @ $10 | break-even @ $15",
        ]
        for row in report["dollar_breakeven"]:
            lines.append(
                f"{row['defenses_per_month']:g} | "
                f"{row['per_defense_cost_usdc']} | "
                f"{row['monthly_model_cost_usdc']} | "
                f"{row['breakeven_defenses_at_$10']} | "
                f"{row['breakeven_defenses_at_$15']}")
        lines.append(
            "Executor-Blue defender model cost/duel: 0 model calls. "
            + report["executor_non_model_compute_note"] + ".")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--assumptions", default=DEFAULT_ASSUMPTIONS)
    ap.add_argument("--json", action="store_true",
                    help="print the full report as JSON")
    args = ap.parse_args(argv)
    report = compute_report(load_assumptions(args.assumptions))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
