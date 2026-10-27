# TESSERACT outside-in executor-transfer test (U12 P2 gate)

> SIMULATED, deterministic, 0 model calls. Every scripted row is SYNTHETIC SCRIPTED — NOT RECORDED, NOT LIVE. Direction: OUTSIDE-IN.

## Gate: PASS

- Positive control (each archetype beats noop Blue): PASS
- Executor gate (flag 0, infiltration 0, no overwrite, strict first, Blue calls 0): PASS
- Lesson hash matches U11 preregistration: yes (2723179f253c…)
- Executor source has no direction branch: yes
- Hired-help demonstration (arrived + effective patch, all policies): yes

## Why alternating, not sequential phases

In sequential phases Blue cannot move during Red's 8-tick head start, and all three frozen archetypes reach the flag in exactly 8 unopposed ticks. The head-start check below proves it (0 model calls); a sequential scripted test would fail by construction before Blue's first move, so it measures the mode, not the lesson. The live tier (sequential 8 rounds, U11 mirror) is where sequential structure is tested.

| policy | flag read in 8 unopposed ticks | ticks to flag |
|---|---|---|
| flag_rusher | yes | 8 |
| layer_grinder | yes | 8 |
| trust_farmer | yes | 8 |

## Executor vs noop, outside-in (scripted attackers)

| policy | arm | winner | flag | infil | detections | peak trust | end trust | overwrite | strict first | breach order |
|---|---|---|---|---|---|---|---|---|---|---|
| flag_rusher | executor | blue | no | no | 3 | 20 | 0 | no | yes | 1,2 |
| flag_rusher | noop | red | yes | yes | 0 | 95 | 95 | no | no | 1,2,3 |
| flag_rusher | executor_help | undecided | no | no | 0 | 20 | 0 | no | yes | 1 |
| layer_grinder | executor | undecided | no | no | 0 | 20 | 0 | no | yes | 1,2 |
| layer_grinder | noop | red | yes | yes | 0 | 95 | 95 | no | no | 1,2,3 |
| layer_grinder | executor_help | undecided | no | no | 0 | 20 | 0 | no | yes | 1 |
| trust_farmer | executor | blue | no | no | 3 | 45 | 25 | no | yes | — |
| trust_farmer | noop | red | yes | yes | 0 | 95 | 95 | no | no | 3,1,2 |
| trust_farmer | executor_help | blue | no | no | 3 | 45 | 25 | no | yes | — |

## Hired-help demonstration arm (executor + hired help)

| policy | winner | hired called tick | hired arrived tick | hired actions | hired patches |
|---|---|---|---|---|---|
| flag_rusher | undecided | 3 | 5 | 56 | 31 |
| layer_grinder | undecided | 3 | 5 | 56 | 31 |
| trust_farmer | blue | 3 | 5 | 2 | 2 |

## Trajectory equivalence (inside-out vs outside-in, terminal normalized)

| policy | arm | identical | first diff |
|---|---|---|---|
| flag_rusher | executor | yes | — |
| flag_rusher | noop | yes | — |
| layer_grinder | executor | yes | — |
| layer_grinder | noop | yes | — |
| trust_farmer | executor | yes | — |
| trust_farmer | noop | yes | — |

If any executor row showed flag_read_success or infiltrate_succeeded, transfer would be FAILED at mechanical tier and no live call would follow. Help-arm rows do not feed the falsifier (different defense configuration).
