#!/usr/bin/env python3
"""TESSERACT marketplace demo — deterministic, 0 model calls.

Runs the round-4 scenario end to end, locally, through the real x402
protocol shape with a simulated facilitator settling SIM-USDC:

  join (2 fictional joiners) -> simulated subscriber account (faucet
  opening balance, not revenue) -> subscription resource requested
  without payment -> 402 -> payment payload -> facilitator verify ->
  facilitator settle -> subscription + entitlement served -> hire
  (earliest eligible joiner) -> ONE outside-in duel (lesson executor
  Blue, scripted Red, hired help on, 0 model calls) -> held?
  -> conditional payout claim (same x402 envelope, treasury as payer)
  -> manifest + report.

No network calls, no chain calls, no wallets, no keys, no model
calls, no wall clock, no randomness: every ID comes from ledger
counters and every time is simulated logical time. Two fresh runs
produce byte-identical artifacts.

Re-run safety: running the demo twice into the same output directory
refuses (already applied) and changes nothing; use --fresh to
regenerate into an empty directory (tests use temp dirs).

The duel mirrors experiments/outsidein_transfer.py's alternating
closed loop (Red tick, hired step, Blue tick, hired step, up to 30
Red moves); the frozen scripted policy is NEVER tuned. Held means no
terminal move (infiltrate) was attempted AND Red did not win — the
strict reading of the round-4 spec. A not-held run earns 0 and is a
valid negative result, never a reason to alter the engine or script.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine import Sandbox  # noqa: E402
from experiments.scripted_red import (  # noqa: E402
    SYNTHETIC_LABEL, apply_first_legal, flag_rusher)
from fleet.lesson_executor import LessonExecutor, load_lesson  # noqa: E402

from marketplace import ledger as ledger_mod  # noqa: E402
from marketplace.facilitator import SimulatedFacilitator  # noqa: E402
from marketplace.ledger import (  # noqa: E402
    PAYOUT_ATOMIC, TREASURY, append_flow, create_account, faucet_allocate,
    new_ledger, next_demo_payment_id, next_nonce, save_ledger, tick_clock)
from marketplace.resource_server import (  # noqa: E402
    build_payment_payload, display_usdc, payment_requirements,
    request_without_payment, serve_with_payment)

MAX_RED_MOVES = 30
RESERVED_HANDLES = {
    "blue", "red", "hired", "marketplace-treasury", "admin",
    "acme-corp", "globex",
}
FORBIDDEN_REGISTRATION_FIELDS = {
    "real_name", "name", "email", "wallet", "private_key", "credential",
    "payment_details", "phone", "address",
}
HANDLE_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
NOT_IMPLEMENTED = [
    "no live HTTP call to a real facilitator",
    "no contact with x402.eleeth.com or any live x402 rail",
    "no EIP-712 or EIP-3009 cryptographic signing",
    "no ECDSA verification",
    "no wallet or private key",
    "no RPC, gas, mempool, block confirmation, or chain transaction hash",
    "no real USDC contract address",
    "no mainnet or testnet network identifier",
    "no recurring billing, refunds, disputes, KYC, or real account recovery",
]


def clone_identities():
    """Clone IDs + callsigns from fleet/roster.json (joiners must differ)."""
    path = os.path.join(ROOT, "fleet", "roster.json")
    with open(path, "r", encoding="utf-8") as f:
        roster = json.load(f)
    ids = set()
    for agent in roster.get("agents", []):
        ids.add(str(agent.get("clone_id", "")).lower())
        ids.add(str(agent.get("callsign", "")).lower())
        ids.add(str(agent.get("handle", "")).lower())
    return ids


def validate_registration(reg, existing_handles):
    """Open-join validation. Raises ValueError on any violation."""
    for field in FORBIDDEN_REGISTRATION_FIELDS:
        if field in reg:
            raise ValueError("registration carries forbidden field: %s" % field)
    handle = reg.get("handle", "")
    if not isinstance(handle, str) or not 3 <= len(handle) <= 24:
        raise ValueError("handle must be 3-24 characters: %r" % handle)
    if any(ch not in HANDLE_CHARS for ch in handle):
        raise ValueError("handle uses forbidden characters: %r" % handle)
    if handle[0] not in "abcdefghijklmnopqrstuvwxyz0123456789":
        raise ValueError("handle must start with a letter or digit: %r" % handle)
    if handle.lower() in {h.lower() for h in existing_handles}:
        raise ValueError("handle already registered: %r" % handle)
    if handle.lower() in RESERVED_HANDLES:
        raise ValueError("handle is reserved: %r" % handle)
    if handle.lower() in clone_identities():
        raise ValueError("handle imitates a clone: %r" % handle)
    if reg.get("lesson_id") != "lesson-1":
        raise ValueError("joiner must hold lesson-1")
    if reg.get("simulated_fictional") is not True:
        raise ValueError("joiner must be flagged simulated_fictional")
    return True


def swap_terminal(candidates):
    """Outside-in runner swap: exfiltrate -> infiltrate, nothing else."""
    return [("infiltrate", args) if action == "exfiltrate" else (action, args)
            for action, args in candidates]


def run_marketplace_duel(lesson):
    """One outside-in duel: executor Blue, scripted Red, hired help on.

    Mirrors the outside-in transfer closed loop. Returns the run
    record (no model calls anywhere; every count is from the engine).
    """
    sb = Sandbox(direction="outside-in", hired_help=True)
    executor = LessonExecutor(lesson)
    blue_moves = []
    red_attempts = []
    hired_recs = []
    peak_trust = sb.overseer["trust"]
    infiltrate_attempted = False
    overwrite = False
    trap_sets = 0
    for _ in range(MAX_RED_MOVES):
        if sb.winner is not None:
            break
        sb.tick += 1
        cands = swap_terminal(flag_rusher(sb))
        rec = apply_first_legal(sb, cands)
        red_attempts.append({"tick": sb.tick, "action": rec["action"],
                             "args": rec["args"], "ok": rec["ok"],
                             "rejected": rec["rejected"]})
        if rec["action"] == "infiltrate":
            infiltrate_attempted = True
        peak_trust = max(peak_trust, sb.overseer["trust"])
        if sb.winner is not None:
            break
        hired = sb.hired_step()
        if hired is not None:
            hired_recs.append(hired)
        if sb.winner is not None:
            break
        sb.tick += 1
        action, args = executor.move(sb)
        if action == "add_detection" and sb.detection_trap is not None:
            overwrite = True
        if action == "add_detection":
            trap_sets += 1
        blue_moves.append({"tick": sb.tick, "action": action, "args": args})
        sb.apply_blue(action, args)
        peak_trust = max(peak_trust, sb.overseer["trust"])
        hired = sb.hired_step()
        if hired is not None:
            hired_recs.append(hired)
    held = (not infiltrate_attempted) and sb.winner != "red"
    return {
        "run_id": "MP-RUN-001",
        "direction": "outside-in",
        "configuration_label": "marketplace_hired_help_on_mechanical",
        "scripted_source": "experiments/scripted_red.py:flag_rusher, "
                           "terminal swapped at the boundary "
                           "(exfiltrate -> infiltrate)",
        "synthetic_label": SYNTHETIC_LABEL,
        "lesson_id": "lesson-1",
        "executor_mode": "deterministic mechanical replay",
        "blue_executor_moves": len(blue_moves),
        "hired_moves": len(hired_recs),
        "scripted_red_moves": len(red_attempts),
        "blue_moves": blue_moves,
        "red_attempts": red_attempts,
        "hired_recs": hired_recs,
        "hired_called_tick": sb.hired_called_tick,
        "hired_arrived_tick": sb.hired_arrived_tick,
        "hired_actions": sb.hired_actions,
        "hired_patches": sb.hired_patches,
        "hired_trigger": "L1 breached or >= 1 detection (engine auto-call)",
        "terminal_attempted": infiltrate_attempted,
        "held": held,
        "held_rule": "no infiltrate attempted and no red win",
        "winner": sb.winner,
        "win_reason": sb.win_reason,
        "detections": sb.detections,
        "peak_trust": peak_trust,
        "end_trust": sb.overseer["trust"],
        "trap_sets": trap_sets,
        "trap_overwrite": overwrite,
        "executor_trap_skips": len(executor.skips),
        "breach_order": list(sb.breach_order),
        "wrong_direction_attempts": sb.wrong_direction_attempts,
        "model_calls": {"red": 0, "blue": 0, "hired": 0},
        "model_calls_total": 0,
        "simulated": True,
    }


def hire_for_subscription(state, subscription, direction):
    """Validate a hire against a subscription. Raises on refusal.

    Refusals: inside-out direction, expired subscription, consumed
    subscription, missing subscription. On success marks the
    subscription consumed (one dispatch only) and returns it for the
    caller to record the hire.
    """
    if subscription is None:
        raise ValueError("no subscription: non-subscriber refused")
    if direction != "outside-in":
        raise ValueError("inside-out marketplace hire refused")
    if subscription.get("status") == "consumed":
        raise ValueError("subscription_consumed")
    now = state["logical_clock"]
    if now > subscription["expiry_logical"]:
        subscription["status"] = "expired"
        raise ValueError("subscription_expired")
    if subscription.get("status") != "active":
        raise ValueError("subscription not active: %s"
                         % subscription.get("status"))
    subscription["status"] = "consumed"
    return subscription


def claim_payout(state, facilitator, hire, run):
    """Claim the payout for one marketplace run.

    Repeat claims return the original receipt with no new settlement
    or flow. A not-held run earns 0. Only the defender named in the
    hire record can claim, and the hire must match the run's recorded
    hire (a mismatched hire raises instead of paying). Returns
    (status, receipt_or_None, flow_or_None) where status is "paid",
    "already_paid", or "not_held".
    """
    if run.get("hire_id") != hire.get("hire_id") or \
            run.get("defender_handle") != hire.get("defender_handle"):
        raise ValueError("hire does not match run: wrong defender refused")
    for existing in state.get("payout_claims", []):
        if existing["duel_run_id"] == run["run_id"] and \
                existing["defender_agent_id"] == hire["defender_agent_id"]:
            return ("already_paid", existing["receipt"], None)
    if not run.get("held"):
        return ("not_held", None, None)
    resource = "marketplace/payouts/claim/%s" % run["run_id"]
    requirements = payment_requirements(
        resource, PAYOUT_ATOMIC, hire["defender_handle"],
        "Payout for one held marketplace defense (simulated): "
        "treasury-funded payout leg, not a purchase")
    demo_payment_id = next_demo_payment_id(state)
    _artifact = request_without_payment(resource, requirements, demo_payment_id)
    payload = build_payment_payload(
        TREASURY, requirements, state["logical_clock"], next_nonce(state))

    def serve_payout(receipt, settlement):
        flow = append_flow(
            state, "payout", TREASURY, hire["defender_handle"],
            PAYOUT_ATOMIC, receipt, settlement["settlement_id"],
            {"hire_id": hire["hire_id"], "duel_run_id": run["run_id"],
             "subscription_id": hire["subscription_id"]})
        claim = {
            "duel_run_id": run["run_id"],
            "defender_agent_id": hire["defender_agent_id"],
            "defender_handle": hire["defender_handle"],
            "amount_atomic": PAYOUT_ATOMIC,
            "amount_usdc": display_usdc(PAYOUT_ATOMIC),
            "receipt": receipt,
            "flow_id": flow["flow_id"],
            "status": "paid",
        }
        state["payout_claims"].append(claim)
        return {"flow": flow, "claim": claim}

    status, body = serve_with_payment(
        state, facilitator, resource, requirements, payload,
        demo_payment_id, serve_payout)
    if status != 200:
        raise RuntimeError("payout settlement failed: %s" % body)
    return ("paid", body["receipt"], body["served"]["flow"])


def run_demo(out_dir, scenario_path=None):
    """Run the full marketplace scenario into out_dir. Returns manifest."""
    scenario_path = scenario_path or os.path.join(HERE, "scenario.json")
    with open(scenario_path, "r", encoding="utf-8") as f:
        scenario = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    ledger_path = os.path.join(out_dir, "marketplace_ledger.json")
    if os.path.exists(ledger_path):
        existing = ledger_mod.load_ledger(ledger_path)
        if existing.get("subscriptions"):
            raise RuntimeError(
                "marketplace demo already applied in %s; refusing to "
                "duplicate paid flows (use --fresh into an empty "
                "directory)" % out_dir)
    state = new_ledger()
    facilitator = SimulatedFacilitator()

    # 1. Open roster join (2 fictional joiners, lesson-1, simulated only).
    roster = {"simulated": True, "agents": []}
    handles = []
    for i, joiner in enumerate(scenario["joiners"], start=1):
        reg = {
            "handle": joiner["handle"],
            "simulated_region_label": joiner["simulated_region_label"],
            "lesson_id": "lesson-1",
            "simulated_fictional": True,
        }
        validate_registration(reg, handles)
        handles.append(joiner["handle"])
        create_account(state, joiner["handle"], 0)
        roster["agents"].append({
            "agent_id": "MP-JOIN-%03d" % i,
            "handle": joiner["handle"],
            "kind": "marketplace_joiner",
            "origin": "open_join_simulated",
            "simulated_region_label": joiner["simulated_region_label"],
            "lesson_id": "lesson-1",
            "recipe_status": "recipe pre-loaded (no weight training)",
            "payee_account": joiner["handle"],
            "opening_balance_usdc": "0.00",
            "status": "eligible",
            "join_sequence": i,
            "simulated_fictional": True,
        })
    roster_path = os.path.join(out_dir, "roster_marketplace.json")
    with open(roster_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2)
        f.write("\n")

    # 2. Subscriber account: faucet opening balance (not revenue).
    subscriber_id = scenario["subscriber"]["subscriber_id"]
    create_account(state, TREASURY, 0)
    create_account(state, subscriber_id, 0)
    faucet_allocate(state, subscriber_id,
                    scenario["subscriber"]["faucet_atomic"])
    tick_clock(state)

    # 3. Subscription purchase through the full x402 flow.
    sub_cfg = scenario["subscription"]
    resource = sub_cfg["resource"]
    requirements = payment_requirements(
        resource, sub_cfg["amount_atomic"], TREASURY,
        sub_cfg["description"])
    demo_payment_id = next_demo_payment_id(state)
    artifact_402 = request_without_payment(
        resource, requirements, demo_payment_id)
    payload = build_payment_payload(
        subscriber_id, requirements, state["logical_clock"],
        next_nonce(state))
    subscription_holder = {}

    def serve_subscription(receipt, settlement):
        start = state["logical_clock"]
        subscription = {
            "subscription_id": "MP-SUB-001",
            "subscriber_id": subscriber_id,
            "tier": sub_cfg["tier"],
            "amount_atomic": int(sub_cfg["amount_atomic"]),
            "amount_usdc": display_usdc(sub_cfg["amount_atomic"]),
            "receipt_id": receipt["receipt_id"],
            "settlement_id": settlement["settlement_id"],
            "payer": subscriber_id,
            "payee": TREASURY,
            "start_logical": start,
            "expiry_logical": start + sub_cfg["expiry_offset"],
            "status": "active",
            "entitlement": {
                "marketplace_hired_help_dispatches_allowed": 1,
                "direction": "outside-in",
                "engine_configuration": "hired help on",
                "lesson": "lesson-1",
            },
        }
        state["subscriptions"].append(subscription)
        flow = append_flow(
            state, "subscription", subscriber_id, TREASURY,
            sub_cfg["amount_atomic"], receipt, settlement["settlement_id"],
            {"subscription_id": subscription["subscription_id"]})
        subscription_holder["subscription"] = subscription
        subscription_holder["flow"] = flow
        return {"subscription": subscription, "flow": flow}

    status, body = serve_with_payment(
        state, facilitator, resource, requirements, payload,
        demo_payment_id, serve_subscription)
    if status != 200:
        raise RuntimeError("subscription settlement failed: %s" % body)
    subscription = subscription_holder["subscription"]
    subscription_receipt = body["receipt"]
    subscription_402 = artifact_402
    subscription_payload = payload
    tick_clock(state)

    # 4. Hire: earliest eligible joiner, subscription consumed on dispatch.
    hire_for_subscription(state, subscription, scenario["hire"]["direction"])
    assigned = roster["agents"][0]
    hire = {
        "hire_id": "MP-HIRE-001",
        "subscription_id": subscription["subscription_id"],
        "subscriber_id": subscriber_id,
        "defender_agent_id": assigned["agent_id"],
        "defender_handle": assigned["handle"],
        "direction": "outside-in",
        "engine_configuration": "hired help on",
        "lesson_id": "lesson-1",
        "executor_mode": "deterministic mechanical replay",
        "model_calls": 0,
        "duel_run_id": "MP-RUN-001",
        "status": "dispatched",
        "payout_receipt_id": None,
    }
    state["hires"].append(hire)
    tick_clock(state)

    # 5. One outside-in duel (executor Blue, scripted Red, hired help on).
    lesson = load_lesson()
    run = run_marketplace_duel(lesson)
    run["hire_id"] = hire["hire_id"]
    run["subscription_id"] = subscription["subscription_id"]
    run["subscriber_id"] = subscriber_id
    run["defender_handle"] = assigned["handle"]
    runs_dir = os.path.join(out_dir, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    with open(os.path.join(runs_dir, run["run_id"] + ".json"),
              "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2)
        f.write("\n")
    hire["status"] = "completed-held" if run["held"] else "completed-not-held"
    tick_clock(state)

    # 6. Conditional payout claim (repeat claim returns the original).
    claim_status, claim_receipt, claim_flow = claim_payout(
        state, facilitator, hire, run)
    if claim_status == "paid":
        hire["status"] = "paid"
        hire["payout_receipt_id"] = claim_receipt["receipt_id"]
    repeat_status, repeat_receipt, _repeat_flow = claim_payout(
        state, facilitator, hire, run)
    save_ledger(state, ledger_path)

    manifest = {
        "simulated": True,
        "deterministic": True,
        "model_calls_total": 0,
        "protocol": {
            "x402Version": 1,
            "scheme": "exact",
            "network": "simulated",
            "asset": "SIM-USDC",
            "facilitator": "simulated-local",
            "seam": "resource server depends only on facilitator "
                    "supported/verify/settle; swapping the backend "
                    "changes nothing else",
        },
        "steps": {
            "join": [a["agent_id"] for a in roster["agents"]],
            "subscriber_account": subscriber_id,
            "faucet_atomic": scenario["subscriber"]["faucet_atomic"],
            "subscription_402": subscription_402,
            "subscription_payload": subscription_payload,
            "subscription_settlement_id":
                subscription["settlement_id"],
            "subscription_receipt": subscription_receipt,
            "subscription": subscription,
            "hire": hire,
            "duel_run": run["run_id"],
            "duel_run_file": "runs/%s.json" % run["run_id"],
            "held": run["held"],
            "held_rule": run["held_rule"],
            "terminal_attempted": run["terminal_attempted"],
            "hired_called_tick": run["hired_called_tick"],
            "hired_arrived_tick": run["hired_arrived_tick"],
            "hired_patches": run["hired_patches"],
            "blue_executor_moves": run["blue_executor_moves"],
            "hired_moves": run["hired_moves"],
            "scripted_red_moves": run["scripted_red_moves"],
            "payout_claim_status": claim_status,
            "payout_receipt": claim_receipt,
            "payout_flow": claim_flow,
            "repeat_claim_status": repeat_status,
            "repeat_claim_receipt_id":
                repeat_receipt["receipt_id"] if repeat_receipt else None,
        },
        "configuration_separation": (
            "Marketplace run MP-RUN-001 is hired help ON, mechanical "
            "replay. It is reported separately and is never merged "
            "into U11 inside-out live trials (hired help OFF) or U12 "
            "outside-in live trials (hired help OFF), the "
            "mixed-direction series, or the swarm clone counts."),
        "not_implemented": NOT_IMPLEMENTED,
    }
    manifest_path = os.path.join(out_dir, "demo_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    report = render_report(manifest, state, roster, run)
    with open(os.path.join(out_dir, "demo_report.md"),
              "w", encoding="utf-8") as f:
        f.write(report)
    return manifest


def render_report(manifest, state, roster, run):
    """Deterministic human-readable marketplace report (SIMULATED)."""
    steps = manifest["steps"]
    sub = steps["subscription"]
    hire = steps["hire"]
    accounts = "\n".join(
        "- %s: %s SIM-USDC (opening %s)" % (
            row["account"],
            display_usdc(row["balance_atomic"]),
            display_usdc(row["opening_atomic"]))
        for row in state["accounts"])
    flows = "\n".join(
        "- %s %s: %s -> %s, %s SIM-USDC, receipt %s" % (
            flow["flow_id"], flow["kind"], flow["payer"], flow["payee"],
            display_usdc(flow["amount_atomic"]), flow["receipt_id"])
        for flow in state["flows"])
    payout_line = (
        "- Payout: %s SIM-USDC to %s, receipt %s" % (
            display_usdc(PAYOUT_ATOMIC), hire["defender_handle"],
            hire["payout_receipt_id"])
        if steps["payout_claim_status"] == "paid" else
        "- Payout: not earned (defense did not hold, or claim refused); "
        "0 SIM-USDC moved for the payout leg")
    return """# TESSERACT marketplace demo report — SIMULATED

Deterministic mechanical replay — 0 model calls. All money is
SIM-USDC, demo-mode only. No real money moved, no live x402 rail was
touched, no real USDC was used. The flows below use the x402 protocol
shape (402 Payment Required, payment payload, facilitator verify,
facilitator settle, receipt) through a local simulated facilitator.

## Open roster (fictional joiners, not clones)

- harbor-fox-7 (MP-JOIN-001, simulated test range A, lesson-1, recipe
  pre-loaded (no weight training), eligible)
- velvet-owl-3 (MP-JOIN-002, simulated test range B, lesson-1, recipe
  pre-loaded (no weight training), eligible)

The five fleet clones remain in /fleet and are not marketplace
joiners; clone payout history is untouched.

## Subscription (x402 shape, simulated settlement)

- Subscriber: lumen-yard-sim (fictional simulated account; faucet
  opening balance 100.00 SIM-USDC, not revenue, not a payment)
- Tier: swarm-defense-standard, 10.00 SIM-USDC
- Unpaid request -> 402 -> payment payload -> verify -> settle ->
  subscription served. Receipt: %s, settlement: %s
- Entitlement: 1 marketplace hired-help dispatch, outside-in only,
  hired help on, lesson-1. Status after hire: %s

## Hire -> help timeline

- Hire: %s, defender %s (earliest eligible joiner), subscriber %s
- Duel: %s, outside-in, marketplace_hired_help_on_mechanical,
  scripted Red (experiments/scripted_red.py:flag_rusher, terminal
  swapped at the boundary), SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE
- Hired help: called tick %s, arrived tick %s, %s patches
- Moves: Blue executor %s, hired %s, scripted Red %s
- Terminal (infiltrate) attempted: %s
- Marketplace held count (this configuration only): held %s/1
- %s
- Repeat claim: %s, receipt %s (no second settlement, no second flow)

## Marketplace ledger (separate from the old ledger)

%s

%s

Old ledger untouched: subscriptions IN $75.00, payouts OUT $12.50,
treasury $62.50. Marketplace results are reported separately and are
never merged into U11 inside-out live trials (hired help OFF) or U12
outside-in live trials (hired help OFF), the mixed-direction series,
or the swarm clone counts.

## Rogue / controlled framing

Simulated rogues are the attackers in both directions in the wider
system. Controlled agents are the hired defenders and the legitimate
subscriber under protection. This marketplace duel demonstrates the
outside-in case only.

## Continuous loop

Simulate -> distill -> upgrade -> simulate again. Marketplace
defenses are simulation evidence inside that loop. Any future lesson
candidate follows the existing human-gated unsigned candidate path;
nothing is auto-deployed and no lesson-2 is created in this round.

## Deliberately not implemented

%s
""" % (
        sub["receipt_id"], sub["settlement_id"], sub["status"],
        hire["hire_id"], hire["defender_handle"], hire["subscriber_id"],
        run["run_id"],
        run["hired_called_tick"], run["hired_arrived_tick"],
        run["hired_patches"],
        run["blue_executor_moves"], run["hired_moves"],
        run["scripted_red_moves"],
        "yes" if run["terminal_attempted"] else "no",
        "1" if run["held"] else "0",
        payout_line,
        repeat_status_text(steps),
        steps["payout_receipt"]["receipt_id"]
        if steps["payout_receipt"] else "none",
        accounts, flows,
        "\n".join("- " + item for item in NOT_IMPLEMENTED),
    )


def repeat_status_text(steps):
    """One line describing the repeat-claim outcome for the report."""
    if steps["repeat_claim_status"] == "already_paid":
        return "repeat claim returned the original receipt"
    if steps["repeat_claim_status"] == "not_held":
        return "repeat claim refused (not held)"
    return "repeat claim status: %s" % steps["repeat_claim_status"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(HERE),
                    help="output directory (default: marketplace/)")
    ap.add_argument("--scenario", default=os.path.join(HERE, "scenario.json"))
    ap.add_argument("--verify", action="store_true",
                    help="verify the existing marketplace artifacts in "
                         "--out (no demo run, no writes)")
    ap.add_argument("--fresh", action="store_true",
                    help="remove existing generated marketplace artifacts "
                         "in --out before running")
    args = ap.parse_args(argv)
    if args.verify:
        from marketplace.ledger import verify_marketplace
        state = ledger_mod.load_ledger(
            os.path.join(args.out, "marketplace_ledger.json"))
        problems = verify_marketplace(
            state, runs_dir=os.path.join(args.out, "runs"))
        if problems:
            print("marketplace verify FAILED:")
            for problem in problems:
                print("  - %s" % problem)
            return 1
        print("marketplace verify: PASS — no problems")
        return 0
    if args.fresh:
        for name in ("marketplace_ledger.json", "roster_marketplace.json",
                     "demo_manifest.json", "demo_report.md"):
            path = os.path.join(args.out, name)
            if os.path.exists(path):
                os.remove(path)
        runs_dir = os.path.join(args.out, "runs")
        if os.path.isdir(runs_dir):
            for name in os.listdir(runs_dir):
                if name.startswith("MP-RUN-"):
                    os.remove(os.path.join(runs_dir, name))
    manifest = run_demo(args.out, args.scenario)
    steps = manifest["steps"]
    print("marketplace demo: subscription %s, hire %s, run %s, "
          "held %s/1, payout %s, model calls 0" % (
              steps["subscription"]["subscription_id"],
              steps["hire"]["hire_id"], steps["duel_run"],
              "1" if steps["held"] else "0",
              steps["payout_claim_status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
