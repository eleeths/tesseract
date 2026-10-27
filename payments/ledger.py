#!/usr/bin/env python3
"""TESSERACT demo-mode payment ledger — SIMULATED ONLY.

Pay-per-call shaped interface (item + amount + receipt) for defensive
work: pay per red-team run, per defense strategy, per hardening.

This is a DEMO. Every entry is settled in SIM-USDC, a simulated asset.
No chain calls, no network calls, no real funds move, no real money.
Written fresh for Tesseract from CONTRACT.md; it imports nothing from
any preexisting project or live business code.

Storage: ledger.json next to this file, in the CONTRACT format:
    {"simulated": true,
     "entries": [{"ts", "payer", "item", "amount_usdc", "asset": "SIM-USDC",
                  "status": "simulated-settled", "receipt", "run_id"}],
     "balances": [{"account", "balance_usdc"}]}

CLI:
    python3 ledger.py account <name> [starting]
    python3 ledger.py charge <payer> <run|strategy|hardening> <amount> [run_id]
    python3 ledger.py balance <name>
    python3 ledger.py receipt <receipt_id>
    python3 ledger.py show
"""

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER_PATH = Path(__file__).resolve().parent / "ledger.json"
ITEMS = ("run", "strategy", "hardening")
ASSET = "SIM-USDC"
STATUS = "simulated-settled"
BANNER = "SIMULATED PAYMENT — SIM-USDC — no real funds move."


def _now_ts():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _empty_ledger():
    return {"simulated": True, "entries": [], "balances": []}


def _load():
    if not LEDGER_PATH.exists():
        return _empty_ledger()
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("simulated", True)
    data.setdefault("entries", [])
    data.setdefault("balances", [])
    return data


def _save(data):
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _find_balance(data, account):
    for row in data["balances"]:
        if row["account"] == account:
            return row
    return None


def _money(value):
    """Round to whole USDC cents; keeps balances reconciling exactly."""
    return round(float(value), 2)


def create_account(name, starting_balance=0.0):
    """Create an account with a simulated starting balance. Returns the balance row."""
    if not name:
        raise ValueError("account name must not be empty")
    starting = _money(starting_balance)
    if starting < 0:
        raise ValueError("starting balance must not be negative")
    data = _load()
    if _find_balance(data, name) is not None:
        raise ValueError(f"account already exists: {name}")
    row = {"account": name, "balance_usdc": starting}
    data["balances"].append(row)
    _save(data)
    return dict(row)


def charge(payer, item, amount_usdc, run_id=None):
    """Charge a payer for one item. Deducts from the balance and appends
    a simulated-settled entry. Returns the entry."""
    if item not in ITEMS:
        raise ValueError(f"item must be one of {', '.join(ITEMS)}, got: {item}")
    amount = _money(amount_usdc)
    if amount <= 0:
        raise ValueError("amount must be positive")
    data = _load()
    row = _find_balance(data, payer)
    if row is None:
        raise ValueError(f"unknown account: {payer}")
    if row["balance_usdc"] < amount:
        raise ValueError(
            f"insufficient simulated balance: {payer} has "
            f"{row['balance_usdc']:.2f} SIM-USDC, charge is {amount:.2f}"
        )
    row["balance_usdc"] = _money(row["balance_usdc"] - amount)
    entry = {
        "ts": _now_ts(),
        "payer": payer,
        "item": item,
        "amount_usdc": amount,
        "asset": ASSET,
        "status": STATUS,
        "receipt": "SIM-RCPT-" + secrets.token_hex(6),
        "run_id": run_id,
    }
    data["entries"].append(entry)
    _save(data)
    return dict(entry)


def get_balance(account):
    """Return the simulated balance for an account (number)."""
    row = _find_balance(_load(), account)
    if row is None:
        raise ValueError(f"unknown account: {account}")
    return row["balance_usdc"]


def get_receipt(receipt_id):
    """Return the ledger entry for a receipt id, or None if not found."""
    for entry in _load()["entries"]:
        if entry["receipt"] == receipt_id:
            return dict(entry)
    return None


def list_entries():
    """Return all ledger entries in order."""
    return [dict(e) for e in _load()["entries"]]


def _fail(message):
    print(BANNER)
    print(f"error: {message}", file=sys.stderr)
    return 1


def main(argv):
    if not argv:
        print(BANNER)
        print("usage: ledger.py account <name> [starting] | "
              "charge <payer> <run|strategy|hardening> <amount> [run_id] | "
              "balance <name> | receipt <receipt_id> | show")
        return 1
    cmd, args = argv[0], argv[1:]
    print(BANNER)
    try:
        if cmd == "account":
            if len(args) not in (1, 2):
                return _fail("usage: ledger.py account <name> [starting]")
            row = create_account(args[0], float(args[1]) if len(args) == 2 else 0.0)
            print(f"account created: {row['account']} "
                  f"balance {row['balance_usdc']:.2f} SIM-USDC (simulated)")
        elif cmd == "charge":
            if len(args) not in (3, 4):
                return _fail("usage: ledger.py charge <payer> "
                             "<run|strategy|hardening> <amount> [run_id]")
            entry = charge(args[0], args[1], float(args[2]),
                           args[3] if len(args) == 4 else None)
            print(f"charged {entry['payer']} {entry['amount_usdc']:.2f} SIM-USDC "
                  f"for {entry['item']} (simulated-settled)")
            print(f"receipt: {entry['receipt']}")
            if entry["run_id"]:
                print(f"run_id: {entry['run_id']}")
        elif cmd == "balance":
            if len(args) != 1:
                return _fail("usage: ledger.py balance <name>")
            print(f"{args[0]}: {get_balance(args[0]):.2f} SIM-USDC (simulated)")
        elif cmd == "receipt":
            if len(args) != 1:
                return _fail("usage: ledger.py receipt <receipt_id>")
            entry = get_receipt(args[0])
            if entry is None:
                return _fail(f"no such receipt: {args[0]}")
            print(json.dumps(entry, indent=2))
        elif cmd == "show":
            data = _load()
            print("--- balances (SIM-USDC, simulated) ---")
            for row in data["balances"]:
                print(f"{row['account']}: {row['balance_usdc']:.2f}")
            print("--- entries (simulated-settled) ---")
            for entry in data["entries"]:
                run = entry["run_id"] if entry["run_id"] else "-"
                print(f"{entry['ts']} {entry['payer']} {entry['item']} "
                      f"{entry['amount_usdc']:.2f} SIM-USDC "
                      f"{entry['receipt']} run={run}")
            if not data["entries"]:
                print("(no entries yet)")
        else:
            return _fail(f"unknown command: {cmd}")
    except ValueError as exc:
        return _fail(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
