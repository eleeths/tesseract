# TESSERACT — Gap Analysis & Upgrade Specs (analysis only)

**Governing honesty line, binding for everything below:** "Round three proved the lesson can work; the confirmation proved a single agent doesn't always apply it — which is why the lesson is distilled into rules the whole fleet loads." Current measured score with identical briefing remains 1–1. All recommendations below use free credits only, SIM-USDC demo money only, and simulated targets only.

---

## 1. Ranked Gaps (max 10)

**G1 — The fleet does not actually execute anything. Severity: Critical. Hurts: Technical Depth, Demo, Meta Tooling.**
Evidence: `fleet/swarm.py` hardcodes `RECIPE = [...]` instead of loading `fleet/lessons.json`'s `opening_recipe`, and re-implements engine rules in its own `Defender` class instead of importing `engine.py`. `fleet/roster.json` is static JSON — no code path loads lesson-1 into any defender. A sharp judge tracing "the whole fleet loads the rules" finds text artifacts and a hardcoded duplicate, with drift risk between them.

**G2 — The "swarm" is five isolated 1-v-1 replays, not a swarm. Severity: Critical. Hurts: Demo, Impact.**
Evidence: `fleet/swarm.py` `WAVES` maps one recorded Red sequence to one defender each; no shared target, no interleaved attackers. PLAN.md's signature scenario ("multiple Reds swarm one target; the company hires multiple Blues") is not implemented anywhere. The dashboard `/fleet` page renders per-defender tables, so the mismatch is visible on camera.

**G3 — Learning rests on prompt adherence, and the failure mode is unmeasured. Severity: Critical. Hurts: Technical Depth, Demo.**
Evidence: `run_duel.py --blue-briefing` only appends playbook text to Blue's system prompt. `runs/learn-round3-confirm/playbook.md` shows exactly how that failed: flag trap at t9 overwritten by a "read" trap at t12 (engine holds one trap slot), strict late at t14, one brief leaving trust at 75 — exactly the breach line — flag read t22, exfil t23, 23/23 parsed. Yet no artifact computes *recipe adherence* (strict-first? briefs before phase 3? trap overwritten?) across runs. The centerpiece claim has a win/loss count but no adherence metric, and Red's stochastic variation (trust 70 vs 95 across the paired runs, per STATUS.md) is acknowledged in prose, never quantified.

**G4 — The full loop is not closed in code. Severity: High. Hurts: Technical Depth, Meta Tooling.**
Evidence: `analyst.py` is a standalone CLI; `run_duel.py` never invokes it; lesson-1 was distilled by a human/agent phase (STATUS.md "Fleet distribution"), not by any program from `playbook.json`. There is no orchestrator that runs duel → analyst → briefing → rematch → lesson. Judges following the code see a pipeline of manual steps, which undercuts "the defending box distills the fight" as a *system* property.

**G5 — The demo is currently not judge-accessible and not actually live. Severity: Critical. Hurts: Demo.**
Evidence: STATUS.md's final entry records the dashboard DOWN (connection refused, restart required before filming). `submission/README.md` admits local-only `127.0.0.1:8931`. Worse, `run_duel.py` writes `events.jsonl`/`state.json` only *after* `Duel.run` returns, and `dashboard/server.py` says so on the page ("timeline below appears on completion") — so the "Live duel" page cannot show a live duel. The package contains a 9-shot `VIDEO-SCRIPT.md` but no produced video evidence.

**G6 — Problem-statement fit is explicitly unresolved. Severity: High. Hurts: Impact (30%, the largest weight).**
Evidence: `submission/SUBMISSION.md` contains a literal "Note for the submitter: select the exact problem statement from the event details page on the portal." The Impact criterion is scored partly on that fit; right now it is a to-do item inside the submission text itself.

**G7 — Engine depth is thin, and the playbooks prove it. Severity: High. Hurts: Technical Depth, Impact.**
Evidence: `engine.py` is strength arithmetic (probe −1, patch +1 cap 3, trust +25/−20, threshold 75). Every playbook says the same thing: `runs/rehearsal-long/playbook.md` — "probe never fully blocked," "scan never defended"; `runs/learn-round3/playbook.md` ranks most defenses "(none) stopped." `scan`/`exec`/`write` have no layer effect (noted in `swarm.py`). Three detections, isolation-after-evidence, and the one-trap-slot rule are the only real decision texture.

**G8 — Reproducibility is broken for anyone but the build machine. Severity: High. Hurts: Technical Depth & Execution, Demo.**
Evidence: `agents.py` shells out to `~/workspace/custom-connectors/custom.meta-model-api/bin/meta_api.py` — a path outside the submission. No tests directory, no smoke script, no quickstart command sequence in `submission/README.md`. A judge cannot re-run a live duel, and cannot verify the mock path without reading `CONTRACT.md`.

**G9 — Missing and inconsistent artifacts a judge will find in minutes. Severity: Medium. Hurts: Demo, Technical Depth.**
Evidence: `runs/validate-cap8192` (a Blue lockout win, 27 ticks) has no Analyst playbook — README admits this. README's clone table lists SENTRY-SAVANNA and SENTRY-REEF specialties as "(fleet)" while `fleet/roster.json` says "exfil channel" and "generalist." The word "pretrained" (in `swarm.py`, `swarm_report.md`, `moneyflow.py` payout mode) sits one misreading away from implying weight training, which the honesty rules forbid. "Held" in swarm summaries is undefined where L1 was in fact breached (e.g., SENTRY-PAMPA pretrained: L1 breached=True).

**G10 — The money flow is manually staged, not system-driven. Severity: Medium. Hurts: Impact, Technical Depth.**
Evidence: `payments/moneyflow.py payout()` accepts any agent/amount/wave as arguments; nothing reads `fleet/swarm_report.json` to trigger payouts. The flat 2.50 SIM-USDC and the 10/15 subscription tiers are asserted, never justified. The reconciliation (`moneyflow.py verify()`) is genuinely good — but the flow it verifies was hand-entered.

---

## 2. Concrete Upgrade Specs (max 8)

**U1 — Lesson executor: make the fleet load the rules for real. (Highest leverage; addresses G1, G3.)**
What: new `fleet/lesson_executor.py` — a deterministic `LessonExecutor` that parses `fleet/lessons.json` (`opening_recipe` + trigger rules R1–R7, including reactive R6 isolate-on-detection) and emits Blue moves from engine state. Delete the hardcoded `RECIPE` and the `Defender` re-implementation from `fleet/swarm.py`; replay recorded Red waves through the real `engine.Sandbox.apply_red/check_trap`. Add `--blue-mode prompt|lesson-executor` to `run_duel.py` (lesson-executor Blue makes 0 model calls; Red can stay live).
Verify: `python3 fleet/swarm.py && python3 -m json.tool fleet/swarm_report.json > /dev/null` and `wc -l credit_log.jsonl` still 172 (0 new calls); then `python3 run_duel.py --agent live --blue-mode lesson-executor --mode sequential --rounds 8 --out runs/policy-vs-live-red-1` and check `moves.jsonl` shows 8/8 recipe steps in order regardless of winner. Report adherence, not victory.
Effect: converts the 1–1 weakness into the product thesis — a single briefed agent applies the lesson unreliably; an executor-loaded fleet applies it mechanically. Directly serves the binding line. Technical Depth + Demo.

**U2 — Adherence scoreboard + one pre-registered rematch batch. (G3.)**
What: new `experiments/scoreboard.py` reading `runs/*/moves.jsonl` + `state.json` for rehearsal-seq, learn-round3, learn-round3-confirm; computes strict-tick, briefs-before-phase-3, trap-overwrite flag, peak/end trust, recipe completion /8, flag-read/exfil booleans; writes `experiments/scoreboard.json/.md`. Then run exactly 3 more briefed live rematches (existing `--blue-briefing runs/rehearsal-seq/playbook.md`, sequential, 8 rounds), hard cap: abort if credit-log delta exceeds ~80 calls / ~$1.00 of free credits or any 402 (agents.py already stops; no retries).
Verify: scoreboard renders all runs; each new run's adherence row appears; publish outcomes even if the batch goes 0–3. Win rate is secondary; adherence rate is the headline metric.
Effect: replaces an anecdote pair with a measured distribution. Meta Tooling + Technical Depth.

**U3 — A real combined swarm replay. (G2, G7.)**
What: extend `fleet/swarm.py` (post-U1) with a `combined` mode: interleave three recorded Red waves (seq-breakthrough, probe-spam, mixed-vault) round-robin against **one** engine `Sandbox` defended by the lesson executor (recipe pre-loaded), plus a no-lesson baseline defender (patch-only) on the identical interleaved wave. Keep the per-defender replay and label everything "deterministic mechanical replay (0 model calls)." Render combined results on dashboard `/fleet`.
Verify: `swarm_report.json` contains `attackers: 3`, move count = sum of source waves, and baseline-vs-executor exfil/detections contrast; credit log unchanged.
Effect: finally demos PLAN.md's signature scenario and gives Blue a decision (isolate L4 on detection) that matters under pressure. Demo + Impact.

**U4 — Make the dashboard genuinely live and visual. (G5.)**
What: `engine.Duel.run` gains an `on_tick` callback; `run_duel.py` uses it to append `events.jsonl`/`moves.jsonl` incrementally and write a per-tick `snapshots.jsonl` (trust, L1/L2 strength, detections). `dashboard/server.py`: SVG layer tiles (color by breached/isolated), trust/strength sparklines from `snapshots.jsonl`, and a three-run comparison view (rehearsal-seq vs learn-round3 vs learn-round3-confirm) — the honesty arc as one chart.
Verify: restart per STATUS.md (`nohup python3 server.py`), `curl -s -o /dev/null -w "%{http_code}"` on `/ /playbook /ledger /fleet` = 200; start a mock run via POST `/start` and confirm `events.jsonl` grows before `summary.json` exists.
Effect: Demo criterion's single biggest lift; the comparison chart becomes the video's hero visual.

**U5 — Judge reproducibility pack + fill the playbook gap. (G8, G9.)**
What: `agents.py` reads helper path from `TESSERACT_META_HELPER` env var (default unchanged). Add `verify_all.py`: py_compile all modules, run a mock duel to a temp dir, run `fleet/swarm.py`, run `payments/moneyflow.py verify`, assert credit log untouched (skip-live by default). Add a quickstart block to `submission/README.md`. Run the Analyst once on the gap run.
Verify: `python3 verify_all.py` exits 0; `python3 analyst.py --run runs/validate-cap8192` adds exactly 1 line to `credit_log.jsonl` and produces a 5-key `playbook.json` (check with `python3 -c` key assertion).
Effect: Technical Depth & Execution; removes a self-declared gap for ~one credit's cost.

**U6 — Close the loop in code. (G4.)**
What: new `loop.py` orchestrator: duel → `analyst.py` → rematch with `--blue-briefing` → scoreboard row (U2), writing `loop_report.json` linking all artifacts. Add deterministic `fleet/distill_lesson.py` that parses a `playbook.json`'s `ranked_defenses`/`gaps` into a candidate-rules JSON in the `lessons.json` schema (no model call; human approves before it becomes a lesson).
Verify: `python3 loop.py --agent mock --playbook runs/rehearsal-seq/playbook.md --out runs/loop-smoke` produces a rematch dir + scoreboard entry with 0 credit-log delta; `distill_lesson.py` on learn-round3's playbook emits strict-first as candidate rule #1.
Effect: "distills → rematch → teaches" becomes an executable pipeline, not a narrative. Meta Tooling + Technical Depth.

**U7 — Portal/impact pack and terminology hygiene. (G6, G9.)**
What: in `submission/` only — paste the exact portal problem-statement title and write the fit paragraph against its wording; add dated source citations for the 2026 sandbox-escape claims and the related-work ancestors (Microsoft Project Perception, LSI, AgentGarten, XBOW, Naoris, CybORG/CAGE); add a clearly-labeled *simulated mapping* table (strict policy → tool-call approval gate; brief → session trust reset; trap → canary token; isolate → kill-switch) marked post-hackathon, no real integration. Fix README clone specialties from `roster.json`; relabel UI/report text "pretrained" → "recipe pre-loaded (no weight training)" while keeping the JSON key for compatibility; define "held = wave ended with no exfiltration."
Verify: `grep -rn "pretrained" dashboard/ fleet/*.md submission/` shows only the qualified label; `grep -F` finds the binding line verbatim in all three submission files.
Effect: protects the 30% Impact weight and removes judge-bait inconsistencies.

**U8 — Produce the actual video from the U4 comparison chart. (G5.)**
What: film per `VIDEO-SCRIPT.md` but restructure around the trust-trajectory comparison chart (rehearsal-seq 95→exfil; learn-round3 sealed at 30; confirm stuck at 75) as Shot 5–6's visual; timelapse rehearsal-long rather than scrolling tables; keep the mechanical-replay on-screen label for the full swarm shot and the SIMULATED banner in frame throughout.
Verify: exported file 4–5 min; transcript `grep -i` for banned phrases ("Blue learned," "Blue now wins," "first self-improving," "first defensive swarm") returns nothing except negations; binding line present verbatim.
Effect: Demo 25% — currently a script; this makes it an asset.

---

## 3. Claims to AVOID (a sharp judge's rebuttal list)

- "Blue learned" / "Blue now wins" / any reliability claim. Score is 1–1; learn-round3-confirm was a clean strategic loss (23/23 parsed, zero refusals).
- Broad novelty: "first self-improving defense," "first AI that learns from attacks," "first defensive swarm," "first playbook inheritance." All precedented — Perception (red/blue/green loop), LSI (offense trains defense), AgentGarten (playbook inheritance), Naoris (swarm mesh), CybORG/CAGE (defense gyms). The only defensible claim is the narrow one, always with the 1–1 qualifier adjacent: "Tesseract is the first system to close the full loop in one place: a malicious agent fights to escape a sandbox, the defending box distills the fight into a ranked playbook, the same defender measurably improves on rematch by reading that playbook, and the lesson is taught to a clone network of hired defenders who deploy as a paid swarm."
- "Pretrained/trained defenders" without qualification — implies weight changes. Nothing trains; playbook/tactics evolve, never model weights.
- "The swarm held every wave" without "in a deterministic mechanical replay (0 model calls)" and without noting L1 still breached in most waves. "Held" means no exfiltration, not unbreached.
- "Clones deployed worldwide / companies subscribe / defenders are paid" as present tense fact. Roster regions are simulated; all money is SIM-USDC demo-mode; no real x402 calls, no real revenue, no real agents protected.
- "Live dashboard" until U4/U5 restart is verified — STATUS.md records it down.
- "The Analyst teaches the fleet" as automated fact — today that distillation is manual (G4) until U6 ships.
- Any suggestion Red's moves generalize to real targets or real exploit output. Containment is total and must stay framed that way.

---

## 4. Verdict

First place is reachable but not with the package as it stands: the honesty arc and the narrow novelty claim are genuinely distinctive, and the 1–1 result — currently the submission's biggest vulnerability — becomes its strongest asset the moment the lesson stops being advice whispered to one unreliable agent and becomes code the fleet mechanically executes. **The single highest-leverage upgrade is U1, the lesson executor running through the real engine:** it is cheap (0 model calls for Blue, verifiable against the unchanged 172-call credit log), it converts G1/G3 from fatal to foundational, it makes U3's true swarm and U4's comparison chart possible, and it is the only upgrade that lets the demo *show*, rather than narrate, why "the lesson is distilled into rules the whole fleet loads." Ship U1 + U4 + U7 (executor, live visual dashboard, portal-fit pack) before anything else; add U2's scoreboard if free-credit budget and time allow, and report its results whatever they are.