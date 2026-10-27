#!/usr/bin/env python3
"""TESSERACT marketplace simulated facilitator — x402 shape, SIM-USDC only.

Implements the x402Version 1 / scheme "exact" message shape against a
LOCAL simulated ledger. No network calls, no chain calls, no wallets,
no private keys, no cryptographic signing: the signature field carries
the literal marker "sim-signature-not-cryptographic", which is
deliberately impossible to confuse with a real authorization.

Swappable seam: the resource server depends ONLY on the Facilitator
interface below (supported / verify / settle). A future real
facilitator would implement the same three methods; roster,
subscription, hire, entitlement, ledger-receipt, and dashboard code
would not change. The real facilitator is NOT built in this round.

Determinism: every ID comes from ledger counters (no randomness, no
wall clock). Simulated logical time is an integer sequence owned by
the ledger; verify/settle never read the wall clock.

verify() is read-only: it consumes no nonce and moves no balance.
settle() re-runs the material checks and, only on success, moves the
balance, consumes the nonce, and appends a settlement journal entry —
atomically (all of those, or none).
"""

SIM_SIGNATURE = "sim-signature-not-cryptographic"
X402_VERSION = 1
SCHEME = "exact"
NETWORK = "simulated"
ASSET = "SIM-USDC"
DECIMALS = 6
MAX_WINDOW = 60


class Facilitator:
    """Interface every facilitator backend must implement."""

    def supported(self):
        """Return the supported (x402Version, scheme, network, asset)."""
        raise NotImplementedError

    def verify(self, payload, requirements, state):
        """Validate a payment payload against requirements.

        Returns (valid, reason, payer): reason is None when valid, else
        one of the refusal reasons below. Never mutates state.
        """
        raise NotImplementedError

    def settle(self, payload, requirements, state):
        """Settle a verified payment.

        Returns (ok, result): result carries transaction/settlement IDs
        on success, or an error reason on failure. On failure nothing
        moves, no nonce is consumed, no journal entry is written.
        """
        raise NotImplementedError


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _malformed(payload, requirements):
    """Payload/requirements shape check (version included)."""
    if not isinstance(payload, dict) or not isinstance(requirements, dict):
        return True
    if payload.get("x402Version") != X402_VERSION:
        return True
    if payload.get("scheme") != requirements.get("scheme"):
        return True
    inner = payload.get("payload")
    if not isinstance(inner, dict):
        return True
    if not isinstance(inner.get("signature"), str):
        return True
    auth = inner.get("authorization")
    if not isinstance(auth, dict):
        return True
    for key in ("from", "to", "value", "validAfter", "validBefore", "nonce"):
        if key not in auth:
            return True
    if not isinstance(auth["from"], str) or not isinstance(auth["to"], str):
        return True
    if not isinstance(auth["value"], str):
        return True
    if not _is_int(auth["validAfter"]) or not _is_int(auth["validBefore"]):
        return True
    if not isinstance(auth["nonce"], str) or not auth["nonce"]:
        return True
    for key in ("scheme", "network", "maxAmountRequired", "payTo", "asset"):
        if key not in requirements:
            return True
    return False


class SimulatedFacilitator(Facilitator):
    """Local simulated facilitator over a marketplace ledger dict."""

    def supported(self):
        return {
            "x402Version": X402_VERSION,
            "scheme": SCHEME,
            "network": NETWORK,
            "asset": ASSET,
        }

    def verify(self, payload, requirements, state):
        if _malformed(payload, requirements):
            return (False, "malformed_payload", None)
        auth = payload["payload"]["authorization"]
        if payload.get("scheme") != SCHEME or requirements.get("scheme") != SCHEME:
            return (False, "scheme_mismatch", None)
        if payload.get("network") != NETWORK or requirements.get("network") != NETWORK:
            return (False, "network_mismatch", None)
        if requirements.get("asset") != ASSET:
            return (False, "asset_mismatch", None)
        payer = auth["from"]
        accounts = {a["account"]: a for a in state.get("accounts", [])}
        if payer not in accounts:
            return (False, "unknown_payer", None)
        if auth["to"] != requirements["payTo"]:
            return (False, "payto_mismatch", payer)
        if auth["value"] != str(requirements["maxAmountRequired"]):
            return (False, "amount_mismatch", payer)
        if payload["payload"].get("signature") != SIM_SIGNATURE:
            return (False, "simulated_signature_required", payer)
        now = state.get("logical_clock", 0)
        if now < auth["validAfter"]:
            return (False, "authorization_not_yet_valid", payer)
        if now > auth["validBefore"]:
            return (False, "authorization_expired", payer)
        if auth["validBefore"] - auth["validAfter"] > MAX_WINDOW:
            return (False, "malformed_payload", payer)
        if auth["nonce"] in {n for n in state.get("used_nonces", [])}:
            return (False, "nonce_reused", payer)
        if accounts[payer]["balance_atomic"] < int(auth["value"]):
            return (False, "insufficient_sim_balance", payer)
        return (True, None, payer)

    def settle(self, payload, requirements, state):
        valid, reason, payer = self.verify(payload, requirements, state)
        if not valid:
            return (False, {"error": reason})
        auth = payload["payload"]["authorization"]
        amount = int(auth["value"])
        accounts = {a["account"]: a for a in state.get("accounts", [])}
        payee = auth["to"]
        if payee not in accounts:
            return (False, {"error": "unknown_payee"})
        # Atomic: all mutations below happen together, only on success.
        counters = state.setdefault("counters", {})
        counters["transaction"] = counters.get("transaction", 0) + 1
        counters["settlement"] = counters.get("settlement", 0) + 1
        transaction = "SIM-TX-MP-%06d" % counters["transaction"]
        settlement = "SIM-STL-MP-%06d" % counters["settlement"]
        accounts[payer]["balance_atomic"] -= amount
        accounts[payee]["balance_atomic"] += amount
        state.setdefault("used_nonces", []).append(auth["nonce"])
        state.setdefault("settlement_journal", []).append({
            "settlement_id": settlement,
            "transaction": transaction,
            "payer": payer,
            "payee": payee,
            "amount_atomic": amount,
            "asset": ASSET,
            "scheme": SCHEME,
            "network": NETWORK,
            "logical_time": state.get("logical_clock", 0),
            "success": True,
        })
        return (True, {
            "transaction": transaction,
            "settlement_id": settlement,
            "payer": payer,
            "payee": payee,
            "amount_atomic": amount,
        })
