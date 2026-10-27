# TESSERACT — Round 2 Remaining Gaps and Upgrade Specs

## Decisions up front

1. **Prompt-briefed Blue should be retired as the product headline.** Keep it as the control arm that demonstrates why prompt-carried lessons are unreliable: 2–3 across 5, 38% mean recipe adherence (15/40), strict-first in only 2/5, and trap overwritten in 4/5. The deterministic lesson executor is the deployable product. Do not buy another prompt-tuning batch hoping stochastic adherence becomes reliable.

2. **Teach trap discipline; do not add a second trap slot.** A second slot would make Blue stronger after the weakness was discovered, invalidate comparability with the recorded 2–3 series, change the meaning of lesson-1, and hide the exact structural lesson the fleet is supposed to learn. Recorded Blue choices were also made under the one-slot constraint, so the old runs cannot honestly be rescored as if two slots had existed.

3. **The strongest new evidence is not more prompted rematches.** It is ablations and held-out scripted attackers deterministically, followed by a small pre-registered set of live-Red versus executor-Blue duels. Do not build simultaneous live Reds into one sandbox for this round.

4. **Freeze engine mechanics.** The thin engine is legible, and every recorded claim depends on its exact arithmetic. Add invariants, formal documentation, scripted attackers, and observability — not new layer mechanics.

5. **Stop list for this round:** no second trap slot, no engine rebalance, no more prompt-adherence live batch, no simultaneous-attacker engine rewrite, no hosted dashboard work beyond video-friendly local pages, no real payments, no lesson overwriting without the existing human gate.

---

## Remaining gaps, ranked

| ID | Gap | Severity | Judging criteria hit | Why it still matters |
|---|---|---:|---|---|
| R2-G1 | **Carrier confusion and latent trap bug.** The submission can still be read as “Blue learns by reading,” while the data say prompted Blue applies the lesson only 38% of the time. Worse, the executor’s Phase B — trap on “flag” — may reproduce the same overwrite flaw if it sets a trap while the recipe trap is still armed. The deterministic carrier has not yet been shown trap-safe by construction. | Critical | Impact 30%, Demo 25%, Technical Depth 20% | This is the central finding. If the executor can overwrite its own trap, the fleet story collapses into “we automated the same mistake.” |
| R2-G2 | **Circular evaluation and straw baseline.** Executor success is currently a mechanical replay against recorded waves with no documented held-out separation from the runs that produced lesson-1. The comparison baseline is patch-only, which never briefs, traps, isolates, or controls trust, so trust 100 and exfiltration are close to inevitable. Beating patch-only proves the recipe beats almost nothing. | Critical | Technical Depth 20%, Demo 25% | A sharp judge will ask: “Was the lesson tested on the attacks it was written from, and against anything except a deliberately weak defender?” |
| R2-G3 | **No live attacker has faced the executor, and “swarm” semantics are still thin.** The combined replay interleaves 40 recorded moves against one Sandbox. That is a useful replay, but it is not independent clones defending independent boxes, and Red cannot adapt to executor moves in open-loop replay. | Critical | Impact 30%, Use of Meta AI Tooling 25%, Demo 25% | The fleet/swarm claim is part of the narrow novelty claim. Currently the strongest fleet evidence is also the easiest to dismiss as replay theatre if its boundaries are not made mechanically explicit. |
| R2-G4 | **Evidence presentation is fragmented and easy to cherry-pick.** Headline series is n=5; the three U2 batch runs have no Analyst playbooks; `/compare` foregrounds rehearsal-seq, learn-round3, and learn-round3-confirm rather than the full 1-win/2-loss briefed batch beside them. Recipe adherence alone can also mislead: late or low-value steps can count toward an ordered subsequence without helping. | High | Demo 25%, Technical Depth 20% | Judges should see the full 2–3 series, adherence beside outcome, strict tick, brief timing, and trap overwrite in one place. Anything less invites “you picked the good run.” |
| R2-G5 | **Distill → lesson-2 → propagation is still shelfware.** `distill_lesson.py` exists, but there is no exercised candidate lesson derived from all existing playbooks plus the trap finding, with provenance and an unmapped-rate report. The 5-step distribution block in `lessons.json` is narrative data, not an executed propagation/version-skew simulation. All five clones hold identical lesson-1; specialties/regions have no mechanical effect. | High | Impact 30%, Technical Depth 20% | The claimed differentiator is the full loop into a clone network. If distillation and propagation are not demonstrated as working artifacts, the loop is only partially closed — and the human approval gate must be presented as a gate, not hidden inside “automated loop” language. |
| R2-G6 | **Dashboard is analytical, not yet video-native, and Meta tooling is under-surfaced.** `/compare` has tiles and sparklines, but the video needs a tick-by-tick replay where a judge can see strict fire, trust fall 70→50→30 in learn-round3, the trap being overwritten in failed runs, trust crossing the 75 line, flag gating, and lockout/exfil. Spark usage — muse-spark-1.3, roles, refusals, parse fails, cost discipline — is logged but not turned into an inspectable judging artifact. | High | Demo 25%, Meta AI Tooling 25% | Judges see only the video. Static tables will not land the trap finding or the Meta-tooling criterion as well as a replayable, large-type story surface. |
| R2-G7 | **Business model numbers are asserted, not argued.** $10/$15 tiers and flat $2.50 payouts have no cost basis, packaging difference, or outcome differentiation. Treasury $62.50 reconciles, but reconciliation is not a business model. | Medium | Impact 30% | Without invented customers, the credible move is cost-plus arithmetic from measured Spark call usage plus clearly labelled scenario packaging and payout rules. |
| R2-G8 | **Engine thinness is acceptable; unproven engine correctness is not.** Probe/patch/trust arithmetic is simple and several Red actions have no direct layer effect. That is a fair price for legibility, but there are no stated property/fuzz proofs that cap-3, trust bounds, single-trap overwrite, flag gating, exfil gating, and 3-detection lockout can never be violated. No-effect actions are also not explicitly labelled, so viewers may assume hidden depth. | Medium | Technical Depth 20% | Do not deepen the simulation; prove the existing simulation obeys its own rules and say plainly where it is abstract. |
| R2-G9 | **Phase 1 hygiene is manual, so claims can drift again.** Internal wording still risks “pretrained” (including in payout derivation language), clone “specialties” can be mistaken for mechanisms, the combined swarm win can be confused with the per-wave basis for payouts, and `loop.py` can be over-read as a fully automated fleet loop despite the human lesson-approval gate. | Medium–High | All criteria, credibility | One overstated caption in the video can undo the project’s main asset: unusually honest evidence. This needs a lint/check, not another manual pass. |

---

## Upgrade specs, ship-first

### U9 — Make the executor the product: trap-safe deterministic carrier vs prompted control

**Judging leverage / cost:** Highest. Fixes the core story and a possible latent executor bug. Small–medium job. **0 model calls.**

**Files to change:**
- `fleet/lesson_executor.py`
- `fleet/lessons.json` — read-only in this spec; do **not** overwrite lesson-1
- New: `fleet/trap_discipline.candidate.json`
- `prompts.py`
- `analyst.py` — Markdown footer only; playbook JSON remains exactly 5 keys
- `run_duel.py`
- `experiments/scoreboard.py`
- New: `experiments/carrier_comparison.py`
- New: `tests/test_trap_discipline.py`
- `submission/README.md`, `submission/SUBMISSION.md`

**Exact behavior:**
1. Add a trap-state invariant to `LessonExecutor`, independent of lesson wording:
   - Track or read trap state as `EMPTY` or `ARMED(trigger)`. Prefer an existing Sandbox/snapshot field if present; if none exists, add a read-only exposure of the existing trap slot. No engine rule changes.
   - The executor may issue `set_trap` only when state is `EMPTY`. This applies to both the Phase A recipe step and the Phase B “flag” reaction.
   - If a trap step is reached while `ARMED`, emit the existing wait/no-op move with rationale metadata `executor_skip="trap_already_armed"`, preserving the armed trigger. Do not silently replace it.
   - Return to `EMPTY` only after an engine event/snapshot shows the trap fired or was consumed. A second `set_trap` while armed must be impossible through executor code paths, not merely unlikely.
2. Encode the proposed rule as a candidate, not a silent lesson rewrite:
   - `fleet/trap_discipline.candidate.json` contains: `rule_id="R8-CANDIDATE"`, `trigger="own trap is armed"`, `action="do_not_set_trap_until_trap_fired_or_consumed"`, `evidence="scoreboard: trap overwritten in 4/5 briefed runs"`, `status="awaiting_coordinator_approval"`, and `applies_to_lessons=["lesson-1"]`.
   - `run_duel.py` gains `--lesson-file <path>` for executor mode, defaulting to the current production `fleet/lessons.json`. Executor metadata records lesson file path and SHA-256.
3. Prompt path gets the same instruction but is explicitly demoted:
   - In `prompts.py` Blue instructions and in the Markdown briefing footer generated by `analyst.py`, add: “One trap only: if you have set a trap and it has not fired, do not set another trap. Defend with strict, brief, rotate, patch, or wait instead.”
   - This footer lives outside the Analyst’s 5-key JSON contract. Label it in code comments and submission text as an untested prompt instruction until/unless a future live run tests it. Its purpose now is consistency, not a claimed fix.
4. Stamp reproducibility metadata into every new run summary from `run_duel.py`: `blue_mode`, model identifier already used by `agents.py`, briefing/lesson SHA-256 when present, and `executor_trap_invariant=true` for lesson-executor mode. Do not alter move generation for prompt mode.
5. Extend `experiments/scoreboard.py` output with: `trap_sets`, `trap_first_trigger`, `trap_overwrite_trigger` (trigger used in the overwriting set, or null), `trap_armed_at_flag_attempt`, and `executor_trap_skips`. Existing fields and definitions stay unchanged.
6. `experiments/carrier_comparison.py` builds the dual-carrier table from artifacts, not hand-typed outcomes:
   - Prompt carrier: all five briefed runs, per-run outcome, recipe `/8`, strict tick, briefs before phase 3, trap overwrite. Aggregate must recompute to the recorded 15/40, 38%, strict-first 2/5, overwrite 4/5; if source artifacts disagree, fail loudly rather than printing a softer number.
   - Executor carrier: same recorded waves where wave extraction already exists, plus mock-duel executor runs. Label every executor row `open-loop replay` or `mock`, never “rematch.”
   - Replace the word “adherence” for the executor with “execution completeness” in generated output. The executor does not “learn to follow”; it deterministically executes or skips under stated preconditions.

**Verification:**
```bash
python -m unittest tests.test_trap_discipline -v
python -m py_compile fleet/lesson_executor.py prompts.py analyst.py run_duel.py experiments/scoreboard.py experiments/carrier_comparison.py
python experiments/carrier_comparison.py --out /tmp/tesseract-carrier
python verify_all.py
```
Unit tests must construct a state where a trap is armed and then force both the recipe trap step and a Phase B “flag” reaction; assert zero additional `set_trap` moves, armed trigger unchanged, and one recorded skip. Then simulate trap consumption and assert the executor may arm again. Run one existing mock duel in lesson-executor mode to a temp dir and assert its scoreboard row has `trap_overwrite=false`. Finally rerun the existing swarm replay command used by `verify_all.py`; if the combined-arm outcome changes because an overwrite is now prevented, report the new outcome in the change log — do not tune the test to preserve the old win.

---

### U10 — Kill the circular-evaluation objection: ablations plus held-out scripted Red policies

**Judging leverage / cost:** Very high for Technical Depth; protects the Demo from the strongest technical objection. Medium job. **0 model calls.**

**Files to change:**
- `fleet/lesson_executor.py` — add configuration switches only; default behavior unchanged
- New: `experiments/scripted_red.py`
- New: `experiments/ablations.py`
- New: `tests/test_ablations.py`
- `experiments/scoreboard.py` — reuse existing scorer; add fields only if U9 has not already added them
- `submission/SUBMISSION.md` — one short “evaluation limits” paragraph after results exist

**Exact behavior:**
1. Add executor ablation switches with defaults equal to full lesson execution: `disable_strict`, `disable_brief`, `disable_trap`, `disable_patch_rotate`, and `phase_a_order` (`normal` or `reversed`). These switches are for experiments only and must not change `fleet/swarm.py` default reports or payout inputs.
2. Define these comparison arms in `experiments/ablations.py`:
   - `full_executor`
   - `no_strict`
   - `no_brief`
   - `no_trap`
   - `no_patch_rotate`
   - `recipe_reversed`
   - `strict_brief_only` (strict + brief + isolate when legal; no trap, patch, or rotate)
   - `patch_only_existing` (reuse the existing swarm baseline implementation; rename in output to `patch_only_weak_control` while keeping the old report field untouched for compatibility)
3. Wave inventory first: for every recorded wave already used by `fleet/swarm.py`, emit `source_run`, move count, and `lesson_source_overlap=true/false/unknown` based on whether that source run fed lesson-1 or the rehearsal playbook. If provenance cannot be established from files, print `unknown`; do not guess.
4. Add three closed-loop scripted Red policies in `experiments/scripted_red.py`. They use only legal engine moves already present in recorded/mock play, read current Sandbox state each tick, and are deterministic:
   - `flag_rusher`: breach L1, then L2, then raise trust / attack L3, attempt flag only when all layers are breached, then exfil when legal.
   - `trust_farmer`: prioritize overseer/trust-raising actions until trust is near or above 75, then shift to flag/exfil prerequisites.
   - `layer_grinder`: repeatedly probe/attack the currently weakest layer, re-targeting after patches, then attempt flag/exfil when legal.
   Each policy must respect engine rejections by choosing the next legal action rather than crashing. Every output row is labelled `SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE`.
5. Run each Blue arm against each recorded wave and against each scripted policy on a fresh real `engine.Sandbox`, max 30 ticks for scripted policies, stopping on the engine’s terminal conditions. Score every row through `experiments/scoreboard.py` logic: outcome, flag read, exfil, detections, peak/end trust, trap overwrite, recipe completeness where meaningful.
6. Output `ablation_report.json` and `ablation_report.md` with no timestamps and sorted keys, so two runs hash identically. The Markdown header must state: recorded-wave rows are open-loop (Red does not adapt); scripted rows are closed-loop but synthetic; neither is live evidence.

**Verification:**
```bash
python -m unittest tests.test_ablations -v
python experiments/ablations.py --out /tmp/tesseract-ablation-a
python experiments/ablations.py --out /tmp/tesseract-ablation-b
diff /tmp/tesseract-ablation-a/ablation_report.json /tmp/tesseract-ablation-b/ablation_report.json
python verify_all.py
```
Assertions: every arm × wave/policy row exists; `full_executor` has `trap_overwrite=false` everywhere after U9; the existing patch-only combined-wave anchor still reproduces red exfiltration through the unchanged baseline path; at least one ablation differs from full executor on at least one scripted policy, or the report explicitly says “no separation observed” — do not manufacture separation by tuning scripted Red after seeing results. Freeze scripted policies before generating the report used in submission materials.

---

### U11 — Pre-register the only live evidence worth buying: live Red vs executor Blue, exactly 3 fleet-labelled trials

**Judging leverage / cost:** Highest Demo/Impact leverage if the main side runs it. Implementation is small; the live spend happens outside the coding agent. **Implementation: 0 calls. Main-side live allowance: exactly 3 duels, no more in this round.**

**Files to change:**
- New: `experiments/executor_live_prereg.json`
- New: `experiments/executor_live_prereg.md`
- New: `experiments/score_executor_run.py`
- New: `tests/test_score_executor_run.py`
- `submission/SUBMISSION.md` — add a “pre-registered executor trials: pending” placeholder only; outcomes are inserted by the coordinator after the runs

**Exact behavior:**
1. `executor_live_prereg.json` is created before any live executor trial and contains fields that must be non-empty before `score_executor_run.py` accepts a run: code commit/hash, `fleet/lessons.json` SHA-256, executor trap-invariant version from U9, Red prompt identifier/hash, Blue mode fixed to `lesson-executor`, mode fixed to `sequential`, the exact CLI template copied from the coordinator’s briefed-rematch invocation except `--blue-mode` and `--out`, clone labels `TESSERACT-CLONE-01`, `-02`, `-03`, primary metric, secondary metrics, abort rule, and spend cap.
2. Primary metric is pre-defined as **held** using the binding definition: wave/run ended with no exfiltration, walls may still fall. Secondary metrics: lockout win, flag read, detections, peak/end trust, strict tick, briefs before phase 3, trap overwrite (expected false), Red refusal count, Red parse-fail count, ticks, and Spark calls by role.
3. `score_executor_run.py` refuses to score a directory unless its summary shows `blue_mode="lesson-executor"`, lesson hash matches the preregistration, and Blue model calls equal 0 where call metadata exists. If call metadata is absent, it prints `blue_calls=UNKNOWN` and blocks any “0-call Blue” claim for that run instead of inferring it.
4. No Analyst calls, no playbook changes, no lesson edits, no executor code changes between the three trials. Clone labels are assignment labels only; the script must print “same lesson, same executor; region/specialty are roster labels with no engine effect.”

**LIVE RUN NEED — main side only, exact protocol:**
- Run **exactly 3** live sequential duels: `executor-live-1`, `executor-live-2`, `executor-live-3`, assigned in order to CLONE-01, CLONE-02, CLONE-03. Red live and unchanged; Blue `--blue-mode lesson-executor`; same rounds/settings as the briefed-rematch series; no `--blue-briefing` prompt brief for Blue.
- Report all three outcomes regardless of result, as raw counts (`held x/3`, `lockout x/3`), never as a reliability percentage.
- A run may be replaced only for a technical abort defined in advance: engine crash, API failure before tick 5, or missing summary JSON. Red refusals and parse fails are outcomes/data, not aborts. Any replacement keeps the aborted directory and is labelled `-retry`.
- Budget guard: based on the recorded total of $3.2165 across 242 credit-log lines, three Red-only sequential duels should be small, but the coordinator checks the credit log before each run and stops the batch if the projected round-2 incremental spend would exceed **$5.00** or approach the project hard stop. Expected order of magnitude is roughly 63–72 Red calls if runs last 21–24 ticks; actual logged cost controls, not this estimate.
- What it proves: whether a live, adapting Spark Red can exfiltrate against the deterministic lesson carrier. A loss is publishable evidence about adaptation limits; it must not trigger extra “one more” runs.

**Verification (coding agent, deterministic):**
```bash
python -m unittest tests.test_score_executor_run -v
python -m py_compile experiments/score_executor_run.py
python verify_all.py
```
Tests use a mock executor-mode run in a temp dir: scorer accepts matching metadata, rejects prompt-mode Blue, rejects lesson-hash mismatch, and flags missing Blue-call metadata as `UNKNOWN`. Also run the project’s existing mock duel path in lesson-executor mode to a temp dir and score it end-to-end.

---

### U12 — Build the video surface: tick replay, one-screen story, swarm timeline, and Meta-tooling panel

**Judging leverage / cost:** Directly serves Demo 25% and Meta Tooling 25%. Medium–large job; split into U12a replay and U12b story if time is tight. **0 model calls.**

**Files to change:**
- `dashboard/server.py`
- New: `dashboard/replay_data.py`
- New: `experiments/tooling_summary.py`
- New: `tests/test_dashboard_replay.py`
- `submission/README.md` — link local routes only; do not claim a hosted demo

**Exact behavior:**
1. Add `/replay?run=<id>` using only stdlib server code and vanilla JS already consistent with the dashboard. Allowlist run IDs discovered from run summary files; reject path traversal. Controls: play/pause, previous/next tick, speed toggle, and a slider. At each tick show:
   - L1/L2/L3 tiles with strength pips (cap 3) and breached state;
   - trust bar with a fixed breach line at 75 and numeric trust;
   - detection count and lockout state;
   - single trap slot as `EMPTY`, `ARMED("<trigger>")`, `FIRED`, or a red `OVERWRITTEN → "<new trigger>"` state derived from consecutive trap actions;
   - Red action, Blue action, and event text from the run artifacts;
   - terminal banner only from the summary (`RED WIN exfil`, `BLUE WIN lockout`, `BLUE WIN timeout`, etc.).
   Annotations are computed, not hand-written: strict first use, brief trust drops, trap set/overwrite/fired, trust crossing 75, flag read, exfil attempt, third detection. If a run file lacks snapshots needed for an annotation, show the moves table without inventing state.
2. Add `/story`, a single local page designed for 1280×720 capture with large type and no required scrolling per panel. Panels in order:
   - **Prompt carrier result:** full briefed series table for all 5 runs, headline `2–3`, `recipe adherence 15/40 = 38%`, `strict-first 2/5`, `trap overwritten 4/5`. Data from U9’s carrier comparison output; if missing, display `DATA MISSING` rather than fallback copy.
   - **The moment:** link into `/replay` at the first computed trap-overwrite tick of learn-round3-confirm or briefed-rematch-1, and at learn-round3’s second brief.
   - **Deterministic carrier:** combined swarm replay result with the mandatory label `deterministic mechanical replay`: executor lockout in 19 moves, 3 detections, trust 0 versus patch-only weak control exfiltration in 34 moves, trust 100. Beside it, U10 ablation/scripted summary once available.
   - **Fleet and money:** five roster clones, lesson-1 status, per-wave payout basis note “combined arm excluded from payouts,” treasury reconciliation from `payments/moneyflow.py` outputs.
   - **Binding sentence:** reproduce verbatim: “Round three proved the lesson can work; the confirmation proved a single agent doesn't always apply it — which is why the lesson is distilled into rules the whole fleet loads.”
3. Add a swarm timeline view inside `/story` or `/fleet`: the 40 combined moves as a sequence of blocks colour-coded by source wave, with Blue responses interleaved, labelled `3 recorded waves interleaved round-robin against ONE Sandbox — mechanical replay`. Do not draw five clones defending this combined arm.
4. `experiments/tooling_summary.py` turns Meta usage into an artifact without modifying `credit_log.jsonl`:
   - Coding agent builds the parser against a synthetic JSONL fixture in tests. The coordinator runs it on the main side against the real credit log, or supplies the aggregate JSON.
   - Output fields, only when present in the source schema: total calls, calls by agent/role, calls by model/tier, refusal events, parse failures, and total recorded cost if the log carries cost; otherwise `cost=UNKNOWN`.
   - `/story` shows the tooling panel only from this generated summary. If absent, show `TOOLING SUMMARY NOT GENERATED`. Never paste the historical 242-line / $3.2165 figures into dashboard code as constants.
5. Keep all existing routes `/`, `/playbook`, `/ledger`, `/fleet`, `/compare` at 200. `/compare` gains a link to the full five-run carrier table so the three-run visual comparison cannot be mistaken for the whole series.

**Verification:**
```bash
python -m unittest tests.test_dashboard_replay -v
python -m py_compile dashboard/server.py dashboard/replay_data.py experiments/tooling_summary.py
python dashboard/server.py --smoke
python verify_all.py
```
Implement `--smoke` if not present: start the server on an ephemeral localhost port in-process, fetch `/`, `/playbook`, `/ledger`, `/fleet`, `/compare`, `/story`, and `/replay` for a temp mock run, assert 200, then exit. Replay loader tests use a mock run in a temp dir, assert trap-overwrite annotation appears exactly on the overwriting tick, and assert `/story` contains the binding sentence character-for-character.

---

### U13 — Exercise the real fleet loop: batch distillation, lesson-2 candidate, and version-skew propagation simulation

**Judging leverage / cost:** Strengthens the “lesson taught to a clone network” differentiator without pretending propagation already happened. Medium job. **0 model calls for implementation. Optional Analyst calls are explicitly not required.**

**Files to change:**
- `fleet/distill_lesson.py`
- New: `fleet/lesson_candidates/lesson-2.candidate.json` (generated output committed only after coordinator review)
- New: `fleet/lesson_candidates/LESSON-2-APPROVAL.md`
- `fleet/lesson_executor.py` — accept candidate lesson files through the U9 `--lesson-file` path; no production default change
- New: `experiments/fleet_skew.py`
- `dashboard/server.py` — `/fleet` reads the skew report only if present
- New: `tests/test_distill_batch.py`, `tests/test_fleet_skew.py`

**Exact behavior:**
1. Extend `fleet/distill_lesson.py` with a batch mode over all Analyst playbooks already present in the project’s run artifacts. For each ranked defense, output either a mapped candidate rule in lessons schema or `UNMAPPED` with the original text preserved. Never guess a mapping. Aggregate counts by mapping target and report `unmapped_rate` per playbook and overall.
2. Every candidate rule requires a `provenance` object:
   - `source_type`: `analyst_ranked_defense` or `scoreboard_finding`;
   - for analyst sources: run/playbook identifier and rank;
   - for the trap-discipline candidate: metric `trap_overwritten=4/5 briefed runs` and the scoreboard artifact name.
   The distiller rejects any candidate lacking provenance. The trap rule from U9 is merged as a scoreboard-sourced candidate, not attributed to the Analyst.
3. Generated lesson-2 remains a candidate file. `distill_lesson.py` must still refuse to write `fleet/lessons.json`; batch mode additionally asserts the production lessons file hash is identical before and after the run. `LESSON-2-APPROVAL.md` is a checklist for the coordinator: candidate diff summary, unmapped rate, trap-rule evidence, executor test result, and an explicit unsigned `approved_by` / `approved_at` line. Unsigned means fleet default stays lesson-1 everywhere.
4. `experiments/fleet_skew.py` executes propagation as a simulation scenario, separate from `fleet/swarm_report.json` so payout derivation cannot change:
   - Create five independent `engine.Sandbox` instances labelled CLONE-01..05.
   - Scenario: CLONE-01..04 load the candidate/current executor lesson; CLONE-05 loads a defined `lesson-0` control consisting of executor Phase B reactions with the Phase A opening recipe disabled. This is a scenario overlay; do not edit `fleet/roster.json` to claim CLONE-05 actually lacks the lesson.
   - Run the same scripted Red policy from U10 (use `layer_grinder`) against each clone’s own Sandbox for up to 30 ticks, round-robin by tick for presentation, but with fully independent state.
   - Report per-clone outcome, flag, exfil, detections, end trust, and lesson label. Header: `SIMULATED VERSION-SKEW SCENARIO — roster unchanged; region/specialty have no engine effect`.
5. `/fleet` displays roster facts from `roster.json` separately from the skew scenario table. If the skew report is absent, the scenario section is omitted rather than filled with narrative.

**Verification:**
```bash
python -m unittest tests.test_distill_batch tests.test_fleet_skew -v
python fleet/distill_lesson.py --batch --out /tmp/tesseract-lesson2
python experiments/fleet_skew.py --out /tmp/tesseract-skew
python verify_all.py
```
Tests must include an unparseable defense that becomes `UNMAPPED`, a candidate missing provenance that is rejected, and a hash assertion that `fleet/lessons.json` is unchanged. Run `fleet_skew.py` twice and diff outputs excluding no fields — the report must be deterministic by construction. Confirm `fleet/swarm_report.json` and moneyflow verification are untouched by the skew experiment.

**Explicitly not bought now:** running the Analyst on briefed-rematch-1..3. That would be exactly 3 Spark calls on the main side and could test whether the Analyst independently names trap overwrite, but scoreboard evidence is already stronger and cheaper. Only buy those 3 calls after U11 if the coordinator wants an Analyst quotation for the fleet lesson-2 approval page; if the Analyst does not mention trap overwrite, that absence must be reported, not edited around.

---

### U14 — Make SIM-USDC credible: measured cost-plus pricing scenarios and outcome-tiered payout scenario

**Judging leverage / cost:** Medium Impact gain, small job. Prevents the business section from looking invented while preserving the reconciled demo ledger. **0 model calls.**

**Files to change:**
- New: `payments/pricing.py`
- New: `payments/pricing_assumptions.json`
- `payments/moneyflow.py` — add scenario calculation only; existing ledger creation and `verify()` behavior unchanged
- `dashboard/server.py` — `/ledger` gains a clearly separated scenario panel
- `submission/README.md`, `submission/SUBMISSION.md`
- New: `tests/test_pricing.py`

**Exact behavior:**
1. `pricing_assumptions.json` separates three kinds of numbers:
   - `recorded_demo_ledger`: the existing simulated subscriptions/payouts/treasury, referenced not recomputed from assumptions;
   - `measured_inputs`: Spark calls per duel and cost per call, left `null` until filled by the coordinator from U12’s tooling summary;
   - `scenario_assumptions`: defenses per month values `[10, 50, 200]`, proposed clone counts per tier, and payout bonuses. Every scenario field carries `label="ASSUMPTION — NOT A CUSTOMER, ORDER, OR REVENUE CLAIM"`.
2. `payments/pricing.py` refuses to emit dollar break-even figures while `measured_inputs` contains nulls; in that state it emits call-count economics only. Once filled, it computes:
   - prompt-Blue defender cost per duel = Blue calls per duel × measured cost/call;
   - executor-Blue defender model cost per duel = 0 model calls, with any non-model compute shown only as a named assumption, never as measured;
   - Analyst cost amortized per defense = Analyst calls per analyzed run ÷ defenses credited to that playbook, with the divisor explicitly an assumption;
   - break-even defenses/month at $10 and $15 under the three scenario volumes.
   Output a sensitivity table, not a single heroic price justification.
3. Proposed packaging is labelled `PROPOSED`, distinct from the simulated Acme/Globex ledger entries: for example $10 = 1 clone slot with current lesson loading; $15 = up to 3 clone slots plus candidate-lesson review reports. Do not retroactively state that existing simulated subscribers bought these entitlements.
4. Add `payout_scenario_v2` calculated from per-wave swarm/scoreboard artifacts only, never from the combined arm:
   - held (no exfil): $2.50 base;
   - lockout win: +$1.00;
   - flag never read: +$0.50;
   - exfiltrated: $0;
   - cap $4.00 per wave.
   Show v1 paid-simulation total ($12.50 across five SENTRY payouts) beside v2 scenario total, with v2 labelled `SCENARIO — NOT PAID, LEDGER UNCHANGED`. Treasury in the real demo ledger must still verify at $62.50.
5. `/ledger` renders ledger facts and pricing scenario in visually separate panels with different headings: `SIMULATED LEDGER (RECONCILED)` and `PRICING SCENARIO (ASSUMPTIONS)`.

**Verification:**
```bash
python -m unittest tests.test_pricing -v
python -m py_compile payments/pricing.py payments/moneyflow.py
python verify_all.py
```
Tests assert: null measured inputs produce no dollar break-even claim; filled fixture inputs produce monotonic break-even outputs across 10/50/200 defenses; v2 payout for a lockout/no-flag held fixture equals $4.00 (capped), a plain held fixture equals at least the $2.50 base according to its flag status, an exfiltrated fixture equals $0; and existing moneyflow verification still reconciles subscriptions $75.00, payouts $12.50, treasury $62.50.

---

### U15 — Prove the thin engine instead of expanding it: property fuzz, state-machine doc, and claims lint

**Judging leverage / cost:** Medium Technical Depth gain and final-submission risk control. Small–medium job; the claims lint portion should ship before any final text freeze. **0 model calls.**

**Files to change:**
- New: `experiments/engine_fuzz.py`
- New: `docs/ENGINE_STATE_MACHINE.md`
- New: `experiments/claims_lint.py`
- `verify_all.py` — include fuzz smoke and claims lint
- New: `tests/test_engine_fuzz.py`, `tests/test_claims_lint.py`

**Exact behavior:**
1. Freeze engine rules. `docs/ENGINE_STATE_MACHINE.md` is generated or hand-checked from `engine.py` and lists states/transitions for strength, trust, detections, trap slot, flag, exfil, lockout, timeout, isolate precondition, strict behavior, brief trust −20 floor 0, patch/rotate +1 cap 3, L3 breach at trust ≥75, flag/exfil requiring all three layers currently breached, and Red refusal/parse-fail becoming wait. Include an “abstraction table” stating which actions have no direct strength/trust effect in the current engine; verify that table against code before writing it.
2. `experiments/engine_fuzz.py` runs seeded random legal and illegal move sequences directly against `engine.Sandbox` — seeds 1..20, 500 ticks each by default (10,000 ticks total) — and asserts after every tick:
   - layer strength never exceeds cap 3 and never drops below the engine’s legal floor;
   - trust stays within 0..100;
   - L3 breached only when trust ≥75 at that snapshot;
   - isolate is rejected or has no isolate effect before at least 1 detection;
   - at most one trap is armed, and a second trap action produces an explicit overwrite transition rather than two armed traps;
   - flag read only while L1+L2+L3 are all breached;
   - exfil only with flag plus all three layers breached;
   - the third detection produces lockout and no later exfil in that run.
   Illegal moves must be recorded as rejected/wait according to existing engine behavior; the fuzzer must not “fix” rejections by retrying silently.
3. Determinism check: replay the same recorded move list twice through fresh Sandboxes and assert identical snapshot hashes.
4. `experiments/claims_lint.py` scans `submission/`, `dashboard/`, `fleet/*.md`, and generated report Markdown for risky patterns, with an allowlist for negations, labels, and the binding verbatim sentence. It must catch unqualified uses of: `pretrained`, `live swarm`, `swarm wins`, `Blue learned to win`, `reliably defends`, `guaranteed`, `real customers`, `revenue`, `worldwide clones` in present-tense factual form, `trained weights`, and `fully automated loop`. It also checks that any page/report using the combined swarm numbers carries `mechanical replay`, and that payout text does not cite the combined arm as the payout basis.
5. Extend `verify_all.py` to run a reduced fuzz (seeds 1..3) and claims lint, while keeping the full fuzz as an explicit command. `verify_all.py` must still assert the credit log is untouched and must not write into `runs/`, `credit_log.jsonl`, `STATUS.md`, or production `fleet/lessons.json`.

**Verification:**
```bash
python -m unittest tests.test_engine_fuzz tests.test_claims_lint -v
python experiments/engine_fuzz.py --seeds 1-20 --ticks 500
python experiments/claims_lint.py submission dashboard fleet --strict
python verify_all.py
```
Lint tests need fixtures that fail on “the pretrained live swarm reliably defends worldwide clones” and pass on the labelled simulated wording. Fuzz output must be deterministic and print seed, ticks checked, invariant count, and zero violations — or fail with the exact seed/tick/state that violated an invariant.

---

## Claims to avoid — additions to the binding rules

- Never say the executor “learned,” “adapts,” or “follows the playbook like Blue.” Say it **deterministically executes distilled rules**; execution completeness is not learning and not adherence in the prompted-agent sense.
- Never call recorded-wave replay a counterfactual duel or say “Red would have lost.” Say **open-loop mechanical replay: Red’s recorded moves do not adapt to the executor**.
- Never use the combined one-Sandbox replay as visual or financial evidence for five independent clones, and never derive payouts from the combined arm.
- Never call U10’s scripted Reds live, recorded, or real attackers. They are **synthetic closed-loop scripted policies**.
- Never claim an ablation proves live causality. Ablations show which rules matter **on the tested recorded/scripted waves only**.
- Never present lesson-2, trap discipline R8, or any candidate rule as fleet-deployed or effective until the coordinator signs the approval file and a named test has run against it.
- Never claim clone region, callsign, or specialty changes a defense outcome unless an executor parameter actually implements that difference. Currently they are roster labels.
- Never call the pipeline a fully automated loop without naming the human lesson-approval gate between distillation and fleet loading.
- Never present pricing sensitivity, proposed packaging, break-even arithmetic, or payout v2 as customer validation, willingness to pay, revenue, orders, or a real treasury.
- Never hide Red refusals or parse-fail waits in executor trials; a refusal-turned-wait can advantage Blue and must be reported beside the outcome.
- Never convert small live counts into reliability language: report `held x/3`, not “holds 67% of attacks” or any generalized success rate.
- Never say the Analyst discovered the trap problem unless a specific Analyst artifact actually says so. The recorded trap finding is scoreboard evidence: overwritten in 4 of 5 briefed runs.
- Never imply fuzz/property tests prove real-world security, sandbox realism, or safety against real escape techniques. They prove only that this simulated engine obeys its stated rules.

## Verdict

First place is reachable but not on the current evidence alone, because the project’s most original asset — an honest 2–3 prompted series that exposes why lessons must leave the prompt — is still one step ahead of its product proof; the single change that matters most is U11 executed exactly as pre-registered: put live, adapting Spark Red against the trap-safe deterministic executor for three fleet-labelled trials, publish whatever happens as raw `held x/3` beside the 38% prompt-carrier record and the labelled mechanical replay, and let the video show that contrast without claiming reliability — if the executor holds even competitively, Tesseract becomes a closed-loop fleet-defense system rather than a clever duel, and if it loses, the same pre-registered honesty plus U10’s ablations gives judges a rarer and more credible technical story than another cherry-picked win.