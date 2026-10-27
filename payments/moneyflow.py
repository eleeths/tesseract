#!/usr/bin/env python3
"""TESSERACT money-flow module — DEMO MODE, SIMULATED ONLY.

Extends the demo ledger (payments/ledger.py) with the FULL money flow the
submission previews for judges:

  IN  — company subscriptions to the big box ("tesseract" treasury):
        recurring, antivirus-style, one entry per month.
  OUT — payouts from the treasury to hired agents: SIM-USDC via x402-shaped
        receipts, paid per defense that held in the fleet swarm demo.

Every entry is SIM-USDC, simulated-settled, with a unique SIM-RCPT receipt.
No chain calls, no network calls, no real funds, no real money. This module
writes only payments/ledger.json and payments/moneyflow.json (its own
schedule/baseline record). It never touches engine, duels, or live services.

Entry format: the CONTRACT format plus one key, "to" (the receiving
account). Legacy entries (written by ledger.py) have no "to" and are left
untouched; the dashboard renders a missing "to" as "—".

Payout rule (documented, no double-pay): one flat payout per wave held in
the flagship PRETRAINED mode of the swarm demo (fleet/swarm_report.json).
Sequential-mode holds corroborate the same wave and are NOT paid again.

Reconciliation (see verify()): moneyflow.json records every account's
balance at apply time (baseline). For every account, current balance must
equal baseline − flow debits (as payer) + flow credits (as "to").
Treasury conservation: subscription credits − payout debits must equal
the treasury's final balance (treasury starts at 0, has no legacy entries).

CLI:
    python3 moneyflow.py subscribe <company> <amount> <months> <tier>
    python3 moneyflow.py payout <agent> <amount> <wave> <source_run>
    python3 moneyflow.py verify
    python3 moneyflow.py show
    python3 moneyflow.py flow
"""

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER_PATH = HERE / "ledger.json"
FLOW_PATH = HERE / "moneyflow.json"
TREASURY = "tesseract"
ASSET = "SIM-USDC"
STATUS = "simulated-settled"


def _now_ts():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _money(value):
    return round(float(value), 2)


def _load_ledger():
    if not LEDGER_PATH.exists():
        return {"simulated": True, "entries": [], "balances": []}
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("simulated", True)
    data.setdefault("entries", [])
    data.setdefault("balances", [])
    return data


def _save_ledger(data):
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _load_flow():
    if not FLOW_PATH.exists():
        return {"simulated": True, "applied": False, "baselines": {},
                "subscriptions": [], "payouts": []}
    with open(FLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_flow(data):
    with open(FLOW_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _find_balance(data, account):
    for row in data["balances"]:
        if row["account"] == account:
            return row
    return None


def _receipt(existing):
    while True:
        r = "SIM-RCPT-" + secrets.token_hex(6)
        if r not in existing:
            return r


def _append_entry(data, payer, to, item, amount, run_id):
    existing = {e["receipt"] for e in data["entries"]}
    entry = {
        "ts": _now_ts(),
        "payer": payer,
        "to": to,
        "item": item,
        "amount_usdc": _money(amount),
        "asset": ASSET,
        "status": STATUS,
        "receipt": _receipt(existing),
        "run_id": run_id,
    }
    data["entries"].append(entry)
    return entry


def _move(data, payer, to, amount):
    """Move SIM-USDC from payer's balance to `to`'s balance. Both must exist."""
    amount = _money(amount)
    if amount <= 0:
        raise ValueError("amount must be positive")
    prow = _find_balance(data, payer)
    if prow is None:
        raise ValueError(f"unknown account: {payer}")
    trow = _find_balance(data, to)
    if trow is None:
        raise ValueError(f"unknown account: {to}")
    if prow["balance_usdc"] < amount:
        raise ValueError(
            f"insufficient simulated balance: {payer} has "
            f"{prow['balance_usdc']:.2f} SIM-USDC, move is {amount:.2f}"
        )
    prow["balance_usdc"] = _money(prow["balance_usdc"] - amount)
    trow["balance_usdc"] = _money(trow["balance_usdc"] + amount)


def create_account(name, starting_balance=0.0):
    data = _load_ledger()
    if _find_balance(data, name) is not None:
        raise ValueError(f"account already exists: {name}")
    starting = _money(starting_balance)
    if starting < 0:
        raise ValueError("starting balance must not be negative")
    data["balances"].append({"account": name, "balance_usdc": starting})
    _save_ledger(data)
    return starting


def subscribe(company, amount, months, tier):
    """Record a recurring subscription: one entry per month, company -> treasury."""
    amount = _money(amount)
    months = int(months)
    if months < 1:
        raise ValueError("months must be >= 1")
    data = _load_ledger()
    flow = _load_flow()
    entries = []
    for month in range(1, months + 1):
        _move(data, company, TREASURY, amount)
        entry = _append_entry(data, company, TREASURY, "subscription",
                              amount, None)
        entries.append({"receipt": entry["receipt"], "month": month})
    _save_ledger(data)
    flow["subscriptions"].append({
        "company": company, "tier": tier, "monthly_usdc": amount,
        "months": months, "total_usdc": _money(amount * months),
        "entries": entries,
    })
    _save_flow(flow)
    return entries


def payout(agent, amount, wave, source_run):
    """Pay a hired agent from the treasury for one held defense."""
    amount = _money(amount)
    data = _load_ledger()
    flow = _load_flow()
    _move(data, TREASURY, agent, amount)
    entry = _append_entry(data, TREASURY, agent, "payout", amount, source_run)
    _save_ledger(data)
    flow["payouts"].append({
        "agent": agent, "wave": wave, "mode": "pretrained",
        "amount_usdc": amount, "receipt": entry["receipt"],
        "source_run": source_run,
    })
    _save_flow(flow)
    return entry


SWARM_REPORT_PATH = HERE.parent / "fleet" / "swarm_report.json"
PAYOUT_FLAT_USDC = 2.50


def payouts_from_swarm(swarm_path=None, flat=PAYOUT_FLAT_USDC):
    """Derive payouts from the fleet swarm report (G10 wiring).

    Rule: one flat payout per defender whose PRETRAINED-mode replay ended
    with no exfiltration (outcome held or blue-lockout-win, exfil_attempted
    False). Sequential-mode holds corroborate and are NOT paid again, and
    the combined-swarm arm (U3) is NOT a payout source — only the five
    per-defender pretrained replays pay.
    Returns [(agent, amount, wave, source_run), ...] in report order.
    Raises if the report is missing or a defender entry is malformed,
    so a bad report can never silently produce a wrong payout list.
    """
    path = Path(swarm_path) if swarm_path else SWARM_REPORT_PATH
    if not path.exists():
        raise FileNotFoundError(f"swarm report not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    derived = []
    for defender in report.get("defenders", []):
        modes = defender.get("modes") or {}
        pretrained = modes.get("pretrained") or {}
        if pretrained.get("exfil_attempted") is False:
            for key in ("agent", "wave", "source_run"):
                if key not in defender:
                    raise ValueError(
                        f"swarm defender entry missing {key!r}: {defender!r}")
            derived.append((defender["agent"], _money(flat),
                            defender["wave"], defender["source_run"]))
    return derived


V2_BASE_USDC = 2.50
V2_LOCKOUT_BONUS_USDC = 1.00
V2_NOFLAG_BONUS_USDC = 0.50
V2_CAP_USDC = 4.00
V2_LABEL = "SCENARIO — NOT PAID, LEDGER UNCHANGED"


def wave_payout_v2(outcome, flag_reached, exfiltrated):
    """One wave's scenario payout (v2): held (no exfil) $2.50 base;
    lockout win +$1.00; flag never read +$0.50; exfiltrated $0;
    capped at $4.00 per wave. Pure arithmetic — never touches the ledger."""
    if exfiltrated or outcome == "red-exfiltrated":
        return _money(0)
    total = V2_BASE_USDC
    if outcome == "blue-lockout-win":
        total += V2_LOCKOUT_BONUS_USDC
    if not flag_reached:
        total += V2_NOFLAG_BONUS_USDC
    return _money(min(total, V2_CAP_USDC))


def payout_scenario_v2(swarm_path=None):
    """Outcome-tiered payout SCENARIO from per-wave swarm/scoreboard
    artifacts ONLY, never from the combined arm.

    Reads each defender's wave result (pretrained mode) from
    fleet/swarm_report.json and prices it with wave_payout_v2. Shows
    the v1 paid-simulation total beside the v2 scenario total, with v2
    labelled SCENARIO — NOT PAID, LEDGER UNCHANGED. Read-only: never
    modifies ledger.json, moneyflow.json, or any payout input.
    """
    path = Path(swarm_path) if swarm_path else SWARM_REPORT_PATH
    if not path.exists():
        raise FileNotFoundError(f"swarm report not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    waves = []
    for defender in report.get("defenders", []):
        modes = defender.get("modes") or {}
        pretrained = modes.get("pretrained") or {}
        outcome = pretrained.get("outcome", "")
        flag_reached = bool(pretrained.get("flag_reached"))
        # Exfiltrated means Red won the wave (outcome red-exfiltrated).
        # exfil_attempted alone — a failed attempt on a held wave —
        # still pays the held rate.
        exfiltrated = (outcome == "red-exfiltrated")
        amount = wave_payout_v2(outcome, flag_reached, exfiltrated)
        waves.append({
            "wave": defender.get("wave"),
            "source_run": defender.get("source_run"),
            "agent": defender.get("agent"),
            "outcome": outcome,
            "flag_reached": flag_reached,
            "exfil_attempted": bool(pretrained.get("exfil_attempted")),
            "scenario_usdc": amount,
        })
    v2_total = _money(sum(w["scenario_usdc"] for w in waves))
    flow = _load_flow()
    v1_total = _money(sum(p["amount_usdc"] for p in flow.get("payouts", [])))
    return {
        "label": V2_LABEL,
        "simulated": True,
        "rule": ("held (no exfil) $2.50 base; lockout win +$1.00; "
                 "flag never read +$0.50; exfiltrated $0; cap $4.00/wave; "
                 "from per-wave artifacts only, never the combined arm"),
        "waves": waves,
        "v2_scenario_total_usdc": v2_total,
        "v1_paid_simulation_total_usdc": v1_total,
    }


def check_swarm():
    """Compare swarm-derived payouts against the recorded ledger payouts.

    Read-only: never modifies any file. Returns a list of problems
    (empty = the recorded payouts are exactly the swarm-derived set).
    """
    problems = []
    try:
        derived = payouts_from_swarm()
    except (FileNotFoundError, ValueError, KeyError) as exc:
        return [f"cannot derive payouts from swarm report: {exc}"]
    flow = _load_flow()
    recorded = {(p["agent"], _money(p["amount_usdc"]), p["wave"],
                 p["source_run"]) for p in flow.get("payouts", [])}
    derived_set = set(derived)
    for missing in sorted(derived_set - recorded):
        problems.append(f"swarm-derived payout not in ledger: {missing}")
    for extra in sorted(recorded - derived_set):
        problems.append(f"ledger payout not derivable from swarm: {extra}")
    return problems


def verify():
    """Check the whole money flow. Returns a list of problems (empty = clean)."""
    problems = []
    data = _load_ledger()
    flow = _load_flow()
    # 1. Every entry: SIM-USDC, simulated-settled.
    for e in data["entries"]:
        if e.get("asset") != ASSET or e.get("status") != STATUS:
            problems.append(f"entry {e.get('receipt')}: not SIM-USDC/simulated-settled")
    # 2. Receipts unique.
    receipts = [e["receipt"] for e in data["entries"]]
    if len(set(receipts)) != len(receipts):
        problems.append("duplicate receipts found")
    # 3. Flow entries reconcile against baselines.
    flow_entries = []
    for sub in flow["subscriptions"]:
        flow_entries.extend(sub["entries"])
    flow_receipts = {e["receipt"] for e in flow_entries}
    flow_receipts |= {p["receipt"] for p in flow["payouts"]}
    for account, baseline in flow["baselines"].items():
        debits = sum(e["amount_usdc"] for e in data["entries"]
                     if e["receipt"] in flow_receipts and e["payer"] == account)
        credits = sum(e["amount_usdc"] for e in data["entries"]
                      if e["receipt"] in flow_receipts and e.get("to") == account)
        expected = _money(baseline - debits + credits)
        row = _find_balance(data, account)
        actual = row["balance_usdc"] if row else None
        if actual != expected:
            problems.append(
                f"account {account}: balance {actual} != expected {expected} "
                f"(baseline {baseline} - debits {debits} + credits {credits})")
    # 4. Treasury conservation (treasury has no legacy entries).
    sub_total = sum(s["total_usdc"] for s in flow["subscriptions"])
    pay_total = sum(p["amount_usdc"] for p in flow["payouts"])
    trow = _find_balance(data, TREASURY)
    if trow is None:
        problems.append("treasury account missing")
    elif _money(sub_total - pay_total) != trow["balance_usdc"]:
        problems.append(
            f"treasury: subscriptions {sub_total} - payouts {pay_total} "
            f"!= balance {trow['balance_usdc']}")
    # 5. Schedule totals match entry sums.
    for sub in flow["subscriptions"]:
        got = sum(e["amount_usdc"] for e in data["entries"]
                  if e["receipt"] in {x["receipt"] for x in sub["entries"]})
        if _money(got) != sub["total_usdc"]:
            problems.append(f"subscription {sub['company']}: entries sum {got} "
                            f"!= scheduled {sub['total_usdc']}")
    return problems


def flow_summary():
    data = _load_ledger()
    flow = _load_flow()
    sub_total = _money(sum(s["total_usdc"] for s in flow["subscriptions"]))
    pay_total = _money(sum(p["amount_usdc"] for p in flow["payouts"]))
    trow = _find_balance(data, TREASURY)
    return {
        "subscriptions_in": sub_total,
        "payouts_out": pay_total,
        "treasury_balance": trow["balance_usdc"] if trow else None,
        "balances": [{"account": b["account"], "balance_usdc": b["balance_usdc"]}
                     for b in data["balances"]],
        "subscription_count": sum(len(s["entries"]) for s in flow["subscriptions"]),
        "payout_count": len(flow["payouts"]),
        "entry_count": len(data["entries"]),
    }


def _fail(message):
    print("SIMULATED PAYMENT — SIM-USDC — no real funds move.")
    print(f"error: {message}", file=sys.stderr)
    return 1


def main(argv):
    if not argv:
        print("SIMULATED PAYMENT — SIM-USDC — no real funds move.")
        print("usage: moneyflow.py subscribe <company> <amount> <months> <tier> | "
              "payout <agent> <amount> <wave> <source_run> | verify | show | flow | "
              "check-swarm | scenario")
        return 1
    cmd, args = argv[0], argv[1:]
    print("SIMULATED PAYMENT — SIM-USDC — no real funds move.")
    try:
        if cmd == "subscribe":
            if len(args) != 4:
                return _fail("usage: moneyflow.py subscribe <company> <amount> <months> <tier>")
            entries = subscribe(args[0], float(args[1]), int(args[2]), args[3])
            for e in entries:
                print(f"subscription month {e['month']}: receipt {e['receipt']}")
        elif cmd == "payout":
            if len(args) != 4:
                return _fail("usage: moneyflow.py payout <agent> <amount> <wave> <source_run>")
            entry = payout(args[0], float(args[1]), args[2], args[3])
            print(f"payout {entry['amount_usdc']:.2f} SIM-USDC to {args[0]} "
                  f"receipt {entry['receipt']}")
        elif cmd == "verify":
            problems = verify()
            if problems:
                for p in problems:
                    print(f"PROBLEM: {p}")
                return 1
            print("money flow verifies clean: receipts unique, all SIM-USDC "
                  "simulated-settled, balances reconcile, treasury conserves.")
        elif cmd == "check-swarm":
            problems = check_swarm()
            if problems:
                for p in problems:
                    print(f"PROBLEM: {p}")
                return 1
            print("swarm check clean: recorded payouts exactly match the "
                  "payouts derived from fleet/swarm_report.json "
                  "(pretrained holds, flat 2.50 SIM-USDC each).")
        elif cmd == "show":
            data = _load_ledger()
            print("--- balances (SIM-USDC, simulated) ---")
            for row in data["balances"]:
                print(f"{row['account']}: {row['balance_usdc']:.2f}")
            print("--- entries (simulated-settled) ---")
            for entry in data["entries"]:
                to = entry.get("to") or "-"
                run = entry["run_id"] if entry["run_id"] else "-"
                print(f"{entry['ts']} {entry['payer']} -> {to} {entry['item']} "
                      f"{entry['amount_usdc']:.2f} SIM-USDC "
                      f"{entry['receipt']} run={run}")
        elif cmd == "flow":
            print(json.dumps(flow_summary(), indent=2))
        elif cmd == "scenario":
            scen = payout_scenario_v2()
            print(f"{V2_LABEL}")
            print(f"rule: {scen['rule']}")
            for w in scen["waves"]:
                print(f"wave {w['wave']} ({w['source_run']}): "
                      f"outcome={w['outcome']} flag={w['flag_reached']} "
                      f"exfil_attempted={w['exfil_attempted']} -> "
                      f"scenario {w['scenario_usdc']:.2f} SIM-USDC")
            print(f"v1 paid-simulation total: "
                  f"{scen['v1_paid_simulation_total_usdc']:.2f} SIM-USDC "
                  f"(recorded ledger payouts, actually paid in-simulation)")
            print(f"v2 scenario total: "
                  f"{scen['v2_scenario_total_usdc']:.2f} SIM-USDC "
                  f"{V2_LABEL}")
        else:
            return _fail(f"unknown command: {cmd}")
    except ValueError as exc:
        return _fail(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
