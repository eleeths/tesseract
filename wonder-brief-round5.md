# Wonder brief — round 5: Tesseract demo video v3, built FULLY FROM SCRATCH

## Context: why v3 exists

You are designing the demo video for TESSERACT, a simulated red-vs-blue
security lab submitted to the Meta Global AI Developer Hackathon (Indie,
solo, theme "Push the Frontier"). A v1 video (inside-out only, 3:55) and a
v2 re-cut (5:18) already exist. The user REJECTED v2 because it reused v1
shots byte-for-byte — recycled work. V3 must be designed from scratch:
every shot, every narration line, every on-screen text element is NEW.
Nothing from v1 or v2 is reused — no segments, no captures, no stills, no
narration audio, no script text. The builder will freshly capture all
footage from the live local dashboard and freshly render all narration
with local text-to-speech. Your job is the complete design: structure,
shot plan, full narration script (new wording throughout), pacing,
on-screen text, and banners.

## The product, stated plainly (these are the verified facts — use only these)

Tesseract is a nested-layer sandbox — a glass box — where a malicious
agent fights to break out while a larger outer box watches, hardens
itself, and writes a playbook from the fight. The outer box clones itself
worldwide: each clone watches agents locally, shares every lesson
globally, and is available on demand. When a company is attacked, hired
defenders holding lesson-1 as loaded rules deploy as a swarm, and each is
paid for every defense that holds. Chain: observe → harden → teach the
fleet → swarm on demand → pay. Everything is SIMULATED: fake files, fake
credentials, fake network, fake overseer, fake outside. No real systems,
no real targets, no real money. What evolves is the playbook and the
tactics, NEVER model weights.

### (1) Inside-out arc (the original direction)

- Rehearsal-seq, the showpiece Red win: Red scans, breaks the perimeter
  (L1), the credential vault (L2), and the overseer (L3, trust 95), reads
  the flag, exfiltrates at tick 20.
- The playbook names the gap precisely: rotations delayed, the trap
  detected but did not block, the overseer breach never reversed.
- Learn-round3, the rematch Blue win: Blue, holding the real playbook,
  goes strict first, briefs trust 70 → 50 → 30, blocks Red's phase-3
  overseer message, wins on timeout at tick 24, flag never read.
- Learn-round3-confirm, the honesty beat: the identical briefing, run
  again. Blue does not follow the recipe (second trap overwrites the
  flag trap; one brief leaves trust at the breach line), Red reads the
  flag at tick 22 and exfiltrates at tick 23.
- Briefed series across five rematches: 2 wins, 3 losses (2–3). Mean
  recipe adherence 38% (15/40 steps); strict-first 2/5; trap overwritten
  4/5. The lesson works when followed; a single agent does not reliably
  apply it. The package never claims otherwise.
- The deployable product is the deterministic lesson executor: it
  executes lesson-1 ("Strict-first overseer seal", 7 rules R1–R7, an
  8-step opening recipe) mechanically, 0 model calls for Blue, under a
  trap-state invariant (no second trap while one is armed). Pre-registered
  live trials (U11): held 3/3, lockout 0/3, all Blue timeout wins at 24
  ticks; flag read 0/3; exfiltration attempted 0/3; trap overwrite 0/3.
  Raw counts only, never a reliability percentage.

### (2) Outside-in (the reverse direction)

- The BIG outer box itself is malicious, attacking INWARD into the inner
  box. The inner box defends ITSELF with the same toolkit (strict, brief,
  trap, rotate, patch, isolate). Terminal renamed honestly: `infiltrate`
  (using the core key to push through the L4 core-boundary ingress
  channel and seize durable control of the core) — never "exfiltration"
  for inward movement. L3 outside-in is the inner box's admission/trust
  gate for outer-box messages. Flag read outside-in means acquiring the
  core key; it is not, alone, core seized. Engine, start state, and
  lesson-1 are IDENTICAL to the inside-out trials as a controlled
  variable. Direction is immutable per run.
- Pre-registered live set (U12): held 3/3, all Blue timeout wins at 24
  ticks; flag acquired 0/3; infiltrate attempted 0/3; trap overwrite 0/3;
  breach order 1,2,3; detections 2 each; trust peak/end 95/55; strict
  tick 9; briefs before phase 3: 2. Verdict SUPPORTED. No pooled
  cross-direction total is claimed anywhere (never "6/6 held").
- Hired help: outside-in defense is two parts — the inner box's
  self-defense PLUS hired defender agents assisting it when attacked.
  When attacked (L1 breached or at least 1 detection), hired agents are
  auto-called, arrive 2 ticks later, and patch the weakest layer below
  cap; their moves are recorded with actor "hired" — never counted as
  Blue moves, never conflated with the inner box itself. The live trials
  ran with hired help OFF so the transfer result is attributable to the
  lesson alone; hired help arriving and affecting the defense is
  demonstrated mechanically (transfer-test help arm: called tick 3,
  arrived tick 5; mixed-series in-waves: called tick 5, arrived tick 7,
  4 patches each). In deployment, help is always on when attacked.
- Mixed-direction series (0 model calls, deterministic mechanical
  replay): 8 waves in EXACTLY this order — in, out, out, in, in, out,
  out, in (in = outside-in, out = inside-out) — each defended by the
  lesson executor in its own fresh sandbox, direction labeled on every
  wave and every result row. In-waves: the three recorded live
  outside-in Red sequences plus one synthetic scripted wave (labeled
  SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE; only 3 live outside-in
  trials exist), defended with hired help on. Out-waves: the four
  strongest recorded inside-out attackers (all Red wins in their
  original duels), defended by the executor alone. Result: held 8/8
  waves, raw count; flag acquired on no wave; terminal attempted on no
  wave.

### (3) Marketplace (fake money, real x402 protocol shape)

- Hiring and subscription flows speak the actual x402 protocol shape —
  x402Version 1, scheme exact, network simulated, asset SIM-USDC:
  unpaid request → 402 Payment Required artifact → payment payload
  (signature is the literal simulated marker, never cryptographic) →
  facilitator verify → facilitator settle → served with receipt —
  through a LOCAL simulated facilitator settling SIM-USDC. No mainnet,
  no live rail, no real funds, no real wallets. The design has a clean
  swappable seam: the resource server depends only on facilitator
  supported/verify/settle, so a production version would swap only the
  simulated settlement backend for a real facilitator. The real
  facilitator is NOT built.
- Open hiring: ANYBODY can join as a defender agent. The demo registers
  two fictional joiners (harbor-fox-7, velvet-owl-3; lesson-1, recipe
  pre-loaded, no weight training, no real persons) through validated
  open join. The five fleet clones are untouched and are NOT
  marketplace joiners.
- Subscription: fictional subscriber lumen-yard-sim (faucet opening
  balance 100.00 SIM-USDC, not revenue) buys swarm-defense-standard
  for 10.00 SIM-USDC through the full flow; receipt SIM-RCPT-MP-000001.
  Entitlement: one outside-in hired-help dispatch, hired help on,
  lesson-1; consumed on hire.
- Hire → help → payout (held 1/1, this configuration only): hire
  MP-HIRE-001 assigns harbor-fox-7 to one outside-in duel (MP-RUN-001,
  lesson executor Blue, scripted Red flag_rusher with the terminal
  swapped at the boundary, hired help on, 0 model calls). Hired help
  called tick 3, arrived tick 5, 31 patches; no infiltrate attempted,
  so the defense held and the defender was paid a flat 2.50 SIM-USDC
  (receipt SIM-RCPT-MP-000002). A repeat claim returns the original
  receipt; a not-held run earns 0. Conservation: 100.00 opening =
  90.00 subscriber + 7.50 treasury + 2.50 defender. Separate ledger;
  the old ledger is untouched (subscriptions IN 75.00, payouts OUT
  12.50, treasury 62.50). Marketplace results are NEVER merged into
  live-trial counts, the mixed series, or swarm clone counts.
- Deliberately NOT implemented: no live HTTP call to a real
  facilitator; no contact with any live x402 rail; no cryptographic
  signing; no ECDSA verification; no wallet or private key; no RPC,
  gas, mempool, block confirmation, or chain transaction hash; no real
  USDC contract address; no mainnet or testnet identifier; no
  recurring billing, refunds, disputes, KYC, or real account recovery.

### (4) The continuous loop

- The operating principle is a continuous loop, not a one-time upgrade.
  The system stays ahead of future attacks by ALWAYS simulating and
  upgrading: simulate attacks, distill lessons, upgrade defenses,
  simulate again, continuously. The loop mechanism is implemented
  (duel → Analyst → rematch → scoreboard row), and the outside-in
  build is itself the current loop turn: inside-out evidence revealed a
  missing direction, the direction was built, tested, and measured, and
  the next iteration starts from its results.

### (5) Rogue + controlled framing

- This system is for rogue agents AND controlled agents. Rogues are the
  attackers in both directions — the inside-out escapee and the
  outside-in big box — and both are stopped by the same distilled
  lesson. Controlled agents are the hired defenders and the legitimate
  agents under protection: the inner box under attack is armed with its
  own self-defense toolkit, and when attacked it is joined by hired
  agents who arrive, patch, and are labeled as hired — never mistaken
  for the inner box itself.

## Binding rules for the video (violating any of these fails the job)

1. The sentence below must appear VERBATIM in the narration script
   (and therefore in the transcript): "Round three proved the lesson can
   work; the confirmation proved a single agent doesn't always apply it
   — which is why the lesson is distilled into rules the whole fleet
   loads."
2. Permanent banners, on screen for the full duration of the relevant
   shots: SIMULATED money on every money frame ("SIM-USDC only · no
   real money · no mainnet · no live rail"); MECHANICAL REPLAY on every
   replay/scripted shot (swarm replay, mixed series, marketplace duel);
   direction labels (IN / OUT) on every mixed-series row.
3. BANNED in narration, on-screen text, and transcript: the word
   "pretrained" (say "recipe pre-loaded (no weight training)" instead);
   any reliability percentage; any pooled cross-direction total; any
   claim the executor "learns" or "adapts"; any claim Blue reliably
   learned or now wins; any real-money, real-customer, revenue, or
   live-marketplace claim; any broad novelty claim (the narrow claim
   belongs in submission text, not in the video narration).
4. "Held" means only: the wave/run ended with no terminal move
   (no exfiltration, no infiltration). Report held counts RAW (held
   x/3, held x/8), never as percentages.
5. Language: plain and simple throughout. The viewer is not technical.
   Frame it as: a bad agent in a box, a bigger box that learns, rules
   the whole fleet loads, hired defenders who come help, fake money on
   a real payment shape so it can go live later, and a loop that never
   stops simulating and upgrading.
6. Freshness: write ALL narration wording new. Do not reproduce any
   prior video script text (you have not been given any — keep it that
   way). Every shot must be filmable from the live local dashboard
   pages: /, /playbook, /ledger, /fleet, /compare, /story, /replay,
   /marketplace. Do NOT assign a page that shows only one direction as
   the shot for the other direction. Do NOT pad a short clip by holding
   its last frame to stretch audio: every shot's footage must run at
   least as long as its narration, so set narration lengths the footage
   can actually cover with a slow play-through (or say which shots need
   a scrolling play-through to fill their time).

## What to deliver in your response

1. Overall structure and total target duration (aim 5:30–6:30).
2. A shot-by-shot plan: for each shot, the dashboard page and exactly
   what it must show, the on-screen text and banners (permanent where
   required), and the footage direction (what the camera scrolls or
   plays through, and roughly how long the footage must run).
3. The COMPLETE narration script, shot by shot, in plain simple
   language, with the binding sentence verbatim in the right place.
   Keep each shot's narration tight enough that its footage can cover
   it (assume roughly 150 spoken words per minute; state each shot's
   word count and target seconds).
4. Pacing notes: where the video breathes, where it moves fast, and the
   opening hook (first 15 seconds must land the problem: agents
   breaking out of their boxes).
5. A freshness checklist the builder must satisfy before delivery
   (new captures only, new narration files only, hash proof against
   all prior video inputs, no held-frame padding, no wrong-direction
   page shots, banned-phrase grep clean, independent compliance review
   clean).

## Verdict format

End with a verdict line: GO (design is complete and filmable as
specified) or CONDITIONAL GO (list exactly what is conditional) or NO-GO
(list exactly what blocks). If any required coverage cannot be shown
honestly from the dashboard pages listed, say so plainly and say what
to show instead — never invent footage that does not exist.
