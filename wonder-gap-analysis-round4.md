# TESSERACT Round-4 Spec: Simulated x402 Marketplace

**Registered live model calls for this build: NONE.**  
The marketplace demo must be entirely deterministic and mechanical: 0 Red model calls, 0 Blue model calls, 0 hired-defender model calls, and no change to `credit_log.jsonl` during the demo run.

---

## 1. THE X402 PROTOCOL SHAPE

Implement **x402Version 1**, scheme **`exact`**, using the real x402 message structure and field names, but with deliberately non-routable simulated values.

### Payment flow

Every marketplace purchase follows this order:

1. **Client requests a protected resource without payment.**
   - Example local resource identifiers:
     - `marketplace/subscriptions/swarm-defense-standard`
     - `marketplace/payouts/claim/<run_id>`
   - These are local simulated resource identifiers, not live URLs.

2. **Resource server returns a 402 artifact** containing:
   - `x402Version: 1`
   - `error`: payment required message
   - `accepts`: one payment-requirements object containing:
     - `scheme: "exact"`
     - `network: "simulated"`
     - `maxAmountRequired`: atomic-unit string
     - `resource`
     - `description`
     - `mimeType: "application/json"`
     - `payTo`: simulated account, e.g. marketplace treasury
     - `maxTimeoutSeconds: 60`
     - `asset: "SIM-USDC"`
     - `extra`: name `SIM-USDC`, version `sim-1`, decimals `6`, facilitator `simulated-local`
   - A demo correlation field outside `accepts`: `demo_payment_id`

3. **Client constructs a payment payload** containing:
   - `x402Version: 1`
   - `scheme: "exact"`
   - `network: "simulated"`
   - `payload.signature`: the literal simulated marker `sim-signature-not-cryptographic`
   - `payload.authorization` containing:
     - `from`: payer simulated account
     - `to`: requirements `payTo`
     - `value`: exactly `maxAmountRequired`
     - `validAfter`: current simulated logical time
     - `validBefore`: simulated logical time + 60
     - `nonce`: unique deterministic simulated nonce for that payment

4. **Client retries the resource request with the payment payload**, represented locally as the X-PAYMENT-equivalent field.

5. **Resource server calls facilitator `verify`** before doing anything else.
   - If verification fails, the server returns a new 402 artifact.
   - No subscription, hire, payout, entitlement, or ledger flow is created.

6. **If verification succeeds, resource server calls facilitator `settle`.**
   - Settlement must succeed before the resource is served.

7. **Only after successful settlement**, the server:
   - creates the subscription, entitlement, or payout-paid record;
   - returns a 200-equivalent response;
   - includes the X-PAYMENT-RESPONSE-equivalent decoded object;
   - issues the receipt described below.

8. **If settlement fails**, the server returns 402 again. There must be:
   - no resource served;
   - no entitlement;
   - no balance change;
   - no paid flow;
   - no receipt.

### Amounts

Use atomic strings in protocol messages:

- Subscription: `10000000` = 10.00 SIM-USDC
- Payout: `2500000` = 2.50 SIM-USDC

Ledger display amounts are derived from the atomic values using 6 decimals.

### Receipt contents

Every successful settlement produces one receipt containing:

- `receipt_id`: unique, prefixed `SIM-RCPT-MP-`
- `transaction`: simulated ID prefixed `SIM-TX-MP-`
- `settlement_id`
- `demo_payment_id`
- `scheme`, `network`, `asset`
- `payer`, `payee`
- atomic amount and displayed SIM-USDC amount
- `resource`
- related subscription, hire, run, or payout ID where applicable
- simulated logical issue sequence
- `simulated: true`

### Deliberately NOT implemented

The following must be listed on the dashboard and in submission text as deliberately not implemented:

- no live HTTP call to a real facilitator;
- no contact with `x402.eleeth.com` or any live x402 rail;
- no EIP-712 or EIP-3009 cryptographic signing;
- no ECDSA verification;
- no wallet or private key;
- no RPC, gas, mempool, block confirmation, or chain transaction hash;
- no real USDC contract address;
- no mainnet or testnet network identifier;
- no recurring billing, refunds, disputes, KYC, or real account recovery.

This is honest because the demo claims the **x402 message shape**, not live settlement. The simulated `network`, `asset`, account IDs, signature marker, and transaction IDs are intentionally impossible to confuse with live payment values.

---

## 2. THE SIMULATED FACILITATOR

Create a separate marketplace package. Do not modify the engine.

### Module shape

- `marketplace/facilitator.py`
  - Defines the facilitator interface and `SimulatedFacilitator`.
- `marketplace/resource_server.py`
  - Handles 402, verify, settle, serve-after-settlement, and receipts.
- `marketplace/ledger.py`
  - Stores marketplace accounts, flows, settlements, subscriptions, hires, and payouts; provides `verify_marketplace()`.
- `marketplace/demo.py`
  - Runs the deterministic marketplace scenario.
- `marketplace/scenario.json`
  - Declares the fictional joiners, subscriber, subscription, hire, and scripted duel source.
- Generated artifacts:
  - `marketplace/roster_marketplace.json`
  - `marketplace/marketplace_ledger.json`
  - `marketplace/demo_manifest.json`
  - `marketplace/runs/<run_id>.json`

### Swappable seam

The resource server may depend only on this facilitator interface:

- `supported()` → supported x402 version, scheme, network, and asset
- `verify(payment_payload, payment_requirements)` → valid/invalid result, invalid reason if any, payer
- `settle(payment_payload, payment_requirements)` → success/failure, simulated transaction ID, network, payer, error reason if any

The demo composition code wires in `SimulatedFacilitator`. Nothing else in the marketplace may branch on whether settlement is simulated.

A future real facilitator would implement the same `verify` and `settle` boundary. Only that backend would change; roster, subscription, hire, entitlement, ledger-receipt, and dashboard code would not.

Do **not** build the real facilitator in this round.

### Simulated verification checks

The simulated facilitator must verify:

- payload is well-formed;
- `x402Version` is 1;
- scheme matches requirements;
- network is exactly `simulated`;
- asset is exactly `SIM-USDC`;
- payer account exists;
- `to` exactly matches `payTo`;
- `value` exactly equals `maxAmountRequired`;
- simulated logical time is within `validAfter`/`validBefore`;
- authorization window does not exceed 60 logical units;
- nonce has never been used;
- signature field is the approved simulated marker;
- payer has sufficient simulated balance.

### Settlement behaviour

Settlement must re-run the material checks, especially balance, expiry, amount, payee, and nonce.

Settlement is atomic:

- Either the payer/payee balances change, the nonce is consumed, the settlement journal entry is written, and a receipt can be issued;
- or none of those things happens.

Use refusal reasons such as:

- `malformed_payload`
- `scheme_mismatch`
- `network_mismatch`
- `asset_mismatch`
- `amount_mismatch`
- `payto_mismatch`
- `authorization_not_yet_valid`
- `authorization_expired`
- `nonce_reused`
- `unknown_payer`
- `insufficient_sim_balance`
- `simulated_signature_required`

A failed verification must not be followed by settlement. A failed settlement must not create a partial transfer, receipt, entitlement, or paid ledger flow. Failed attempts may be recorded only in a separate attempts list with `amount_moved: 0`.

---

## 3. ROSTER JOIN

Open joining is demonstrated through a local simulated registration flow, not a public web form.

### Required registration fields

- `handle`
- `simulated_region_label`
- `lesson_id`, which must be lesson-1 for eligibility
- `simulated_fictional: true`

Reject any registration containing real-world identity or secret fields, including real name, email, wallet, private key, credential, or payment details.

### Handle rules

Handles must:

- be 3–24 characters;
- use only lowercase letters, digits, hyphen, and underscore;
- start with a letter or digit;
- be unique case-insensitively;
- not equal or imitate the five clone IDs or callsigns;
- not use reserved actor names such as `blue`, `red`, `hired`, `marketplace-treasury`, or `admin`;
- not reuse `acme-corp` or `globex`.

### Demo joiners

Create exactly two fictional joiners:

- `harbor-fox-7`
- `velvet-owl-3`

Use simulated region labels such as “simulated test range A” and “simulated test range B”.

### Joiner record

Each roster record contains:

- `agent_id`: e.g. `MP-JOIN-001`
- `handle`
- `kind: "marketplace_joiner"`
- `origin: "open_join_simulated"`
- `simulated_region_label`
- `lesson_id: "lesson-1"`
- recipe status using “recipe pre-loaded (no weight training)”
- simulated payee account ID
- opening simulated balance: 0
- `status: "eligible"`
- logical join sequence

A joiner is not a clone. Joiners live only in `marketplace/roster_marketplace.json`.

`fleet/roster.json` must not be modified. The five clones, their IDs, callsigns, regions, and prior payout history remain exactly as they were.

---

## 4. SUBSCRIPTION FLOW

Create one new fictional simulated subscriber:

- `lumen-yard-sim`

Do not reuse acme-corp or globex for the marketplace demonstration.

### Simulated account

At subscriber creation, the facilitator creates:

- one simulated payer account;
- one recorded simulated faucet allocation of 100.00 SIM-USDC;
- opening balance 100.00 SIM-USDC.

That faucet allocation is opening simulated balance, not revenue and not a subscription payment.

### Purchase

The subscriber buys `swarm-defense-standard` for 10.00 SIM-USDC through the full flow in Section 1:

unpaid request → 402 → payment payload → verify → settle → subscription served → receipt.

### Subscription record

A successful subscription record contains:

- `subscription_id`
- `subscriber_id`
- tier ID
- amount in atomic units and displayed SIM-USDC
- `receipt_id`
- `settlement_id`
- payer and payee accounts
- simulated logical start
- simulated logical expiry, start + 500
- `status: "active"`
- entitlement:
  - marketplace hired-help dispatches allowed: 1
  - direction: outside-in only
  - engine configuration: hired help on
  - lesson: lesson-1

### Entitlement meaning

An active subscription grants only the right to request marketplace-delivered hired help for one outside-in simulated duel.

It does not guarantee a held defense, earnings, or protection outside the simulation.

### Expiry and non-payment

- If payment is not verified and settled, no subscription record is created.
- If simulated logical time passes expiry before hire dispatch, status becomes `expired` and hire is refused with `subscription_expired`.
- If the one dispatch is used, status becomes `consumed`.
- Expired or consumed subscriptions cannot start a duel.
- There is no real billing, renewal, charge, refund, or payment retry outside the simulated protocol messages.

---

## 5. HIRE → HELP BINDING

### Hire sequence

Use this exact sequence for the demo:

1. `harbor-fox-7` and `velvet-owl-3` join.
2. `lumen-yard-sim` receives its simulated account.
3. Subscriber requests the subscription resource without payment and receives 402.
4. Subscriber pays through verify and settle.
5. Subscription and entitlement are created only after settlement.
6. Subscriber requests hire.
7. Marketplace deterministically assigns the earliest joined eligible joiner: `harbor-fox-7`.
8. Marketplace creates one hire record.
9. Marketplace starts exactly one outside-in duel using:
   - the existing engine;
   - lesson-1 unchanged;
   - deterministic lesson executor unchanged;
   - `hired_help=True`;
   - a scripted Red sequence already used by an existing outside-in mechanical replay;
   - 0 model calls.
10. Engine records hired-defender actions under actor `"hired"`, as it already does.
11. After the run ends, the marketplace determines held status solely by whether a terminal move occurred.
12. If and only if the defense held, the defender may claim the payout.

Do not tune, reorder, or replace the Red sequence after seeing the outcome.

### Hire record

Each hire record contains:

- `hire_id`
- `subscription_id`
- `subscriber_id`
- `defender_agent_id`
- `defender_handle`
- direction: outside-in
- engine configuration: hired help on
- lesson-1 identifier
- executor mode: deterministic mechanical replay
- model calls: 0
- `duel_run_id`
- status: requested, dispatched, completed-held, completed-not-held, or paid
- payout receipt ID or null

### Run record

Each run record contains:

- `run_id`
- `hire_id`
- direction: outside-in
- configuration label: `marketplace_hired_help_on_mechanical`
- source identifier for the reused scripted Red sequence
- separate move counts for Blue executor, hired actor, and scripted Red
- hired-help trigger recorded by the engine
- hired-help arrival tick recorded by the engine
- terminal move attempted: yes/no
- held: true/false, where held means no terminal move occurred
- model calls by actor, all 0
- total model calls: 0

The engine’s actor label must remain `"hired"`. The marketplace hire record maps that run’s hired actor to `harbor-fox-7`; do not rewrite engine logs with the joiner’s handle.

### End-to-end proof

`demo_manifest.json` must link, by ID, every step:

join → simulated account → 402 → payment payload → verify → settle → receipt → subscription → entitlement → hire → duel run → held result → payout attempt → payout receipt if earned.

The demo proves “hire paid → help arrived → defense held → payout issued” only if every referenced artifact exists and the run actually held. If the run did not hold, the manifest must show payout not earned. That is a valid negative result, not a reason to alter the engine or script.

### Payout rule

Pay a flat **2.50 SIM-USDC** for one distinct held marketplace duel.

This mirrors the existing swarm amount because the unit is also one defense engagement and reusing the known simulated amount prevents inventing new marketplace economics.

It differs because:

- the source is the marketplace simulated treasury funded by the new subscription;
- the recipient is an open marketplace joiner, not one of the five clones;
- the configuration is hired help on;
- it is recorded only in the marketplace ledger;
- it is not part of the earlier swarm payout history.

No-double-pay rule:

- payout identity is the pair (`duel_run_id`, defender account);
- a repeated claim returns the original receipt;
- no second settlement or flow is created;
- a not-held run earns 0;
- only the defender named in the hire record can receive that run’s payout.

The payout leg uses the same facilitator verify/settle envelope and receipt format, with the marketplace treasury as payer and the defender as payee. It must be labelled as the treasury-funded payout leg, not as the defender buying a resource.

### Separation from U11/U12

Marketplace runs are a different configuration: **hired help ON, mechanical replay**.

They must never be added to:

- U11 inside-out live executor trials, hired help OFF;
- U12 outside-in live executor trials, hired help OFF;
- mixed-direction series counts;
- swarm clone counts;
- any cross-direction or cross-tier total.

Marketplace results may be reported only as their own raw count, for example “held x/1” copied from the generated marketplace manifest after the run. Submission prose must not state a marketplace held number before that artifact exists.

---

## 6. LEDGER VERSIONING

### Decision: create a separate marketplace ledger

Use:

- `marketplace/marketplace_ledger.json`
- schema: `marketplace-ledger/1`

Do not extend or rewrite `payments/moneyflow.json` or `payments/ledger.json`.

Reasons:

- the recorded $75.00 subscription history remains untouched;
- the recorded $12.50 clone payout history remains untouched;
- the $62.50 treasury result remains reconcilable by the existing rule;
- marketplace activity can be regenerated or removed without endangering prior history;
- judges can audit simulated marketplace conservation separately.

### Marketplace ledger contents

The ledger contains separate collections for:

- simulated accounts and opening balances;
- facilitator settlement journal;
- failed attempts with zero amount moved;
- paid flows;
- subscriptions;
- hires;
- payout claims.

Paid flow records contain:

- `flow_id`
- kind: `subscription` or `payout`
- atomic amount and displayed amount
- asset SIM-USDC
- payer and payee
- receipt ID
- settlement ID
- related subscription, hire, and run IDs as applicable
- logical sequence

### Reconciliation rule

`verify_marketplace()` must confirm:

1. Every paid flow has one unique `SIM-RCPT-MP-` receipt.
2. No marketplace receipt ID appears in the old ledger.
3. Every subscription flow follows a successful settlement.
4. Every payout flow references a completed hire and a held run.
5. Every payout amount is exactly 2.50 SIM-USDC.
6. No `duel_run_id` is paid twice.
7. Marketplace treasury never goes negative in flow order.
8. For every account: ending balance equals opening balance plus inflows minus outflows.
9. Total SIM-USDC across marketplace accounts equals total recorded simulated opening allocations; transfers create and destroy nothing.
10. Failed attempts moved 0 and produced no receipt or paid flow.

The existing `verify()` must continue to run against the old files and keep passing. `verify_all` must report old-ledger verification and marketplace verification as separate steps.

---

## 7. DASHBOARD + SUBMISSION TEXT

### `/marketplace` page

Add a read-only `/marketplace` route. It must show:

1. **SIMULATED banner**
   - fake money;
   - real x402 protocol shape;
   - local simulated facilitator;
   - no live rail touched.

2. **Deterministic label**
   - “Deterministic mechanical replay — 0 model calls” wherever the demo or outcome appears.

3. **Protocol section**
   - unpaid request;
   - 402;
   - payment payload;
   - verify;
   - settle;
   - serve only after settlement;
   - receipt;
   - scheme `exact`, x402Version 1, network `simulated`, asset SIM-USDC;
   - the deliberately-not-implemented list from Section 1.

4. **Open roster section**
   - the two marketplace joiners;
   - joiner records and simulated balances;
   - a separate note that the five clones remain in `/fleet` and are not marketplace joiners.

5. **Subscription section**
   - only `lumen-yard-sim`;
   - tier, simulated amount, receipt, status, entitlement, expiry.

6. **Hire → help timeline**
   - subscription receipt;
   - hire ID;
   - assigned joiner;
   - engine trigger and arrival tick;
   - separate Blue, hired, and scripted-Red move counts;
   - terminal attempted yes/no;
   - raw marketplace held count only for that configuration;
   - payout status and receipt if earned.

7. **Marketplace ledger section**
   - subscription and payout flows;
   - simulated account balances;
   - `verify_marketplace()` result;
   - separate statement that the old ledger remains at subscriptions IN $75.00, payouts OUT $12.50, treasury $62.50.

8. **Rogue/controlled framing**
   - simulated rogues are the attackers in both directions in the wider system;
   - controlled agents are the hired defenders and the legitimate subscriber under protection;
   - this marketplace duel demonstrates the outside-in case only.

9. **Continuous-loop section**
   - simulate → distill → upgrade → simulate again;
   - marketplace defenses are simulation evidence inside that loop;
   - any future lesson candidate follows the existing human-gated unsigned candidate path;
   - nothing is auto-deployed and no lesson-2 is created in this round.

The page must not contain a wallet button, checkout, live signup form, real payment instruction, reliability percentage, pooled held total, or claim that joining is open on a live service.

### Submission-text replacement for stale claim (a)

Replace:

> “the real USDC x402 marketplace is the post-hackathon business layer, not part of this build”

with:

> “The marketplace is in this build in simulated form: hiring and subscription flows use the x402 protocol shape — 402 Payment Required, payment payload, facilitator verify, facilitator settle, and receipt — through a local simulated facilitator settling SIM-USDC. No real USDC was used, no mainnet or live x402 rail was touched, and no real money moved. A production version would swap only the simulated settlement backend for a real facilitator.”

### Submission-text replacement for stale claim (b)

Remove ancestor-diff language asserting that competitors lack “a hired-defender marketplace or pay-per-defense.” That comparative claim is no longer needed and is not verified here.

Replace it with an own-build statement:

> “TESSERACT demonstrates, in simulation, a hired-defender marketplace and pay-per-held-defense flow using the x402 message shape. It does not operate a live marketplace, accept real payments, or enrol real defenders.”

Search all submission files for “post-hackathon business layer”, “not part of this build”, and competitor-lack phrasing about marketplaces. No occurrence may remain.

### Required updates by file

- `submission/README.md`
  - Add the simulated marketplace section, open-join flow, subscription, hire→help proof, separate ledger, and deterministic 0-call label.
- `submission/SUBMISSION.md`
  - Add protocol shape, swappable facilitator seam, reconciliation rule, configuration separation, and not-implemented list.
- `submission/VIDEO-SCRIPT.md`
  - Do not add a marketplace scene and do not imply a re-cut.
  - Add a text note stating the video shows inside-out only and the marketplace is shown through the dashboard/demo artifacts, not in the video.
- `STATUS.md`
  - Add a Round-4 entry recording files changed, 0 model calls, old ledger verification, marketplace verification, raw marketplace outcome copied from its manifest, dashboard route checks, and claims-lint result. Leave result fields to be filled from actual builder output.

All three submission files must plainly state:

- video shows inside-out only;
- all marketplace money is simulated;
- no real money moved;
- no live x402 rail was touched.

The following sentence must remain verbatim in all three submission files:

“Round three proved the lesson can work; the confirmation proved a single agent doesn't always apply it — which is why the lesson is distilled into rules the whole fleet loads.”

---

## 8. TESTS + FALSIFIER

### Unit tests

Facilitator:

- accepts one well-formed simulated payment;
- rejects each invalid case in Section 2 with the correct reason;
- rejects nonce replay;
- rejects expired authorization;
- rejects insufficient simulated balance;
- settlement after a balance change fails atomically;
- failed settlement changes no balance and consumes no nonce unless settlement succeeded;
- simulated transaction and receipt IDs have simulated prefixes.

Roster:

- accepts the two demo joiners;
- rejects duplicate handles;
- rejects clone IDs and callsigns;
- rejects reserved actor names;
- rejects real identity, wallet, and credential fields;
- joining does not alter `fleet/roster.json`.

Subscription and hire:

- unpaid request returns 402 and creates no subscription;
- settled subscription creates exactly one entitlement;
- expired subscription refuses hire;
- consumed subscription refuses a second hire;
- non-subscriber refuses hire;
- inside-out marketplace hire is refused;
- hire assigns the earliest eligible joiner deterministically.

Payout:

- held run pays exactly 2.50 SIM-USDC once;
- repeated claim returns the original receipt;
- not-held run pays 0;
- wrong defender cannot claim;
- payout cannot precede a finalized run record.

Ledger:

- `verify_marketplace()` passes on the generated demo ledger;
- duplicate receipt fails;
- duplicate payout fails;
- unexplained balance change fails;
- negative treasury step fails;
- old `verify()` still passes;
- old subscription, payout, and treasury baselines remain $75.00, $12.50, and $62.50.

Seam:

- a local test-double facilitator implementing the same interface can return success and failure, and the resource server serves only on settlement success. This proves the seam without any network or live call.

### Integration tests

- Full deterministic demo:
  join → subscribe through 402/verify/settle → hire → outside-in duel → outcome → conditional payout → marketplace verification.
- Failed-payment demo:
  invalid payment → 402 again → no subscription → no hire → no duel → no paid flow.
- Re-run safety:
  running the demo again must not duplicate paid flows, receipts, joiners, subscriptions, hires, or payouts in the same ledger.
- Determinism:
  a fresh marketplace run reproduces the same IDs, amounts, scripted sequence, actor counts, and outcome.
- Dashboard:
  `/marketplace` and all pre-existing routes return 200.
- Segregation:
  marketplace run IDs do not appear in U11/U12 records, and marketplace held counts are not included in any live-trial, mixed-series, or swarm total.
- Model budget:
  marketplace demo makes 0 model calls and does not append to `credit_log.jsonl`.

### Claims lint

Extend claims lint to scan dashboard text, submission text, STATUS.md, and generated marketplace reports for:

- the banned P-word;
- held results expressed as percentages;
- pooled held totals;
- claims that Blue reliably learned or now wins;
- claims that the executor learns or adapts;
- model-weight evolution claims;
- affirmative real-money, real-USDC, mainnet, live-marketplace, or real-defender claims;
- presentation of marketplace holds as U11/U12 results.

Approved negated statements, such as “no real money moved”, are allowed only in their approved plain form.

Add the marketplace checks to `verify_all` as new final steps without removing or reordering the existing verification steps.

### Falsifier

The marketplace demo is dishonest if any of the following is found:

- a network call to a live facilitator or live x402 rail;
- a real chain identifier, wallet, private key, USDC contract, or chain transaction hash;
- any model call in the demo;
- any change to the engine, lesson-1, deterministic executor, fleet roster, old ledger, or U11/U12 records;
- a marketplace hold merged into another held count;
- an entitlement served before settlement;
- settlement after failed verification;
- a payout for a not-held run;
- the same run paid twice;
- a missing or duplicate receipt;
- an unexplained simulated balance;
- a joiner presented as a real person or as one of the five clones;
- the dashboard omitting SIMULATED or deterministic-mechanical labels.

If any falsifier check fails, the builder must stop, preserve the failing artifact, and report the exact check to the parent. Do not hide the failure in prose, tune the attack, rebalance the engine, force a held result, or rewrite the old ledger. Fixes are allowed only inside the marketplace, ledger, dashboard, tests, or submission text. If a fix would require changing the engine, lesson, or executor, the build stops as a NO-GO.

A not-held marketplace run is not itself dishonesty; claiming or paying for a hold that did not occur is.

---

## 9. CUTS

### Cut first if scope or honesty is threatened

- interactive dashboard registration or checkout;
- local HTTP transport for the facilitator;
- cryptographic wallet signing;
- a second subscription tier;
- bidding, auctions, ratings, reputation, or dynamic pricing;
- a second marketplace duel;
- more than one subscriber;
- inside-out marketplace hiring;
- a real-facilitator adapter;
- testnet of any kind;
- automatic lesson-candidate creation from the marketplace run;
- any live model call.

### Keep even under pressure

- one simulated facilitator behind the stated seam;
- one `exact`-scheme x402 flow;
- two fictional joiners;
- one fictional subscriber;
- one subscription;
- one hire;
- one outside-in deterministic duel;
- conditional 2.50 SIM-USDC payout;
- separate marketplace ledger;
- old-ledger verification;
- `/marketplace`;
- full claims lint;
- submission-text corrections.

---

## 10. VERDICT

**CONDITIONAL GO — proceed only with 0 model calls, a separate marketplace ledger, outside-in hired-help configuration kept strictly apart from U11/U12, and settlement-before-service enforced, because the marketplace must demonstrate the real x402 shape without ever implying live money or live protection.**