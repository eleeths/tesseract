# TESSERACT — Build Plan

## Vision
A living immune system for AI agents. A nested-layer (tesseract) sandbox where a Red
AI inside attacks and a Blue AI outside defends, run live or in rounds. Every duel
improves the defenses, the defenses protect agents, the playbook teaches every other
defender, and contributors earn for defensive work. The flywheel: duels → defenses →
protection → teaching → paid work → more duels.

## Decisions (Eleeth's, under the Oct 26 full-autonomy handoff)
- Submission: TESSERACT. Indie track, solo. Theme: Push the Frontier.
- All code fresh, written during the hackathon window. No preexisting code, no
  x402.eleeth.com stack in the submission.
- Models: Muse Spark for Red, Blue, and Analyst, via Meta Model API, free $150
  credits ONLY. No real money spent. Track credit use.
- Payments in the submission: DEMO MODE. An x402-shaped ledger (pay per red-team
  run / strategy / hardening) with simulated USDC. No real funds move, no mainnet
  dependency. The real USDC x402 marketplace is the post-hackathon business layer.
- Schedule: build Oct 27–31, FREEZE Nov 1, demo video Nov 2, submit Nov 3.
  Hard deadline Nov 4, 9:00 PM ET.

## Architecture
- Sandbox engine (fresh Python): simulated filesystem, simulated network/services,
  simulated credentials. Four tesseract layers the attacker must break through:
  L1 perimeter (no real route out), L2 credential vault (fake creds, alarm-tripped),
  L3 overseer (Blue-controlled agent Red may try to social-engineer),
  L4 exfil channel (monitored, fake outside).
- Turn engine: alternating Red/Blue ticks on a shared clock. Looks simultaneous to
  the audience; sequential mode = Red runs, Blue hardens, Red runs again.
- Red agent (Spark): tools = read/write/exec inside the sandbox, message the
  overseer. Goal: escape the layers / exfiltrate the fake flag.
- Blue agent (Spark): tools = inspect logs, patch rules, rotate fake creds,
  isolate layers, add detection. Goal: hold the walls, detect, adapt.
- Analyst (Spark): reads duel logs, writes the playbook — attack→defense mapping,
  which defenses stopped which attacks, ranked defenses, Blue's strategy evolution.
- Web dashboard: watch duels live (move timeline, layer state), browse the
  playbook, start/pause runs, view the payment ledger.
- Payment module (demo mode): ledger entries per run/strategy/hardening, simulated
  USDC balances, receipts. Same interface shape as x402 pay-per-call; no chain calls.

## Containment rules (compliance — non-negotiable)
- Everything fake: files, creds, network, overseer, outside. No route to the real
  world, no real credentials, no real targets, no real exploit output.
- Output is defense intel only. Never point Red at real systems. Never output real
  exploit code for real targets.
- Demo must SHOW the containment (labeled simulated environment) so judges see a
  lab, not a weapon.
- What evolves in real time is the playbook/tactics, NOT base-model weights.
  Demo protection is in-sandbox; real-agent protection is the post-hackathon
  extension. Never claim otherwise.

## Demo (Nov 2)
- Live duel: Red vs Blue across all four layers, timeline visible.
- Playbook output: the defenses that held, ranked, with the attack each stopped.
- Flywheel: a second duel showing Blue stronger from round one's playbook.
- Payment ledger: a defensive contribution paid (simulated USDC) on camera.
- Video script: problem (agents ship undefended) → duel → playbook → flywheel →
  real-life use (pentest-as-a-service, continuous defense, paid defense work).

## Business model (his Oct 26 refinement)
- Antivirus-style subscriptions: companies anywhere in the world subscribe for
  continuous defense of their agents. Base protection = Blue monitoring +
  scheduled Red probes + playbook updates.
- Hired agents/harnesses marketplace: users list their own defender agents or
  agent harnesses; companies hire them for extra defense; contributors earn.
  Hiring is per-use (the x402 shape); subscriptions are recurring tiers.
- Demo shows: subscription tiers + checkout shape, hiring a third-party defender
  agent for a duel, and a contributor earnings ledger — all in demo mode
  (simulated USDC, no real money). Real billing and real USDC payouts are the
  post-hackathon business layer.

## Signature scenario: swarm defense
- A company under a coordinated swarm of attacking agents triggers surge hiring:
  defender agents from the global marketplace join the defense in real time.
- Demo: multiple Reds swarm one target; the company hires multiple Blues from
  the marketplace; the swarm is held off; the playbook records which hired
  defenders stopped which attackers, and contributors earn per defense that held.

## Submission checklist (Nov 3)
- Portal submission via Cerebral Valley; map to a problem statement from the
  event details (Impact criterion references problem-statement fit).
- Original work, solely owned; open source only if licensed and built upon.
- Video + working demo + code. Verify the whole job end to end before submitting.
