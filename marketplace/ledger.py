#!/usr/bin/env python3
"""TESSERACT marketplace ledger — schema marketplace-ledger/1.

A SEPARATE ledger from payments/ledger.json + payments/moneyflow.json.
The old history (subscriptions IN $75.00, payouts OUT $12.50, treasury
$62.50) is never extended or rewritten here; judges audit marketplace
conservation separately. The old verify() keeps passing untouched.

Determinism: no wall clock, no randomness. Simulated logical time is
an integer sequence; every ID comes from a counter. Two fresh runs
produce byte-identical artifacts.

verify_marketplace() implements the 10 reconciliation checks from the
round-4 spec. It is read-only and returns a list of problems (empty =
pass). It reads the old ledger ONLY to check receipt-ID disjointness
(check 2) and never modifies it.
"""

import json
import os

SCHEMA = "marketplace-ledger/1"
TREASURY = "marketplace-treasury"
PAYOUT_ATOMIC = 2500000  # 2.50 SIM-USDC, mirrors the swarm flat rule
PAYOUT_USDC = "2.50"
OLD_LEDGER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "payments", "ledger.json")


def new_ledger():
    """Empty marketplace ledger (logical clock starts at 100)."""
    return {
        "schema": SCHEMA,
        "simulated": True,
        "logical_clock": 100,
        "counters": {
            "transaction": 0,
            "settlement": 0,
            "receipt": 0,
            "demo_payment": 0,
            "flow": 0,
            "nonce": 0,
        },
        "accounts": [],
        "faucet_allocations": [],
        "settlement_journal": [],
        "failed_attempts": [],
        "flows": [],
        "subscriptions": [],
        "hires": [],
        "payout_claims": [],
        "used_nonces": [],
    }


def load_ledger(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("schema") != SCHEMA:
        raise ValueError("not a marketplace ledger: %s" % path)
    return data


def save_ledger(state, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def find_account(state, account_id):
    for row in state["accounts"]:
        if row["account"] == account_id:
            return row
    return None


def create_account(state, account_id, opening_atomic=0):
    if find_account(state, account_id) is not None:
        raise ValueError("account already exists: %s" % account_id)
    row = {
        "account": account_id,
        "opening_atomic": int(opening_atomic),
        "balance_atomic": int(opening_atomic),
    }
    state["accounts"].append(row)
    return row


def faucet_allocate(state, account_id, amount_atomic):
    """Opening simulated balance: NOT revenue, NOT a subscription payment."""
    row = find_account(state, account_id)
    if row is None:
        raise ValueError("unknown account: %s" % account_id)
    row["opening_atomic"] += int(amount_atomic)
    row["balance_atomic"] += int(amount_atomic)
    state["faucet_allocations"].append({
        "account": account_id,
        "amount_atomic": int(amount_atomic),
        "note": "opening simulated balance, not revenue, not a payment",
        "logical_time": state["logical_clock"],
    })


def next_demo_payment_id(state):
    state["counters"]["demo_payment"] += 1
    return "DP-%06d" % state["counters"]["demo_payment"]


def next_nonce(state):
    state["counters"]["nonce"] += 1
    return "sim-nonce-%06d" % state["counters"]["nonce"]


def next_flow_id(state):
    state["counters"]["flow"] += 1
    return "MP-FLOW-%06d" % state["counters"]["flow"]


def tick_clock(state):
    """Advance simulated logical time by one; return the new value."""
    state["logical_clock"] += 1
    return state["logical_clock"]


def append_flow(state, kind, payer, payee, amount_atomic, receipt,
                settlement_id, related):
    flow = {
        "flow_id": next_flow_id(state),
        "kind": kind,
        "payer": payer,
        "payee": payee,
        "amount_atomic": int(amount_atomic),
        "receipt_id": receipt["receipt_id"],
        "settlement_id": settlement_id,
        "related": related,
        "logical_time": state["logical_clock"],
    }
    state["flows"].append(flow)
    return flow


def verify_marketplace(state, runs_dir=None, old_ledger_path=None):
    """The 10 reconciliation checks. Returns a list of problems."""
    problems = []
    flows = state.get("flows", [])
    # 1. Every paid flow has one unique SIM-RCPT-MP- receipt.
    receipts = [f.get("receipt_id") for f in flows]
    for flow in flows:
        rid = flow.get("receipt_id") or ""
        if not rid.startswith("SIM-RCPT-MP-"):
            problems.append("flow %s has no SIM-RCPT-MP- receipt" %
                            flow.get("flow_id"))
    if len(receipts) != len(set(receipts)):
        problems.append("duplicate marketplace receipt ID")
    # 2. No marketplace receipt ID appears in the old ledger.
    old_path = old_ledger_path or OLD_LEDGER_PATH
    if os.path.exists(old_path):
        with open(old_path, "r", encoding="utf-8") as f:
            old = json.load(f)
        old_receipts = {e.get("receipt") for e in old.get("entries", [])}
        clash = set(receipts) & old_receipts
        if clash:
            problems.append("marketplace receipt in old ledger: %s" %
                            sorted(clash))
    # 3. Every subscription flow follows a successful settlement.
    journal = {j["settlement_id"]: j
               for j in state.get("settlement_journal", [])}
    for flow in flows:
        if flow.get("kind") == "subscription":
            entry = journal.get(flow.get("settlement_id"))
            if entry is None or not entry.get("success"):
                problems.append("subscription flow %s lacks a successful "
                                "settlement" % flow.get("flow_id"))
    # 4. Every payout flow references a completed hire and a held run.
    hires = {h["hire_id"]: h for h in state.get("hires", [])}
    for flow in flows:
        if flow.get("kind") != "payout":
            continue
        related = flow.get("related") or {}
        hire = hires.get(related.get("hire_id"))
        if hire is None or hire.get("status") not in ("completed-held", "paid"):
            problems.append("payout flow %s lacks a completed hire" %
                            flow.get("flow_id"))
        run_id = related.get("duel_run_id")
        run = None
        if runs_dir is not None and run_id:
            run_path = os.path.join(runs_dir, run_id + ".json")
            if os.path.exists(run_path):
                with open(run_path, "r", encoding="utf-8") as f:
                    run = json.load(f)
        if run is None or not run.get("held"):
            problems.append("payout flow %s lacks a held run" %
                            flow.get("flow_id"))
    # 5. Every payout amount is exactly 2.50 SIM-USDC.
    for flow in flows:
        if flow.get("kind") == "payout" and flow.get("amount_atomic") != PAYOUT_ATOMIC:
            problems.append("payout flow %s amount is not 2.50 SIM-USDC" %
                            flow.get("flow_id"))
    # 6. No duel_run_id is paid twice.
    paid_runs = [ (f.get("related") or {}).get("duel_run_id")
                  for f in flows if f.get("kind") == "payout" ]
    if len(paid_runs) != len(set(paid_runs)):
        problems.append("a duel run was paid twice")
    # 7. Treasury never goes negative in flow order.
    treasury = 0
    for flow in sorted(flows, key=lambda f: f.get("logical_time", 0)):
        if flow.get("payee") == TREASURY:
            treasury += int(flow.get("amount_atomic", 0))
        if flow.get("payer") == TREASURY:
            treasury -= int(flow.get("amount_atomic", 0))
        if treasury < 0:
            problems.append("treasury negative after flow %s" %
                            flow.get("flow_id"))
            break
    # 8. Every account: ending = opening + inflows - outflows.
    for row in state.get("accounts", []):
        acct = row["account"]
        inflows = sum(int(f["amount_atomic"]) for f in flows
                       if f.get("payee") == acct)
        outflows = sum(int(f["amount_atomic"]) for f in flows
                        if f.get("payer") == acct)
        expected = int(row["opening_atomic"]) + inflows - outflows
        if int(row["balance_atomic"]) != expected:
            problems.append("account %s balance mismatch: %d != %d" %
                            (acct, row["balance_atomic"], expected))
    # 9. Total across accounts equals total recorded opening allocations.
    total_balances = sum(int(r["balance_atomic"])
                         for r in state.get("accounts", []))
    total_opening = sum(int(r["opening_atomic"])
                        for r in state.get("accounts", []))
    if total_balances != total_opening:
        problems.append("conservation broken: balances %d != opening %d" %
                        (total_balances, total_opening))
    # 10. Failed attempts moved 0 and produced no receipt or paid flow.
    flow_receipts = set(receipts)
    for attempt in state.get("failed_attempts", []):
        if attempt.get("amount_moved") != 0:
            problems.append("failed attempt moved a nonzero amount")
        if attempt.get("receipt") is not None:
            problems.append("failed attempt produced a receipt")
        if attempt.get("receipt") in flow_receipts:
            problems.append("failed attempt receipt appears in paid flows")
    return problems
