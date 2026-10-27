#!/usr/bin/env python3
"""TESSERACT money-flow demo — scripted, idempotent, SIMULATED ONLY.

Applies the demo money flow once:
  IN  — subscriptions to the "tesseract" treasury (antivirus-style, recurring):
        acme-corp, standard tier, 10.00 SIM-USDC x 3 months = 30.00
        globex,    plus tier,     15.00 SIM-USDC x 3 months = 45.00
        Total IN: 75.00
  OUT — payouts from the treasury to hired agents, flat 2.50 SIM-USDC per
        wave held in the PRETRAINED mode of fleet/swarm_report.json
        (sequential holds corroborate the same wave and are NOT paid again):
        SENTRY-MONSOON (seq-breakthrough, lockout win)
        SENTRY-AURORA  (learn-pattern, lockout win)
        SENTRY-PAMPA   (probe-spam, held)
        SENTRY-SAVANNA (mixed-vault, held)
        SENTRY-REEF    (short-probe, held)
        Total OUT: 12.50.  Treasury final: 62.50.

Idempotency: refuses to run twice (moneyflow.json "applied" flag). Baselines
for every account present at apply time are recorded first, so verify()
can reconcile afterwards. No model calls, no network, no real funds.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import moneyflow

SUBSCRIPTIONS = [
    ("acme-corp", 10.00, 3, "standard"),
    ("globex", 15.00, 3, "plus"),
]

# G10 wiring: payouts are DERIVED from fleet/swarm_report.json at demo
# time (one flat 2.50 SIM-USDC per pretrained-mode hold), not hand-entered.
# The recorded ledger is verified against the same derivation by
# `moneyflow.py check-swarm`. The demo refuses to run twice, so this
# change affects future regenerations only; the existing ledger is
# untouched and must match the derivation exactly.
PAYOUTS = moneyflow.payouts_from_swarm()


def main():
    flow = moneyflow._load_flow()
    if flow.get("applied"):
        print("money-flow demo already applied — refusing to run twice.")
        print("Run `python3 moneyflow.py verify` to re-check it.")
        return 1
    ledger = moneyflow._load_ledger()
    # Baselines first, before any movement.
    flow["baselines"] = {b["account"]: b["balance_usdc"]
                         for b in ledger["balances"]}
    moneyflow._save_flow(flow)
    # Treasury + new accounts.
    try:
        moneyflow.create_account(moneyflow.TREASURY, 0.0)
    except ValueError as exc:
        print(f"treasury setup: {exc}")
        return 1
    for agent, _, _, _ in PAYOUTS:
        try:
            moneyflow.create_account(agent, 0.0)
        except ValueError as exc:
            print(f"agent account setup: {exc}")
            return 1
    try:
        moneyflow.create_account("globex", 100.0)
    except ValueError as exc:
        print(f"company account setup: {exc}")
        return 1
    # New accounts' baselines are their starting balances (created after the
    # first baseline snapshot, so record them explicitly).
    flow = moneyflow._load_flow()
    flow["baselines"][moneyflow.TREASURY] = 0.0
    flow["baselines"]["globex"] = 100.0
    for agent, _, _, _ in PAYOUTS:
        flow["baselines"][agent] = 0.0
    moneyflow._save_flow(flow)
    # IN: subscriptions.
    for company, amount, months, tier in SUBSCRIPTIONS:
        moneyflow.subscribe(company, amount, months, tier)
        print(f"subscribed {company} ({tier}): {amount:.2f} x {months} months")
    # OUT: payouts per held defense.
    for agent, amount, wave, source_run in PAYOUTS:
        entry = moneyflow.payout(agent, amount, wave, source_run)
        print(f"paid {agent}: {amount:.2f} SIM-USDC for {wave} "
              f"(receipt {entry['receipt']})")
    flow = moneyflow._load_flow()
    flow["applied"] = True
    moneyflow._save_flow(flow)
    problems = moneyflow.verify()
    if problems:
        print("VERIFY PROBLEMS (flow applied, but reconciliation failed):")
        for p in problems:
            print(f"  PROBLEM: {p}")
        return 1
    print("money-flow demo applied and verified clean.")
    print(json.dumps(moneyflow.flow_summary(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
