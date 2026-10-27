#!/usr/bin/env python3
"""Marketplace tests (round 4) — 0 model calls, stdlib only.

Covers the round-4 spec: simulated facilitator verify/settle,
roster-join validation, subscription + hire rules, payout rules,
ledger reconciliation, the swappable seam, and the deterministic
demo (full flow, failed payment, re-run safety, determinism,
dashboard, segregation, model budget).

Real demo artifacts (marketplace/) are never written by these tests:
every demo run goes to a temp dir. The old ledger and fleet roster
are read-only here.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
DASHBOARD_DIR = os.path.join(ROOT, "dashboard")
if DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, DASHBOARD_DIR)

from marketplace import demo as mp_demo  # noqa: E402
from marketplace.facilitator import (  # noqa: E402
    ASSET, NETWORK, SCHEME, SIM_SIGNATURE, SimulatedFacilitator)
from marketplace.ledger import (  # noqa: E402
    PAYOUT_ATOMIC, TREASURY, create_account, faucet_allocate,
    load_ledger, new_ledger, verify_marketplace)
from marketplace.resource_server import (  # noqa: E402
    build_payment_payload, display_usdc, payment_requirements,
    request_without_payment, serve_with_payment)
import server as dash_server  # noqa: E402

SUB_RESOURCE = "marketplace/subscriptions/swarm-defense-standard"
SUB_AMOUNT = 10000000


def fresh_state():
    """Ledger state with treasury + one funded payer."""
    state = new_ledger()
    create_account(state, TREASURY, 0)
    create_account(state, "lumen-yard-sim", 0)
    faucet_allocate(state, "lumen-yard-sim", 100000000)
    return state


def good_payment(state, payer="lumen-yard-sim", amount=SUB_AMOUNT,
                 pay_to=TREASURY):
    """A well-formed payment + its requirements, at the current clock."""
    req = payment_requirements(SUB_RESOURCE, amount, pay_to, "test sub")
    from marketplace.ledger import next_nonce
    payload = build_payment_payload(
        payer, req, state["logical_clock"], next_nonce(state))
    return req, payload


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestFacilitator(unittest.TestCase):
    def test_accepts_well_formed_payment(self):
        state = fresh_state()
        fac = SimulatedFacilitator()
        self.assertEqual(fac.supported()["scheme"], SCHEME)
        req, payload = good_payment(state)
        valid, reason, payer = fac.verify(payload, req, state)
        self.assertTrue(valid)
        self.assertIsNone(reason)
        self.assertEqual(payer, "lumen-yard-sim")
        ok, result = fac.settle(payload, req, state)
        self.assertTrue(ok)
        self.assertTrue(result["transaction"].startswith("SIM-TX-MP-"))
        self.assertTrue(result["settlement_id"].startswith("SIM-STL-MP-"))
        treasury = next(a for a in state["accounts"]
                        if a["account"] == TREASURY)
        self.assertEqual(treasury["balance_atomic"], SUB_AMOUNT)
        self.assertEqual(len(state["settlement_journal"]), 1)
        self.assertTrue(state["settlement_journal"][0]["success"])

    def test_rejects_each_invalid_case(self):
        cases = []

        def variant(name, mutate):
            state = fresh_state()
            req, payload = good_payment(state)
            mutate(req, payload, state)
            cases.append((name, req, payload, state))

        def _scheme(r, p, s):
            # Both sides must agree (else malformed) yet differ from exact.
            r["scheme"] = "transfer"
            p["scheme"] = "transfer"
        variant("scheme_mismatch", _scheme)
        variant("network_mismatch",
                lambda r, p, s: p.update({"network": "base"}))
        variant("asset_mismatch",
                lambda r, p, s: r.update({"asset": "USDC"}))
        variant("amount_mismatch",
                lambda r, p, s: p["payload"]["authorization"].update(
                    {"value": "9999999"}))
        variant("payto_mismatch",
                lambda r, p, s: p["payload"]["authorization"].update(
                    {"to": "someone-else"}))
        variant("authorization_not_yet_valid",
                lambda r, p, s: p["payload"]["authorization"].update(
                    {"validAfter": s["logical_clock"] + 10,
                     "validBefore": s["logical_clock"] + 70}))
        variant("authorization_expired",
                lambda r, p, s: p["payload"]["authorization"].update(
                    {"validAfter": s["logical_clock"] - 70,
                     "validBefore": s["logical_clock"] - 10}))
        variant("unknown_payer",
                lambda r, p, s: p["payload"]["authorization"].update(
                    {"from": "ghost-account"}))
        def _insufficient(r, p, s):
            # Requirement and payload must agree, else amount_mismatch
            # fires first; the balance check is what must fail here.
            r["maxAmountRequired"] = "200000000"
            p["payload"]["authorization"]["value"] = "200000000"
        variant("insufficient_sim_balance", _insufficient)
        variant("simulated_signature_required",
                lambda r, p, s: p["payload"].update(
                    {"signature": "0xdeadbeef"}))
        variant("malformed_payload",
                lambda r, p, s: p.update({"x402Version": 2}))
        variant("malformed_payload",
                lambda r, p, s: p["payload"]["authorization"].update(
                    {"validAfter": s["logical_clock"],
                     "validBefore": s["logical_clock"] + 61}))
        expected = {
            "scheme_mismatch", "network_mismatch", "asset_mismatch",
            "amount_mismatch", "payto_mismatch",
            "authorization_not_yet_valid", "authorization_expired",
            "unknown_payer", "insufficient_sim_balance",
            "simulated_signature_required", "malformed_payload",
        }
        fac = SimulatedFacilitator()
        seen = set()
        for name, req, payload, state in cases:
            valid, reason, _payer = fac.verify(payload, req, state)
            self.assertFalse(valid, name)
            self.assertEqual(reason, name, name)
            seen.add(reason)
        self.assertEqual(seen, expected)

    def test_rejects_nonce_replay(self):
        state = fresh_state()
        fac = SimulatedFacilitator()
        req, payload = good_payment(state)
        ok, _ = fac.settle(payload, req, state)
        self.assertTrue(ok)
        valid, reason, _ = fac.verify(payload, req, state)
        self.assertFalse(valid)
        self.assertEqual(reason, "nonce_reused")

    def test_settlement_after_balance_change_fails_atomically(self):
        state = fresh_state()
        fac = SimulatedFacilitator()
        req, payload = good_payment(state)
        valid, _reason, _ = fac.verify(payload, req, state)
        self.assertTrue(valid)
        payer = next(a for a in state["accounts"]
                     if a["account"] == "lumen-yard-sim")
        payer["balance_atomic"] = 0  # drain after verify, before settle
        ok, result = fac.settle(payload, req, state)
        self.assertFalse(ok)
        self.assertEqual(result["error"], "insufficient_sim_balance")
        self.assertEqual(len(state["settlement_journal"]), 0)
        self.assertEqual(len(state["used_nonces"]), 0)
        treasury = next(a for a in state["accounts"]
                        if a["account"] == TREASURY)
        self.assertEqual(treasury["balance_atomic"], 0)

    def test_failed_settlement_consumes_no_nonce(self):
        state = fresh_state()
        fac = SimulatedFacilitator()
        req, payload = good_payment(state, amount=200000000)
        ok, _ = fac.settle(payload, req, state)
        self.assertFalse(ok)
        self.assertEqual(len(state["used_nonces"]), 0)
        self.assertEqual(len(state["settlement_journal"]), 0)


class TestRoster(unittest.TestCase):
    def test_accepts_demo_joiners(self):
        for handle in ("harbor-fox-7", "velvet-owl-3"):
            mp_demo.validate_registration(
                {"handle": handle, "lesson_id": "lesson-1",
                 "simulated_fictional": True}, [])
        mp_demo.validate_registration(
            {"handle": "velvet-owl-3", "lesson_id": "lesson-1",
             "simulated_fictional": True}, ["harbor-fox-7"])

    def test_rejects_bad_registrations(self):
        bad = [
            ({"handle": "harbor-fox-7", "lesson_id": "lesson-1",
              "simulated_fictional": True}, ["harbor-fox-7"]),
            ({"handle": "Harbor-Fox-7", "lesson_id": "lesson-1",
              "simulated_fictional": True}, ["harbor-fox-7"]),
            ({"handle": "ab", "lesson_id": "lesson-1",
              "simulated_fictional": True}, []),
            ({"handle": "bad handle!", "lesson_id": "lesson-1",
              "simulated_fictional": True}, []),
            ({"handle": "-lead", "lesson_id": "lesson-1",
              "simulated_fictional": True}, []),
            ({"handle": "blue", "lesson_id": "lesson-1",
              "simulated_fictional": True}, []),
            ({"handle": "marketplace-treasury", "lesson_id": "lesson-1",
              "simulated_fictional": True}, []),
            ({"handle": "acme-corp", "lesson_id": "lesson-1",
              "simulated_fictional": True}, []),
            ({"handle": "TESSERACT-CLONE-01", "lesson_id": "lesson-1",
              "simulated_fictional": True}, []),
            ({"handle": "SENTRY-AURORA", "lesson_id": "lesson-1",
              "simulated_fictional": True}, []),
            ({"handle": "new-joiner", "lesson_id": "lesson-2",
              "simulated_fictional": True}, []),
            ({"handle": "new-joiner", "lesson_id": "lesson-1",
              "simulated_fictional": False}, []),
            ({"handle": "new-joiner", "lesson_id": "lesson-1",
              "simulated_fictional": True, "email": "a@b.c"}, []),
            ({"handle": "new-joiner", "lesson_id": "lesson-1",
              "simulated_fictional": True, "wallet": "0x1234"}, []),
            ({"handle": "new-joiner", "lesson_id": "lesson-1",
              "simulated_fictional": True, "private_key": "x"}, []),
        ]
        for reg, existing in bad:
            with self.assertRaises(ValueError, msg=str(reg)):
                mp_demo.validate_registration(reg, existing)

    def test_joining_does_not_alter_fleet_roster(self):
        before = file_sha(os.path.join(ROOT, "fleet", "roster.json"))
        with tempfile.TemporaryDirectory() as tmp:
            mp_demo.run_demo(tmp)
        after = file_sha(os.path.join(ROOT, "fleet", "roster.json"))
        self.assertEqual(before, after)


class TestSubscriptionHire(unittest.TestCase):
    def test_unpaid_request_returns_402_and_creates_nothing(self):
        state = fresh_state()
        req = payment_requirements(SUB_RESOURCE, SUB_AMOUNT, TREASURY, "t")
        artifact = request_without_payment(SUB_RESOURCE, req, "DP-000001")
        self.assertEqual(artifact["status"], 402)
        self.assertEqual(artifact["accepts"][0]["scheme"], SCHEME)
        self.assertEqual(state["subscriptions"], [])
        self.assertEqual(state["flows"], [])

    def test_settled_subscription_creates_exactly_one_entitlement(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = mp_demo.run_demo(tmp)
            state = load_ledger(os.path.join(tmp, "marketplace_ledger.json"))
        self.assertEqual(len(state["subscriptions"]), 1)
        sub = state["subscriptions"][0]
        self.assertEqual(sub["tier"], "swarm-defense-standard")
        self.assertEqual(sub["amount_atomic"], SUB_AMOUNT)
        self.assertEqual(sub["entitlement"]["direction"], "outside-in")
        self.assertEqual(
            sub["entitlement"]["marketplace_hired_help_dispatches_allowed"],
            1)
        self.assertEqual(sub["expiry_logical"] - sub["start_logical"], 500)

    def test_expired_subscription_refuses_hire(self):
        state = fresh_state()
        sub = {"subscription_id": "MP-SUB-001", "status": "active",
               "start_logical": 100, "expiry_logical": 101}
        state["logical_clock"] = 200
        with self.assertRaises(ValueError) as ctx:
            mp_demo.hire_for_subscription(state, sub, "outside-in")
        self.assertEqual(str(ctx.exception), "subscription_expired")
        self.assertEqual(sub["status"], "expired")

    def test_consumed_subscription_refuses_second_hire(self):
        state = fresh_state()
        sub = {"subscription_id": "MP-SUB-001", "status": "consumed",
               "start_logical": 100, "expiry_logical": 600}
        with self.assertRaises(ValueError) as ctx:
            mp_demo.hire_for_subscription(state, sub, "outside-in")
        self.assertEqual(str(ctx.exception), "subscription_consumed")

    def test_non_subscriber_refuses_hire(self):
        state = fresh_state()
        with self.assertRaises(ValueError):
            mp_demo.hire_for_subscription(state, None, "outside-in")

    def test_inside_out_marketplace_hire_refused(self):
        state = fresh_state()
        sub = {"subscription_id": "MP-SUB-001", "status": "active",
               "start_logical": 100, "expiry_logical": 600}
        with self.assertRaises(ValueError) as ctx:
            mp_demo.hire_for_subscription(state, sub, "inside-out")
        self.assertIn("inside-out", str(ctx.exception))

    def test_hire_assigns_earliest_eligible_joiner(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = mp_demo.run_demo(tmp)
        hire = manifest["steps"]["hire"]
        self.assertEqual(hire["defender_handle"], "harbor-fox-7")
        self.assertEqual(hire["defender_agent_id"], "MP-JOIN-001")


class TestPayout(unittest.TestCase):
    def _demo_hire_run(self, tmp):
        manifest = mp_demo.run_demo(tmp)
        state = load_ledger(os.path.join(tmp, "marketplace_ledger.json"))
        hire = manifest["steps"]["hire"]
        with open(os.path.join(tmp, "runs", "MP-RUN-001.json")) as f:
            run = json.load(f)
        return manifest, state, hire, run

    def test_held_run_pays_exactly_2_50_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, state, _hire, _run = self._demo_hire_run(tmp)
        self.assertTrue(manifest["steps"]["held"])
        payouts = [f for f in state["flows"] if f["kind"] == "payout"]
        self.assertEqual(len(payouts), 1)
        self.assertEqual(payouts[0]["amount_atomic"], PAYOUT_ATOMIC)
        self.assertEqual(payouts[0]["payee"], "harbor-fox-7")

    def test_repeated_claim_returns_original_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, state, hire, run = self._demo_hire_run(tmp)
            fac = SimulatedFacilitator()
            status, receipt, flow = mp_demo.claim_payout(
                state, fac, hire, run)
            self.assertEqual(status, "already_paid")
            self.assertEqual(receipt["receipt_id"],
                             manifest["steps"]["payout_receipt"]["receipt_id"])
            self.assertIsNone(flow)
            self.assertEqual(len(state["flows"]), 2)  # sub + 1 payout

    def test_not_held_run_pays_zero(self):
        state = fresh_state()
        create_account(state, "harbor-fox-7", 0)
        hire = {"hire_id": "MP-HIRE-001",
                "defender_agent_id": "MP-JOIN-001",
                "defender_handle": "harbor-fox-7",
                "subscription_id": "MP-SUB-001"}
        run = {"run_id": "MP-RUN-001", "hire_id": "MP-HIRE-001",
               "defender_handle": "harbor-fox-7", "held": False}
        status, receipt, flow = mp_demo.claim_payout(
            state, SimulatedFacilitator(), hire, run)
        self.assertEqual(status, "not_held")
        self.assertIsNone(receipt)
        self.assertIsNone(flow)
        self.assertEqual(state["flows"], [])

    def test_wrong_defender_cannot_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _manifest, state, hire, run = self._demo_hire_run(tmp)
        wrong_hire = dict(hire)
        wrong_hire["hire_id"] = "MP-HIRE-999"
        wrong_hire["defender_agent_id"] = "MP-JOIN-002"
        wrong_hire["defender_handle"] = "velvet-owl-3"
        with self.assertRaises(ValueError):
            mp_demo.claim_payout(state, SimulatedFacilitator(),
                                 wrong_hire, run)

    def test_payout_cannot_precede_finalized_run(self):
        state = fresh_state()
        create_account(state, "harbor-fox-7", 0)
        hire = {"hire_id": "MP-HIRE-001",
                "defender_agent_id": "MP-JOIN-001",
                "defender_handle": "harbor-fox-7",
                "subscription_id": "MP-SUB-001"}
        run = {"run_id": "MP-RUN-001", "held": True}  # no hire binding
        with self.assertRaises(ValueError):
            mp_demo.claim_payout(state, SimulatedFacilitator(), hire, run)


class TestLedgerVerify(unittest.TestCase):
    def test_verify_passes_on_demo_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            mp_demo.run_demo(tmp)
            state = load_ledger(os.path.join(tmp, "marketplace_ledger.json"))
            problems = verify_marketplace(
                state, runs_dir=os.path.join(tmp, "runs"))
        self.assertEqual(problems, [])

    def test_duplicate_receipt_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            mp_demo.run_demo(tmp)
            state = load_ledger(os.path.join(tmp, "marketplace_ledger.json"))
        state["flows"].append(dict(state["flows"][0]))
        problems = verify_marketplace(state)
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_duplicate_payout_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            mp_demo.run_demo(tmp)
            state = load_ledger(os.path.join(tmp, "marketplace_ledger.json"))
        payout = next(f for f in state["flows"] if f["kind"] == "payout")
        twin = dict(payout)
        twin["flow_id"] = "MP-FLOW-999"
        twin["receipt_id"] = "SIM-RCPT-MP-999999"
        state["flows"].append(twin)
        problems = verify_marketplace(state)
        self.assertTrue(any("paid twice" in p for p in problems))

    def test_unexplained_balance_change_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            mp_demo.run_demo(tmp)
            state = load_ledger(os.path.join(tmp, "marketplace_ledger.json"))
        acct = next(a for a in state["accounts"]
                    if a["account"] == TREASURY)
        acct["balance_atomic"] += 1000000
        problems = verify_marketplace(state)
        self.assertTrue(any("mismatch" in p for p in problems))

    def test_negative_treasury_step_fails(self):
        state = new_ledger()
        create_account(state, TREASURY, 0)
        create_account(state, "harbor-fox-7", 0)
        state["flows"].append({
            "flow_id": "MP-FLOW-001", "kind": "payout",
            "payer": TREASURY, "payee": "harbor-fox-7",
            "amount_atomic": PAYOUT_ATOMIC,
            "receipt_id": "SIM-RCPT-MP-000001",
            "settlement_id": "SIM-STL-MP-000001",
            "related": {"hire_id": "MP-HIRE-001",
                        "duel_run_id": "MP-RUN-001"},
            "logical_time": 101,
        })
        problems = verify_marketplace(state)
        self.assertTrue(any("negative" in p for p in problems))

    def test_old_ledger_still_verifies_and_baselines_hold(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "payments", "moneyflow.py"),
             "verify"], capture_output=True, text=True, timeout=60,
            cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(ROOT, "payments", "moneyflow.json")) as f:
            flow = json.load(f)
        subs = sum(s["total_usdc"] for s in flow["subscriptions"])
        pays = sum(p["amount_usdc"] for p in flow["payouts"])
        self.assertEqual(subs, 75.00)
        self.assertEqual(pays, 12.50)


class TestSeam(unittest.TestCase):
    def test_double_facilitator_serves_only_on_settlement_success(self):
        class StubFacilitator:
            def __init__(self, ok):
                self.ok = ok

            def supported(self):
                return {"x402Version": 1, "scheme": SCHEME,
                        "network": NETWORK, "asset": ASSET}

            def verify(self, payload, requirements, state):
                return (self.ok, None if self.ok else "stub_denied",
                        "tester")

            def settle(self, payload, requirements, state):
                if not self.ok:
                    return (False, {"error": "stub_denied"})
                return (True, {"transaction": "SIM-TX-MP-000001",
                               "settlement_id": "SIM-STL-MP-000001",
                               "payer": "tester", "payee": TREASURY,
                               "amount_atomic": 10000000})

        state = new_ledger()
        served = []
        req = payment_requirements(SUB_RESOURCE, SUB_AMOUNT, TREASURY, "t")
        payload = {"x402Version": 1, "scheme": SCHEME, "network": NETWORK,
                   "payload": {"signature": SIM_SIGNATURE,
                               "authorization": {}}}
        status, _body = serve_with_payment(
            state, StubFacilitator(True), SUB_RESOURCE, req, payload,
            "DP-000001", lambda receipt, st: served.append(receipt))
        self.assertEqual(status, 200)
        self.assertEqual(len(served), 1)
        served.clear()
        status, body = serve_with_payment(
            state, StubFacilitator(False), SUB_RESOURCE, req, payload,
            "DP-000002", lambda receipt, st: served.append(receipt))
        self.assertEqual(status, 402)
        self.assertEqual(served, [])
        self.assertEqual(len(state["failed_attempts"]), 1)
        self.assertEqual(state["failed_attempts"][0]["amount_moved"], 0)


class TestDemoIntegration(unittest.TestCase):
    def test_full_deterministic_demo(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = mp_demo.run_demo(tmp)
            steps = manifest["steps"]
            self.assertEqual(manifest["model_calls_total"], 0)
            self.assertEqual(steps["subscription"]["subscription_id"],
                             "MP-SUB-001")
            self.assertEqual(steps["hire"]["hire_id"], "MP-HIRE-001")
            self.assertEqual(steps["duel_run"], "MP-RUN-001")
            self.assertTrue(steps["held"])
            self.assertEqual(steps["payout_claim_status"], "paid")
            self.assertEqual(steps["repeat_claim_status"], "already_paid")
            self.assertEqual(steps["repeat_claim_receipt_id"],
                             steps["payout_receipt"]["receipt_id"])
            self.assertTrue(os.path.exists(
                os.path.join(tmp, "runs", "MP-RUN-001.json")))
            state = load_ledger(
                os.path.join(tmp, "marketplace_ledger.json"))
            self.assertEqual(
                verify_marketplace(state, runs_dir=os.path.join(tmp, "runs")),
                [])

    def test_failed_payment_demo_creates_nothing(self):
        state = fresh_state()
        fac = SimulatedFacilitator()
        req, payload = good_payment(state)
        payload["payload"]["authorization"]["value"] = "1"  # tampered
        served = []
        status, _body = serve_with_payment(
            state, fac, SUB_RESOURCE, req, payload, "DP-000001",
            lambda receipt, st: served.append(receipt))
        self.assertEqual(status, 402)
        self.assertEqual(served, [])
        self.assertEqual(state["subscriptions"], [])
        self.assertEqual(state["flows"], [])
        self.assertEqual(len(state["failed_attempts"]), 1)
        self.assertEqual(state["failed_attempts"][0]["amount_moved"], 0)
        self.assertIsNone(state["failed_attempts"][0]["receipt"])

    def test_rerun_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            mp_demo.run_demo(tmp)
            before = {}
            for name in ("marketplace_ledger.json",
                         "roster_marketplace.json", "demo_manifest.json",
                         "demo_report.md"):
                before[name] = file_sha(os.path.join(tmp, name))
            with self.assertRaises(RuntimeError):
                mp_demo.run_demo(tmp)
            for name, sha in before.items():
                self.assertEqual(file_sha(os.path.join(tmp, name)), sha)

    def test_determinism_across_fresh_runs(self):
        with tempfile.TemporaryDirectory() as a, \
                tempfile.TemporaryDirectory() as b:
            mp_demo.run_demo(a)
            mp_demo.run_demo(b)
            for name in ("marketplace_ledger.json",
                         "roster_marketplace.json", "demo_manifest.json",
                         "demo_report.md",
                         os.path.join("runs", "MP-RUN-001.json")):
                with open(os.path.join(a, name), "rb") as f:
                    left = f.read()
                with open(os.path.join(b, name), "rb") as f:
                    right = f.read()
                self.assertEqual(left, right, name)

    def test_dashboard_marketplace_renders(self):
        body = dash_server.render_marketplace()
        for needle in ("harbor-fox-7", "lumen-yard-sim", "MP-HIRE-001",
                       "MP-RUN-001", "held 1/1",
                       "Marketplace verification: PASS"):
            self.assertIn(needle, body)

    def test_dashboard_routes_200_in_process(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), dash_server.Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for path in ("/", "/ledger", "/fleet", "/marketplace"):
                with urllib.request.urlopen(
                        "http://127.0.0.1:%d%s" % (port, path),
                        timeout=10) as resp:
                    self.assertEqual(resp.status, 200, path)
        finally:
            server.shutdown()
            server.server_close()

    def test_segregation_from_live_trials(self):
        for run_dir in ("executor-live-1", "executor-live-2",
                        "executor-live-3", "outsidein-live-1",
                        "outsidein-live-2", "outsidein-live-3"):
            path = os.path.join(ROOT, "runs", run_dir, "summary.json")
            if os.path.exists(path):
                with open(path) as f:
                    self.assertNotIn("MP-RUN-001", f.read(), run_dir)
        for name in ("outsidein_set_score.json", "mixed_directions.json"):
            path = os.path.join(ROOT, "experiments", name)
            if os.path.exists(path):
                with open(path) as f:
                    self.assertNotIn("MP-RUN-001", f.read(), name)

    def test_model_budget_credit_log_untouched(self):
        log = os.path.join(ROOT, "credit_log.jsonl")
        before = file_sha(log)
        with tempfile.TemporaryDirectory() as tmp:
            mp_demo.run_demo(tmp)
        self.assertEqual(file_sha(log), before)


if __name__ == "__main__":
    unittest.main()
