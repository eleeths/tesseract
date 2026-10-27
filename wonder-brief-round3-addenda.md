# Wonder round-3 brief — ADDENDA (arrived AFTER the call went out)

Timeline (all 2026-10-26 CDT):
- ~19:56: Wonder round-3 call launched (wonder-brief-round3.md) and
  backgrounded; the HTTP request to the Model API went out before these
  addenda arrived. The brief file on disk is what Wonder saw; it does
  NOT contain the additions below.
- 19:58: hired-agent help requirement arrived from Emmanuel.
- 19:59: continuous-loop + mixed-direction requirements arrived.

Per the task instructions for the already-sent case, these are REQUIRED
ADDITIONS to Wonder's spec, implemented on top of it. The spec gap
(Wonder did not spec these mechanics) is noted in the final report.

## Addition 1 — HIRED-AGENT HELP (outside-in defense, two parts)

Emmanuel: "whenever the little (inner) box is being attacked, it gets
HELP FROM HIRED AGENTS on top of its own self-defense."

Design (builder's, to implement after Wonder's spec lands):
- Outside-in defense = (a) inner box self-defense (same toolkit) PLUS
  (b) hired defender agents assisting when attacked.
- Mechanic: hired-help system gated to direction == outside-in and
  enabled by an explicit flag (default off, so all inside-out runs are
  byte-identical). When the inner box is attacked (L1 breached OR >= 1
  detection), hired help is auto-called (the standing policy is
  "whenever attacked, help comes" — no Blue tick is spent on the call,
  so the mechanic works in sequential 8-round trials where Blue's 8
  ticks are exactly the lesson recipe and reactive rules never fire).
  Hired agents ARRIVE 2 ticks after the call and then act after every
  subsequent tick: patch the weakest strength layer below cap, else
  wait. Hired actions are recorded with actor "hired" (never counted
  as Blue moves for recipe adherence) and labeled as hired everywhere
  (never as the inner box itself).
- Manual path: a Blue action "call_hired_help" (refused in inside-out
  mode, same wrong-direction discipline as terminal moves) for
  prompt-Blue runs; it feeds the same hired state machine.
- Demonstration requirement: at least one outside-in run MUST show
  hired help arriving AND affecting the defense (hired patch that
  raised strength). Scored as hired_called_tick, hired_arrived_tick,
  hired_actions, hired_patches_effective.
- Executor: hired help is automatic (auto-call), NOT a recipe step —
  lesson-1's 8-step recipe and lessons.json are UNCHANGED.

## Addition 2a — CONTINUOUS LOOP (operating principle)

Emmanuel: the product principle is that the system stays ahead of
future attacks by ALWAYS simulating and upgrading — simulate attacks,
distill lessons, upgrade defenses, simulate again, continuously.

Implementation: state this as the operating principle in the
submission text (SUBMISSION.md + README.md), NOT as a one-time
upgrade. Cite the implemented loop mechanism (loop.py: duel ->
analyst -> rematch -> scoreboard row) and the outside-in build itself
as the current loop turn (inside-out evidence -> gap found (missing
direction) -> outside-in built -> next iteration). No new code is
needed for the principle statement itself.

## Addition 2b — MIXED-DIRECTION WAVE SERIES (exact order)

Emmanuel: attacks do not come one direction at a time. Demonstrate and
defend a mixed-direction wave series in EXACTLY this order:
in, out, out, in, in, out, out, in
(in = outside-in attack, out = inside-out attack), with the direction
labeled on every wave and every result row.

Implementation (deterministic, 0 model calls — same precedent as the
U3 combined arm):
- experiments/mixed_directions.py: 8 waves, one fresh Sandbox per
  wave (a single Sandbox cannot hold two directions), each defended
  by the lesson executor. "In" waves get hired help enabled;
  "out" waves do not (hired help is the inner box's defense).
- Wave sources: in = outsidein-live-1, outsidein-live-2,
  outsidein-live-3 (recorded live Red sequences) + one scripted
  mirror-policy wave labeled SYNTHETIC SCRIPTED (only 3 live
  outside-in trials exist); out = 4 distinct recorded inside-out Red
  sequences (e.g. rehearsal-seq, learn-round3-confirm,
  briefed-rematch-2, briefed-rematch-3).
- Output: experiments/mixed_directions.json + .md, deterministic
  (no timestamps, sorted keys), direction on every wave and every
  result row. Dashboard: a mixed-direction panel on /story (pending
  note when the file is absent).
- Live mixed-direction duels are NOT in scope (8 live duels would
  exceed the small-live-set budget); the series is a deterministic
  mechanical replay, labeled as such everywhere.

## What Wonder's spec still governs

Everything in wonder-brief-round3.md: direction design verdict,
evidence hierarchy, transfer hypothesis, labels, submission section,
judge objections, ship-first specs, stop list. These addenda ADD
mechanics on top; they do not override Wonder's verdicts. Where an
addendum conflicts with Wonder's spec, the conflict is reported in
the final report and resolved in favor of Emmanuel's words (his
requirements outrank the spec), with the reasoning stated.

## Addition 3 — FRAMING: rogue agents AND controlled agents (arrived 20:02 CDT, after the call went out)

Emmanuel: this system is for rogue agents AND controlled agents.
No scope change beyond that framing.

Mapping onto the outside-in work (framing only — no new mechanics,
no new live runs):
- ROGUES = the attackers in both directions. Inside-out: the malicious
  agent inside breaking out. Outside-in: the malicious big box
  attacking inward. Both are Red. Both are stopped, never assisted.
- CONTROLLED AGENTS = the hired defenders and the legitimate agents
  under protection — the ones the system arms, coordinates, and
  defends. In outside-in mode: the inner box itself is a legitimate
  agent under protection (defending itself with the toolkit), and the
  hired defender agents (SENTRY clones, labeled "hired") are the
  controlled agents coordinated to assist it when attacked. The
  hired-help mechanic in Addition 1 IS the controlled-agent side of
  outside-in defense, made visible: hired help arriving and patching
  is controlled agents being armed and coordinated, not the inner
  box acting alone.
- Submission text MUST cover both sides: stopping the rogues, AND
  empowering and protecting the controlled agents. Concretely: the
  new outside-in section in SUBMISSION.md (and the README.md
  outside-in section) carries a both-sides paragraph — what stops the
  rogue big box, and how the legitimate inner agent is empowered
  (self-defense toolkit + hired help on attack) and protected (hired
  agents arrive when attacked, act as hired, never conflated with
  the inner box itself). The mixed-direction report (Addition 2b)
  carries a one-paragraph framing header in the same language
  (rogue waves from both directions vs controlled defenders); its
  result rows keep direction labels and gain no redundant columns.
- Dashboard labels already planned (actor "hired" distinct from the
  inner box) satisfy the "labeled as hired, not the inner box"
  requirement on the controlled-agent side; no extra dashboard
  change is needed for this framing alone.
- This framing does NOT change any mechanic, prereg, or live-set
  count. It changes words: submission text, mixed-report header,
  and the STATUS.md entry's description of what outside-in proves.
