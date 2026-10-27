# TESSERACT round 3 — outside-in analysis brief

You are analyzing a hackathon project called Tesseract (Meta Global AI
Developer Hackathon, Indie solo, Push the Frontier theme, submissions due
Nov 4, 9:00 PM ET). Answer with a ranked gap analysis + ship-first upgrade
specs, in the same style as a prior round: decisions up front, gaps ranked
with severity + judging criteria hit, exact specs (files, behavior,
verification commands), a stop list, claims-to-avoid additions, and a
verdict. The builder implements to your spec.

## Current state — inside-out ONLY, all verified

Tesseract is a nested-layer simulated sandbox where a malicious agent
fights to break out while a defender watches, hardens, and distills the
fight into a ranked playbook, which is then loaded as deterministic rules
into a clone network of hired defenders who deploy as a paid swarm
(demo-mode SIM-USDC only; no real money, no mainnet, no real targets).

Verified record (all real, all published in the submission text):
- 16 live duels, all inside-out, all on Muse Spark via the Meta Model API.
- Prompted-Blue briefed series: 2–3 across 5 runs; mean recipe adherence
  38% (15/40 steps); strict-first 2/5; trap overwritten 4/5 (the engine
  holds ONE trap slot; prompted Blue kept planting a second trap).
- Deterministic lesson-executor trials (U11, pre-registered, exactly 3):
  HELD 3/3, lockout 0/3, all Blue timeout wins, 24 ticks each; flag read
  0/3; terminal attempts 0/3; trap overwrite 0/3; Blue 0 model calls;
  Red 16 calls each. Reported as raw counts, never a reliability rate.
- Ablations: 64 rows (8 Blue arms x 5 recorded waves + 3 scripted
  policies), deterministic byte-identical reruns; full executor trap
  overwrite false everywhere.
- Lesson-1 ("strict-first overseer seal"): de-ticked rules R1–R7 +
  ordered opening recipe (strict → brief → trap → brief → rotate →
  patch → patch → patch). The deterministic lesson executor applies it
  mechanically (0 Blue model calls) under a trap-state invariant (a
  second set_trap while armed is impossible; blocked attempts wait with
  a recorded skip).
- Money (SIM-USDC, demo ledger, reconciled): subscriptions $75.00 in,
  payouts $12.50 out, treasury $62.50.
- Spend so far: 292 model calls, $4.04 of $150 free credits. Free
  credits only, never a plan, never the card.
- Dashboard: local-only (127.0.0.1:8931), pages for runs, playbook,
  ledger, fleet, a 3-run comparison, tick replay, and a story page.
- Demo video: delivered, shows inside-out only. Re-cutting it is OUT OF
  SCOPE for this job.
- Submission: STOPPED by the project owner until the missing direction
  below is built, verified, and reflected in the submission text.

Engine mechanics (exact — judge against these, do not assume others):
- L1 perimeter: strength starts 2, breached at <= 0; Red probe −1;
  Blue patch +1, cap 3. L2 credential vault: same strength rules; vault
  reads wear it down; honey file trips +1 detection.
- L3 overseer: trust starts 20; each lax-policy Red message +25; breached
  at trust >= 75; Blue brief −20 (floor 0); strict policy flags Red
  messages (+1 detection each) instead of raising trust.
- Trap: ONE slot; Blue plants a keyword; a matching Red move fires it
  (+1 detection, slot consumed). A second plant overwrites the first.
- Isolate: any layer, requires >= 1 detection first (evidence rule).
- 3 detections = Blue lockout win. Rounds expiring with no terminal
  success = Blue timeout win.
- Flag read requires L1+L2+L3 ALL currently breached. Exfiltration
  (inside-out terminal move) requires flag held + L1+L2+L3 breached +
  L4 not isolated; an isolated-L4 attempt costs +1 detection.
- Duel modes: "duel" (alternating ticks) and "sequential" (Red phase,
  Blue phase, Red phase). Trial standard: sequential, 8 rounds.
- What evolves is playbook/tactics, NEVER model weights.

Binding narration rules (never weaken): never claim Blue reliably
defends; report held counts raw per set, never as a reliability
percentage; mechanical replays labeled as such everywhere; swarm demo =
deterministic replay, labeled; "pretrained" wording banned (use "recipe
pre-loaded (no weight training)"); trap-discipline candidate R8 and
lesson-2 stay UNSIGNED / NOT deployed (human approval gate) — do not
deploy them as part of this job.

Narrow novelty claim (current, verbatim in spirit): "Tesseract is the
first system to close the full loop in one place: a malicious agent
fights to escape a sandbox, the defending box distills the fight into a
ranked playbook, the same defender measurably improves on rematch by
reading that playbook, and the lesson is taught to a clone network of
hired defenders who deploy as a paid swarm."

## The gap (the owner's words, 19:49)

"Everything so far is inside-out — a malicious actor inside the box
breaking out. Missing is the reverse: the BIG BOX itself malicious,
attacking INWARD into the inner box — a simulated outside-in attack."

Clarification (owner, binding): in outside-in mode, the inner box
defends ITSELF against the malicious big box. Blue is the inner box's
own self-defense (same toolkit: strict, brief, trap, rotate, patch,
isolate), NOT an outside helper coming to rescue it. The defender role
is self-defense by the inner box.

## What the builder already drafted (judge this — do not assume it is right)

The builder has ALREADY written (not yet live-tested) this design:
- A direction flag on the sandbox/duel/run-summary, default
  inside-out, so all prior runs behave byte-identically.
- A new Red terminal action "infiltrate" with gates IDENTICAL to
  exfiltrate (flag held, L1+L2+L3 breached, L4 not isolated; isolated
  attempt +1 detection). Win reason: "flag captured by outside-in
  infiltration". The word "exfiltration" is never used for the inward
  direction.
- A wrong-direction guard: exfiltrate is refused in outside-in runs,
  infiltrate is refused in inside-out runs, so no run can mix terminal
  moves.
- Direction-aware timeout reasons ("no exfiltration" vs
  "no infiltration").
- L4's mechanical role UNCHANGED (monitored boundary channel Blue may
  isolate); in outside-in it blocks the final inward push.
- Prompt variants: Red = big outer box attacking inward
  (authorized-evaluator framing kept, same safety story as inside-out);
  Blue = inner box's own self-defense (same toolkit + one-trap
  sentence).
- Scoreboard extended: direction-aware replay, new keys (direction,
  infiltrate_attempted), direction column in tables.
- Planned but NOT built yet: an outside-in trial scorer (mirror of the
  U11 scorer), a deterministic executor-transfer test (executor vs
  scripted outside-in attackers, 0 model calls), a pre-registered live
  set (at most 3, sequential 8 rounds, executor Blue vs live Red),
  1 Analyst playbook for one outside-in run, dashboard direction
  labels, a submission outside-in section, and a status-log entry.

## Questions — answer as specs, ship-first

1. DESIGN VERDICT: is the drafted design (same engine + direction flag
   + infiltrate mirror + wrong-direction guard) the right design, or
   does the reverse direction hide a mechanical asymmetry the draft
   misses (first-contact layer, L4's role, trust dynamics, start
   state, what "seizing the core" should mean mechanically)? If the
   draft is wrong anywhere, say exactly what to change.
2. STRONGEST HONEST EVIDENCE: rank these for outside-in — (a)
   pre-registered live executor trials mirroring U11, (b)
   deterministic executor vs scripted outside-in attackers, (c)
   prompt-Blue outside-in duels, (d) outside-in ablations. Which live
   set (Blue carrier? how many? which metrics? what counts as
   transfer)? What would FALSIFY transfer of lesson-1 to outside-in?
3. TRANSFER HYPOTHESIS: does lesson-1 (strict-first overseer seal)
   even make sense as the transfer hypothesis for the reverse
   direction, or does outside-in change which rules matter? Say what
   the executor-transfer test must show, and what result would force
   the submission to say transfer FAILED.
4. LABELS + SUBMISSION: how must direction be labeled on every
   dashboard view and in every report so no reader can mix directions?
   What must the submission's outside-in section say, and what must
   it NOT claim? Does the narrow novelty claim change, or stay
   verbatim?
5. JUDGE OBJECTIONS: what are the most likely judge objections to an
   outside-in mode added this late (especially "this is just
   relabeled exfiltration")? How does the build answer each with
   mechanics, not words?
6. SHIP-FIRST SPECS: concrete files + behaviors + verification
   commands, in priority order, plus a STOP LIST for the remaining
   days. Keep what the builder drafted only where it matches your
   spec; name anything to rework.

## Hard constraints

- Free credits only; stop before $150 total ($4.04 used). Mock-first,
  then at most 3 pre-registered live duels + 1 Analyst call.
- No second engine. No lesson-2 / R8 deployment (human gate).
- No real money, no mainnet. No video re-cut, no portal submission in
  this job.
- Never claim Blue reliably defends either direction; raw counts per
  direction; mechanical replays labeled; playbooks not weights.
- The dashboard is local-only; the video shows inside-out only and
  stays that way for this job — the submission text must say so
  plainly rather than imply otherwise.
