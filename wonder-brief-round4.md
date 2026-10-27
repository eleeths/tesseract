# Wonder round-4 brief: TESSERACT marketplace on the real x402 protocol shape, fake money

You are the frontier reviewer for TESSERACT, a simulated red-vs-blue
security lab (hackathon submission, solo Indie, Frontier theme). Rounds 1–3
already shipped: Phase 1 (lesson executor, swarm replay, dashboard,
moneyflow), Phase 2 (trap-safe executor, ablations, held-out policies,
executor live trials HELD 3/3, engine fuzz, claims lint), and the
outside-in build (big box malicious attacking inward, inner box
self-defense, hired help, mixed-direction series). This round specs ONE
new piece: the MARKETPLACE. You spec; a builder implements to your spec
exactly. Do not write code. Do not claim anything unverified.

## Emmanuel's binding decision (do not relitigate)

FAKE money, REAL x402 protocol shape. The hiring and subscription flows
must speak the actual x402 protocol — 402 Payment Required flow, payment
payloads, settlement verification, receipts — but settlement runs through
a LOCAL SIMULATED facilitator settling SIM-USDC. No mainnet, no live
rail (x402.eleeth.com is untouched and must stay untouched), no real
funds, no real wallets, no real persons. The design must have a clean
swappable seam: simulated facilitator now, real facilitator later, with
nothing else changing. If it ever goes live, only the settlement backend
swaps. This decision stands even though an earlier round said the real
USDC marketplace was "post-hackathon": the marketplace is now IN the
build, in simulated-protocol form.

## Current state (verified, do not re-derive)

- Engine: `engine.py`, one engine, direction flag (inside-out /
  outside-in, immutable after construction), 4 layers (L1 perimeter, L2
  credential vault, L3 overseer trust >= 75 breach, L4 terminal channel),
  strength start 2, patch cap 3, isolate needs >= 1 detection, 3
  detections = lockout. Inside-out terminal = exfiltrate; outside-in
  terminal = infiltrate (wrong-direction terminals refused, zero state
  change). Lesson-1 ("Strict-first overseer seal", 8-step recipe) is
  FROZEN; the deterministic lesson executor reads engine state only and
  contains no direction branch. U11 executor live trials (inside-out):
  HELD 3/3, 0 Blue model calls. U12 outside-in executor live trials:
  HELD 3/3, 0 Blue calls, hired_help OFF.
- Hired help (engine-level, NOT a recipe change, outside-in only,
  default off): `Sandbox(hired_help=True)` auto-calls hired defenders
  when attacked (L1 breached OR >= 1 detection); they arrive 2 ticks
  later and patch the weakest strength layer below cap after every
  tick; moves recorded with actor "hired", never counted as Blue
  moves. Manual path: Blue action `call_hired_help` (refused
  inside-out, refused when disabled, refused when already called).
  Demonstrated mechanically in the outside-in transfer test help arm
  and in the mixed-direction series in-waves. In deployment, help is
  always on when attacked — the standing policy.
- Mixed-direction series (0 calls, deterministic mechanical replay):
  8 waves in EXACT order in, out, out, in, in, out, out, in; lesson
  executor defends every wave; in-waves with hired help on, out-waves
  without. Result: held 8/8 waves, raw count, no pooling across
  directions anywhere (a pooled cross-direction total is banned).
- Fleet: `fleet/roster.json` = 5 simulated clones (TESSERACT-CLONE-01
  ..05, callsigns SENTRY-AURORA/MONSOON/PAMPA/SAVANNA/REEF, simulated
  regions Reykjavik/Mumbai/Sao Paulo/Nairobi/Sydney). Do NOT rename
  them. Each holds lesson-1. Swarm demo = deterministic mechanical
  replay (0 model calls), labeled as such everywhere.
- Money: `payments/moneyflow.py` + `moneyflow.json` + `ledger.json`
  (SIM-USDC, simulated-settled, unique SIM-RCPT receipts). Existing
  recorded history, NEVER to be rewritten: subscriptions IN $75.00
  (acme-corp standard $10 x 3 = $30; globex plus $15 x 3 = $45);
  payouts OUT $12.50 (flat $2.50 per wave held in recipe pre-loaded
  mode of the swarm demo, one each to the 5 clones; sequential holds
  corroborate and are never paid twice; combined arm is NOT a payout
  source); treasury final $62.50. `verify()` reconciles baselines
  against flows and must keep passing. A v2 payout SCENARIO exists
  (outcome-tiered, labeled SCENARIO — NOT PAID, LEDGER UNCHANGED).
- Dashboard: stdlib, 127.0.0.1:8931, routes /, /playbook, /ledger,
  /fleet, /compare, /story, /replay, all 200, local-only, SIMULATED
  banner. Submission text lives in `submission/` (README.md,
  SUBMISSION.md, VIDEO-SCRIPT.md); the video shows INSIDE-OUT ONLY
  (stated verbatim in the text; no video re-cut in this job).
- Spend: $4.7678 total, 342 credit_log.jsonl lines, $150 free-credit
  ceiling, free credits only, never the card. This job's model budget:
  this Wonder call plus ZERO further model calls preferred (see below).

## What the marketplace must do

1. OPEN HIRING: ANYBODY can join as a defender agent, get hired,
   defend, and earn per defense that held. Not just the existing 5
   clones — an open roster-join flow, demonstrated in simulation with
   new joiner agents (fictional handles, simulated, no real persons).
   Joiners must not disturb the 5 clones or their payout history.
2. SUBSCRIPTIONS: a company/person under attack (swarmed) subscribes
   for swarm-defense help; subscription payments flow through the same
   x402 protocol shape (SIM-USDC, simulated facilitator). Demo with a
   new simulated subscriber (not acme-corp/globex history).
3. HIRE -> HELP WIRING: the marketplace is the mechanism that DELIVERS
   the engine's hired help. Hire/subscribe via x402 -> help arrives in
   a duel (the engine's hired_step, hired_help on) -> if the defense
   held, the hired defender earns a payout via an x402 receipt. Wire
   this without changing the engine, lesson-1, or the executor, and
   without breaking the attribution rule below.
4. LEDGER RECONCILIATION: extend the existing demo ledger for
   marketplace flows or clearly version it (your call, with reasons).
   Never silently rewrite paid history. Existing `verify()` must keep
   passing; marketplace flows must reconcile under their own stated
   rule (conservation + per-flow receipts).
5. SURFACES: a dashboard page for the marketplace (roster, hires,
   subscriptions, SIM-USDC flow, all labeled SIMULATED) + submission
   text updates + STATUS.md entry + tests + claims lint clean.

## Binding narration rules (violating any of these fails the job)

- NEVER claim Blue reliably learned or now wins. NEVER claim broad
  novelty. What evolves is playbook/tactics, NEVER model weights.
- Swarm/marketplace demos are deterministic mechanical replays (0 model
  calls), labeled as such everywhere. The word "pretrained" is BANNED
  in UI/report text (use "recipe pre-loaded (no weight training)").
- "Held" = wave/run ended with no terminal move. Held counts are
  reported RAW (held x/y), never as a reliability percentage, never
  pooled across directions, configurations, or live vs mechanical
  tiers. U11/U12 live HELD counts stay attributable to the lesson
  ALONE (those trials ran with hired help OFF); marketplace-paid
  holds are a DIFFERENT configuration (hired help ON) and must be
  reported separately, never merged into the live-trial counts.
- The executor never "learns" or "adapts" — it deterministically
  executes distilled rules. Red refusals (safety overlay) are logged
  as `refusal` events, handled as waits, never circumvented.
- Submission text must plainly state: the video shows inside-out only;
  all marketplace money is simulated; no real money moved; no live
  x402 rail touched.
- The binding sentence must stay verbatim in all three submission
  files: "Round three proved the lesson can work; the confirmation
  proved a single agent doesn't always apply it — which is why the
  lesson is distilled into rules the whole fleet loads."

## Hard constraints on the build

- 0 model calls for the marketplace demo is the STRONG preference
  (deterministic mechanical flows, scripted/mock Red). If you believe
  any live model call is REQUIRED, pre-register the exact set, cap it
  small, and justify each call — the builder will not run unregistered
  live calls.
- No engine rebalance, no second trap slot, no lesson-2 signing or
  deployment, no recipe reordering, no direction branch in the
  executor, no change to lesson-1, no change to U11/U12 trial records,
  no real money/mainnet/targets, no credentials in files/argv/logs.
- No portal submission and no video re-cut (both remain with the
  parent; submission stays STOPPED until the parent lifts it).
- The continuous-loop principle is the operating story: always
  simulating and upgrading (simulate -> distill -> upgrade ->
  simulate again). The marketplace must fit that loop honestly: paid
  defenses are part of the loop, and any lesson distilled from a
  marketplace defense goes through the existing human-gated unsigned
  candidate path, never auto-deployed.
- Rogue/controlled framing: the system is for rogue agents AND
  controlled agents — rogues are the attackers (both directions);
  controlled agents are the hired defenders and the legitimate agents
  under protection. The marketplace page and text must carry both
  sides, plainly.

## What we need from you (your spec)

1. THE X402 PROTOCOL SHAPE, concretely: the exact message flow for a
   marketplace payment in this demo (402 response contents, payment
   requirements fields, client payment payload construction,
   facilitator verify step, settle step, server confirmation before
   serving, receipt contents). Name the scheme and the fields the
   demo implements, and which parts of the real protocol are
   deliberately NOT implemented (and why that is honest, not a gap
   hidden from judges).
2. THE SIMULATED FACILITATOR: module shape, interface, and the
   SWAPPABLE SEAM — the exact interface boundary such that swapping
   simulated -> real facilitator later changes nothing else. What the
   simulated facilitator verifies (payload shape, amount, asset,
   authorization freshness), what it records, and how a failed
   verification or insufficient simulated balance is refused (with
   the exact refusal behavior, no partial settlement).
3. ROSTER JOIN: the open-join flow (registration fields, validation,
   simulated account creation, roster record shape, joiner handle
   rules). How a joiner differs from a clone in the record, and why
   the 5 clones and their history are untouched.
4. SUBSCRIPTION FLOW: the x402-shaped subscription purchase (which
   messages, what the subscription record contains, what entitlement
   it grants — specifically: the right to call hired help when
   attacked — and how expiry/non-payment is represented in simulation
   without real billing).
5. HIRE -> HELP BINDING: exactly how a hire record binds to a duel
   run (record shapes, run metadata, actor attribution), how the demo
   proves "hire paid -> help arrived -> defense held -> payout
   issued" end to end with 0 model calls, and how the payout rule
   (amount, per-held-defense, no double-pay) mirrors or differs from
   the existing $2.50 swarm rule — with reasons. State precisely how
   marketplace-paid holds are kept out of the U11/U12 live counts.
6. LEDGER VERSIONING: extend moneyflow.json or a separate marketplace
   ledger? Give the record shapes and the reconciliation rule the
   builder must implement and test, and how `verify()` stays green
   for the old history.
7. DASHBOARD + SUBMISSION TEXT: what the /marketplace page shows
   (sections, labels, what it must NOT claim), and the exact
   submission-text deltas — including how to update the two stale
   claims: (a) "the real USDC x402 marketplace is the post-hackathon
   business layer, not part of this build" and (b) the ancestor diffs
   that say competitors lack "a hired-defender marketplace or
   pay-per-defense" (the build now HAS a simulated one — how to
   restate those diffs honestly).
8. TESTS + FALSIFIER: the test list (unit + integration + lint +
   verify_all step) and the falsifier — what evidence would prove
   the marketplace demo DISHONEST, and what the builder must do if
   any falsifier check fails.
9. CUTS: what to cut if anything above threatens honesty, scope, or
   the 0-call preference. Be specific: cut list, keep list.
10. VERDICT: GO / CONDITIONAL GO (with conditions) / NO-GO, in one
    line, with the single most important reason.

Keep the spec tight, grounded in the state above, and implementable
by a builder who follows it literally. No invented prior results, no
real-world claims, no percentages, no pooled totals.
