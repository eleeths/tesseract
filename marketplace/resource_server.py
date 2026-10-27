#!/usr/bin/env python3
"""TESSERACT marketplace resource server — x402 shape, serve-after-settle.

Every marketplace purchase follows the x402 flow, locally:

  unpaid request -> 402 artifact -> payment payload -> facilitator
  verify -> facilitator settle -> ONLY THEN serve + receipt.

If verification fails, the server returns a fresh 402 and creates
nothing. If settlement fails, the server returns 402 again: no
resource served, no entitlement, no balance change, no paid flow, no
receipt. Failed attempts are recorded only in a separate attempts list
with amount_moved 0.

The server depends on the facilitator ONLY through the supported /
verify / settle interface (see facilitator.py) — the swappable seam.
Nothing here branches on whether settlement is simulated.

Amounts in protocol messages are atomic-unit strings (6 decimals:
10000000 = 10.00 SIM-USDC). Ledger display amounts derive from them.
"""

from .facilitator import (
    ASSET, DECIMALS, MAX_WINDOW, NETWORK, SCHEME, SIM_SIGNATURE,
    X402_VERSION,
)


def display_usdc(amount_atomic):
    """Atomic units (6 decimals) -> 2-decimal display string."""
    return "%.2f" % (int(amount_atomic) / (10 ** DECIMALS))


def payment_requirements(resource, amount_atomic, pay_to, description):
    """One x402 payment-requirements object for a local resource."""
    return {
        "scheme": SCHEME,
        "network": NETWORK,
        "maxAmountRequired": str(int(amount_atomic)),
        "resource": resource,
        "description": description,
        "mimeType": "application/json",
        "payTo": pay_to,
        "maxTimeoutSeconds": MAX_WINDOW,
        "asset": ASSET,
        "extra": {
            "name": ASSET,
            "version": "sim-1",
            "decimals": DECIMALS,
            "facilitator": "simulated-local",
        },
    }


def request_without_payment(resource, requirements, demo_payment_id):
    """An unpaid request: returns the 402 artifact, creates nothing."""
    return {
        "status": 402,
        "x402Version": X402_VERSION,
        "error": "payment required",
        "accepts": [requirements],
        "demo_payment_id": demo_payment_id,
    }


def build_payment_payload(payer, requirements, logical_now, nonce):
    """Client-side payment payload construction (exact scheme)."""
    return {
        "x402Version": X402_VERSION,
        "scheme": SCHEME,
        "network": NETWORK,
        "payload": {
            "signature": SIM_SIGNATURE,
            "authorization": {
                "from": payer,
                "to": requirements["payTo"],
                "value": str(requirements["maxAmountRequired"]),
                "validAfter": int(logical_now),
                "validBefore": int(logical_now) + MAX_WINDOW,
                "nonce": nonce,
            },
        },
    }


def next_receipt_id(state):
    """Deterministic receipt ID from the ledger counter."""
    counters = state.setdefault("counters", {})
    counters["receipt"] = counters.get("receipt", 0) + 1
    return "SIM-RCPT-MP-%06d" % counters["receipt"]


def issue_receipt(state, settlement, demo_payment_id, resource,
                  payer, payee, amount_atomic, related):
    """Receipt for one successful settlement (called only after settle)."""
    return {
        "receipt_id": next_receipt_id(state),
        "transaction": settlement["transaction"],
        "settlement_id": settlement["settlement_id"],
        "demo_payment_id": demo_payment_id,
        "scheme": SCHEME,
        "network": NETWORK,
        "asset": ASSET,
        "payer": payer,
        "payee": payee,
        "amount_atomic": int(amount_atomic),
        "amount_usdc": display_usdc(amount_atomic),
        "resource": resource,
        "related": related,
        "logical_sequence": state.get("logical_clock", 0),
        "simulated": True,
    }


def serve_with_payment(state, facilitator, resource, requirements,
                       payload, demo_payment_id, serve):
    """Run one x402 purchase end to end.

    serve(receipt, settlement) is called ONLY after successful
    settlement and returns the served record (subscription, hire, or
    payout-flow data). Returns (status, body) where status is 200 or
    402. On 402, body is a fresh 402 artifact and serve was not called.
    Failed attempts are appended to state["failed_attempts"] with
    amount_moved 0 and no receipt.
    """
    valid, reason, _payer = facilitator.verify(payload, requirements, state)
    if not valid:
        state.setdefault("failed_attempts", []).append({
            "resource": resource,
            "demo_payment_id": demo_payment_id,
            "stage": "verify",
            "reason": reason,
            "amount_moved": 0,
            "receipt": None,
            "logical_time": state.get("logical_clock", 0),
        })
        return (402, request_without_payment(
            resource, requirements, demo_payment_id))
    ok, settlement = facilitator.settle(payload, requirements, state)
    if not ok:
        state.setdefault("failed_attempts", []).append({
            "resource": resource,
            "demo_payment_id": demo_payment_id,
            "stage": "settle",
            "reason": settlement.get("error"),
            "amount_moved": 0,
            "receipt": None,
            "logical_time": state.get("logical_clock", 0),
        })
        return (402, request_without_payment(
            resource, requirements, demo_payment_id))
    receipt = issue_receipt(
        state, settlement, demo_payment_id, resource,
        settlement["payer"], settlement["payee"],
        settlement["amount_atomic"], related={})
    served = serve(receipt, settlement)
    return (200, {
        "status": 200,
        "resource": resource,
        "served": served,
        "x_payment_response": {
            "success": True,
            "transaction": settlement["transaction"],
            "settlement_id": settlement["settlement_id"],
            "payer": settlement["payer"],
            "payee": settlement["payee"],
            "amount_atomic": settlement["amount_atomic"],
            "receipt_id": receipt["receipt_id"],
        },
        "receipt": receipt,
    })
