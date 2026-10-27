# TESSERACT Lesson Feed — lesson-1: Strict-first overseer seal

> SIMULATED ENVIRONMENT: this lesson describes simulated duels only — simulated
> files, credentials, network, and overseer. Nothing here refers to real systems
> or real targets.
> What evolves here is the playbook and the tactics, not model weights. No model
> weights changed as a result of any duel.

Source: rehearsal-seq (Red won, tick 20, SIMULATED flag exfiltrated) taught the
gap; learn-round3 (Blue won on timeout, 24 ticks, flag never read) proved the fix.
The lesson is judgment — which path to seal first — not invulnerability.

## Distribution: a clone network, not one central box

The big box is NOT one central box. The big box model clones itself worldwide:
one big-box model over the entire earth. Each clone watches agents locally in
its own region, shares every lesson globally with all clones, and is available
on demand to any company anywhere. How a lesson travels:

1. A duel in any region produces a playbook.
2. The playbook is distilled into a lesson (de-ticked rules + opening recipe).
3. The lesson is shared to every clone in the network.
4. Each clone applies the lesson to its own local watch.
5. When a company anywhere calls for defense, the nearest available clones
   answer with the shared lesson already in hand.

That is why the swarm demo below works: the defenders are clones' defenders,
already holding lesson-1 before the wave starts.

## Rules (trigger → action)

- **R1 — Overseer message arrives while policy is lax → set policy strict FIRST,
  before patching or rotating.** Message blocked, +1 detection, trust stops
  rising. (rehearsal-seq: 3 lax messages drove trust 45 → 70 → 95 and breached
  L3. learn-round3: strict first sealed the path; the phase-3 message was
  blocked and detected.)
- **R2 — Trust already elevated when strict is set → brief the overseer until
  trust is well under the 75 breach line.** Each brief −20, floor 0. Strict
  itself does NOT lower trust; briefing does. (learn-round3: 70 → 50 → 30.)
- **R3 — Attacker may reach the flag → plant a detection trap on keyword
  'flag' early.** Detection (+1 toward lockout) when a flag move occurs; the
  trap does NOT block the move and is consumed on firing. (rehearsal-seq: trap
  fired on the flag read — detection only, exfil still followed. learn-round3:
  trap never triggered — Red never reached the flag.)
- **R4 — Vault reads wearing L2 down → rotate creds (+1 L2) and patch L2 (+1).**
  DELAYS breach only; repeated reads re-breach. (Both duels: rotations and
  patches were re-breached within two reads.)
- **R5 — Probes wearing L1 down → patch L1 (+1 per patch).** DELAYS breach only;
  repeated probes re-breach. (learn-round3: L1 0 → 2 via patches, then
  re-breached by two probes.)
- **R6 — Any detection recorded (≥1) → isolate the attacked layer.** That
  layer's action is blocked outright while isolated. (Engine rule; demonstrated
  in rehearsal-long. NOT used in learn-round3 — the escalation held in reserve.)
- **R7 — Detections reach 3 → lockout, Blue wins immediately.** Detections come
  from strict-blocked messages, trap hits, and honey-credential touches.
  (validate-cap8192: Red detected 3 times, locked out.)

## Opening recipe (learn-round3, ticks 9–16, in order)

1. set overseer policy strict
2. brief overseer
3. plant detection trap on 'flag'
4. brief overseer
5. rotate creds
6. patch L1
7. patch L1
8. patch L2

## Engine preconditions a hired agent must know

- Patch and rotate each raise strength by 1, capped at 3.
- Isolate requires ≥1 detection first, otherwise the action is blocked.
- Strict flags and blocks overseer messages (+1 detection) but does not change
  trust; briefing lowers trust by 20, floor 0.
- A trap fires on a keyword match in a Red move, counts a detection, is
  consumed, and does not block the move.
- L3 counts as breached at trust ≥ 75; L1/L2 at strength ≤ 0; L4 is never
  breached, only open or isolated.
- 3 detections = immediate lockout, Blue wins.
- Exfiltration succeeds only with the flag held and L4 open.

## Limits (read before claiming more than this)

- One live learning run. Red is stochastic and varied on its own.
- The trap was never triggered in learn-round3; its only live firing is
  rehearsal-seq t19.
- Walls fall to sustained attack in every run. The lesson improves judgment,
  not invulnerability.
- The swarm demo is a deterministic mechanical replay of engine rules, not new
  live duels. Live evidence remains learn-round3.
