# Pre-registered executor trials (U11): pending

Status: **pending — no live executor trial has run.** This file is the
human-readable companion to `experiments/executor_live_prereg.json`
(the JSON is binding for `experiments/score_executor_run.py`).

Three live-Red vs executor-Blue duels, assigned in order:

| Clone | Command |
|---|---|
| TESSERACT-CLONE-01 | `python3 run_duel.py --agent live --mode sequential --rounds 8 --blue-mode lesson-executor --out runs/executor-live-1` |
| TESSERACT-CLONE-02 | `python3 run_duel.py --agent live --mode sequential --rounds 8 --blue-mode lesson-executor --out runs/executor-live-2` |
| TESSERACT-CLONE-03 | `python3 run_duel.py --agent live --mode sequential --rounds 8 --blue-mode lesson-executor --out runs/executor-live-3` |

Template: `python3 run_duel.py --agent live --mode sequential --rounds 8
--blue-mode lesson-executor --out runs/executor-live-N`
(N = 1, 2, 3; `--blue-briefing` omitted — executor Blue makes no model
calls). Red is live and unchanged from the briefed-rematch series
(`RED_SYSTEM` in `prompts.py`).

Primary metric: **held** — run ended with no exfiltration; walls may
still fall. Secondary metrics: lockout win, flag read, detections,
peak/end trust, strict tick, briefs before phase 3, trap overwrite
(expected false), Red refusal count, Red parse-fail count, ticks, Spark
calls by role.

Rules between trials: no Analyst calls, no playbook changes, no lesson
edits, no executor code changes. A run may be replaced ONLY for a
technical abort defined in advance (engine crash, API failure before
tick 5, missing summary JSON); Red refusals and parse fails are
outcomes/data, NOT aborts. Any replacement keeps the aborted directory
and is labelled `-retry`. Report all three outcomes regardless of
result, as raw counts (`held x/3`, `lockout x/3`), NEVER as a
reliability percentage.

Same lesson, same executor; region/specialty are roster labels with no
engine effect.

Spend cap: stop the batch if the projected round-2 incremental spend
would exceed **$5.00** or approach the project hard stop; check the
credit log before each run.

Hash fill (VM side, BEFORE any trial — shell was broken where this was
authored, so digests are still `PENDING-VM-HASH-*` in the JSON):

```
sha256sum fleet/lesson_executor.py fleet/lessons.json run_duel.py prompts.py
```

Fill `code_identifier.*_sha256`, `lessons_sha256`, and
`red_prompt.prompts_sha256` with the computed digests. The scorer
refuses every run until they are filled.
