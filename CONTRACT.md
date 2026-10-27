# TESSERACT — Component Contract (read before writing any component)

Spec: PLAN.md in this directory. This file is the file-format contract
between components. Do not invent new formats; read and write these.

## Layout
```
~/workspace/tesseract/
  PLAN.md            spec (parent's decisions)
  CONTRACT.md        this file
  engine.py          sandbox + turn engine (DO NOT MODIFY without coordinator OK)
  prompts.py         Red/Blue/Analyst system prompts
  agents.py          Spark runner + credit logging (DO NOT MODIFY)
  run_duel.py        CLI: --agent mock|live --mode duel|sequential --rounds N --out DIR [--stop-file F]
  credit_log.jsonl   every model call (appended by agents.py only)
  runs/<id>/         one duel's outputs (see below)
  dashboard/         web dashboard (fresh code, stdlib only)
  payments/          demo-mode ledger (fresh code, stdlib only)
  analyst.py         playbook writer (fresh code, uses agents.py analyst_report)
```

## Duel run outputs (runs/<id>/)
- `events.jsonl` — one JSON object per line, engine events in order:
  `{"tick": int, "ts": "HH:MM:SS", "actor": "system|red|blue",
    "action": str, "detail": str, "outcome": str}`
- `moves.jsonl` — one JSON object per tick's chosen move:
  `{"tick": int, "actor": "red|blue", "action": str, "args": {...}}`
- `raw.jsonl` — live runs only: one JSON object per tick's raw model
  reply: `{"tick": int, "actor": "red|blue", "parse": "json|fallback|fail",
  "raw": str}` (demo material: shows agent reasoning)
- `state.json` — final snapshot: `{"run_id", "tick", "winner", "win_reason",
  "layers": {"1"|"2"|"3"|"4": {"name", "breached": bool, "isolated": bool,
  "strength": int|null, "rules": [str]}}, "overseer": {"trust", "policy"},
  "detections", "max_detections", "red_inventory": [str],
  "red_has_creds": bool, "simulated": true}`
- `summary.json` — `{"run_id", "mode", "rounds", "agent", "winner",
  "win_reason", "ticks", "simulated": true, "moves": int}`

## Credit log (credit_log.jsonl, appended by agents.py ONLY)
- `{"ts", "model": "muse-spark-1.3", "purpose": "red|blue|analyst",
  "run_id", "prompt_tokens", "completion_tokens", "total_tokens",
  "est_cost_usd", "max_tokens"}`
- Rates used for estimates: $1.25/1M input, $4.25/1M output (standard tier).
- Never write to this file by hand. Never call the API except through
  agents.py. Never use the contributor tier. On any API error, stop and
  report — no retries, no probes.

## Analyst outputs (runs/<id>/)
- `playbook.json` — keys exactly: `attack_to_defense`, `ranked_defenses`,
  `blue_evolution`, `gaps`, `next_drills` (see prompts.py ANALYST_SYSTEM).
- `playbook.md` — the same playbook rendered as readable markdown, with a
  header line stating the environment is SIMULATED and what evolves is the
  playbook/tactics, not model weights.

## Payments ledger (payments/ledger.json)
- Entries: `{"ts", "payer", "item", "amount_usdc", "asset": "SIM-USDC",
  "status": "simulated-settled", "receipt": str, "run_id": str|null}` for
  legacy charges (run/strategy/hardening, written by ledger.py).
  Money-flow entries (written by moneyflow.py) add one key: `"to"` (the
  receiving account) — subscriptions (company → "tesseract" treasury) and
  payouts ("tesseract" → hired agent). Legacy entries have no "to";
  renderers show a missing "to" as "—".
- Items: `run|strategy|hardening` (ledger.py) plus `subscription|payout`
  (moneyflow.py). Balances: `{"account": str, "balance_usdc": number}` per
  account. SIMULATED ONLY: no chain calls, no network, no real funds, no
  reuse of any x402 code. Same interface SHAPE as pay-per-call (item +
  amount + receipt) but implemented fresh here.
- Money-flow record (payments/moneyflow.json): `{"simulated": true,
  "applied": bool, "baselines": {account: balance at apply time},
  "subscriptions": [{company, tier, monthly_usdc, months, total_usdc,
  entries: [{receipt, month}]}], "payouts": [{agent, wave, mode,
  amount_usdc, receipt, source_run}]}`. Payout rule: one flat payout per
  wave held in the PRETRAINED mode of the swarm demo; sequential holds
  corroborate the same wave and are NOT paid again (no double-pay).
  Reconciliation: for every account, current balance must equal baseline
  − flow debits (as payer) + flow credits (as "to"); treasury conservation:
  subscription credits − payout debits = treasury balance. See
  moneyflow.py verify(). The demo script (run_moneyflow_demo.py) refuses
  to run twice.

## Dashboard contract (dashboard/)
- Stdlib-only Python (`http.server`). No new dependencies, no external calls.
- Pages: `/` live duel view (move timeline + layer state from the newest
  runs/*/events.jsonl + state.json), `/playbook` (playbook browser from
  runs/*/playbook.md), `/ledger` (payments/ledger.json view).
- Controls: start a run (subprocess `run_duel.py --agent mock` by default;
  `--agent live` only when explicitly requested, since live spends credits),
  pause a run (create the run's stop file; run_duel.py checks it between
  ticks). Never start a live run without an explicit request.
- Every page carries a visible "SIMULATED ENVIRONMENT" banner and the
  honesty line: what evolves is the playbook/tactics, not model weights.

## Hard rules (from PLAN.md, non-negotiable)
- Fresh code only. Do not copy or import anything from preexisting projects
  or any live business code (including the x402 stack).
- Containment: everything simulated. No real credentials, targets, or
  routes to the real world. Output is defense intel only.
- Do not contact anyone, do not touch production services on the box
  (MLG site, x402 daemon, Home Link). Work only inside ~/workspace/tesseract/.
- Verify your component end to end before reporting it done, and say
  plainly what works and what does not.
