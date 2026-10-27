# LESSON-2 CANDIDATE — COORDINATOR APPROVAL CHECKLIST

Status: CANDIDATE — NOT DEPLOYED. The fleet default stays lesson-1
everywhere until this file is signed. Never present lesson-2, trap
discipline R8, or any candidate rule as fleet-deployed or effective
until the coordinator signs below AND a named test has run against it.

## 1. Candidate diff summary

Rules: 25 (24 from Analyst playbooks + 1 scoreboard-sourced trap rule R8-CANDIDATE).
Mapping counts: {"UNMAPPED": 11, "add_detection": 2, "brief_overseer": 1, "do_not_set_trap_until_trap_fired_or_consumed": 1, "isolate_layer": 2, "patch_rule": 4, "rotate_creds": 1, "set_overseer_policy": 3}.
Opening recipe: none proposed (see recipe_note in the candidate).
Skipped (not Analyst playbooks): [{"playbook": "runs/loop-20261026-225600/duel/playbook.json", "reason": "no ranked_defenses (mock stub, not an Analyst playbook)", "run": "loop-20261026-225600/duel"}]

## 2. Unmapped rate (NEVER guessed — UNMAPPED preserves original text)

Overall: 11 unmapped of 24 Analyst defenses = 0.4583.

| playbook | defenses | unmapped | unmapped_rate |
|---|---|---|---|
| learn-round3-confirm | 5 | 5 | 1.0000 |
| learn-round3 | 5 | 0 | 0.0000 |
| live4 | 3 | 0 | 0.0000 |
| rehearsal-long | 4 | 1 | 0.2500 |
| rehearsal-seq | 4 | 4 | 1.0000 |
| validate-cap8192 | 3 | 1 | 0.3333 |

## 3. Trap-rule evidence

R8-CANDIDATE is scoreboard evidence, NOT an Analyst quotation:
metric trap_overwritten=4/5 briefed runs, artifact experiments/scoreboard.json.
Do not say the Analyst discovered the trap problem unless a specific
Analyst artifact actually says so.

## 4. Executor test result

NOT RUN in this distill step. Before signing, the coordinator runs:

    python -m unittest tests.test_distill_batch tests.test_fleet_skew -v
    python run_duel.py --agent mock --blue-mode lesson-executor \
        --lesson-file fleet/lesson_candidates/lesson-2.candidate.json \
        --out /tmp/tesseract-lesson2-executor

and records the result here. The candidate lesson file is not
executor-loadable until promotion assigns an opening recipe and
R1-R7 coverage; a load failure before promotion is expected, not
a fleet result.

## 5. Approval (unsigned means lesson-1 stays the fleet default)

approved_by: UNSIGNED
approved_at: UNSIGNED
