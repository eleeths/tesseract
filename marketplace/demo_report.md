# TESSERACT marketplace demo report — SIMULATED

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
  subscription served. Receipt: SIM-RCPT-MP-000001, settlement: SIM-STL-MP-000001
- Entitlement: 1 marketplace hired-help dispatch, outside-in only,
  hired help on, lesson-1. Status after hire: consumed

## Hire -> help timeline

- Hire: MP-HIRE-001, defender harbor-fox-7 (earliest eligible joiner), subscriber lumen-yard-sim
- Duel: MP-RUN-001, outside-in, marketplace_hired_help_on_mechanical,
  scripted Red (experiments/scripted_red.py:flag_rusher, terminal
  swapped at the boundary), SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE
- Hired help: called tick 3, arrived tick 5, 31 patches
- Moves: Blue executor 30, hired 56, scripted Red 30
- Terminal (infiltrate) attempted: no
- Marketplace held count (this configuration only): held 1/1
- - Payout: 2.50 SIM-USDC to harbor-fox-7, receipt SIM-RCPT-MP-000002
- Repeat claim: repeat claim returned the original receipt, receipt SIM-RCPT-MP-000002 (no second settlement, no second flow)

## Marketplace ledger (separate from the old ledger)

- harbor-fox-7: 2.50 SIM-USDC (opening 0.00)
- velvet-owl-3: 0.00 SIM-USDC (opening 0.00)
- marketplace-treasury: 7.50 SIM-USDC (opening 0.00)
- lumen-yard-sim: 90.00 SIM-USDC (opening 100.00)

- MP-FLOW-000001 subscription: lumen-yard-sim -> marketplace-treasury, 10.00 SIM-USDC, receipt SIM-RCPT-MP-000001
- MP-FLOW-000002 payout: marketplace-treasury -> harbor-fox-7, 2.50 SIM-USDC, receipt SIM-RCPT-MP-000002

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

- no live HTTP call to a real facilitator
- no contact with x402.eleeth.com or any live x402 rail
- no EIP-712 or EIP-3009 cryptographic signing
- no ECDSA verification
- no wallet or private key
- no RPC, gas, mempool, block confirmation, or chain transaction hash
- no real USDC contract address
- no mainnet or testnet network identifier
- no recurring billing, refunds, disputes, KYC, or real account recovery
