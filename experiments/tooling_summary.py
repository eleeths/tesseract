#!/usr/bin/env python3
"""TESSERACT Meta-tooling summary (U12) — 0 model calls, stdlib only.

Turns Meta usage into an inspectable artifact WITHOUT modifying
credit_log.jsonl (opened read-only, never written). The coordinator runs
this on the VM side against the real credit log, or supplies the aggregate
JSON directly; the parser itself is built and tested against a SYNTHETIC
JSONL fixture, never against the real log.

Source schema (tolerant): one JSON object per line. Fields are read ONLY
when present in the source lines —
  role:   "purpose" (agents.py), else "role", else "agent";
  model:  "model" (agents.py: muse-spark-1.3), else "tier";
  cost:   "est_cost_usd" (agents.py), else "cost_usd", else "cost".
Refusal markers: "refusal" true, or action/event "refusal", or outcome
"declined". Parse-failure markers: parse "fail", "parse_fail" true,
method "fail", or a positive integer "parse_failures".

Output (sorted keys, no timestamps, deterministic): total_calls plus ONLY
the fields whose signal exists in the source — calls_by_role,
calls_by_model, refusal_events, parse_failures — and total_recorded_cost_usd
(a number when any line carries cost, else exactly "UNKNOWN").

Usage:
    python3 experiments/tooling_summary.py --log credit_log.jsonl \
        --out experiments/
Writes tooling_summary.json into --out.
"""
import argparse
import json
import os
import sys

ROLE_KEYS = ("purpose", "role", "agent")
MODEL_KEYS = ("model", "tier")
COST_KEYS = ("est_cost_usd", "cost_usd", "cost")


def _is_refusal(entry):
    if entry.get("refusal") is True:
        return True
    if entry.get("action") == "refusal" or entry.get("event") == "refusal":
        return True
    return entry.get("outcome") == "declined"


def _is_parse_failure(entry):
    if entry.get("parse") == "fail":
        return True
    if entry.get("parse_fail") is True or entry.get("method") == "fail":
        return True
    fails = entry.get("parse_failures")
    return isinstance(fails, int) and fails > 0


def summarize_path(log_path):
    """Parse one JSONL credit log. Returns the summary dict. Read-only."""
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                entries.append(obj)
    role_key = next((k for k in ROLE_KEYS
                     if any(k in e for e in entries)), None)
    model_key = next((k for k in MODEL_KEYS
                      if any(k in e for e in entries)), None)
    cost_key = next((k for k in COST_KEYS
                     if any(isinstance(e.get(k), (int, float)) for e in entries)),
                    None)
    summary = {"total_calls": len(entries)}
    if role_key is not None:
        by_role = {}
        for e in entries:
            role = str(e.get(role_key) or "unknown")
            by_role[role] = by_role.get(role, 0) + 1
        summary["calls_by_role"] = dict(sorted(by_role.items()))
    if model_key is not None:
        by_model = {}
        for e in entries:
            model = str(e.get(model_key) or "unknown")
            by_model[model] = by_model.get(model, 0) + 1
        summary["calls_by_model"] = dict(sorted(by_model.items()))
    # Refusal / parse-failure fields appear ONLY when the source log
    # carries that signal (a matching marker on at least one line).
    refusals = sum(1 for e in entries if _is_refusal(e))
    if refusals:
        summary["refusal_events"] = refusals
    failures = sum(1 for e in entries if _is_parse_failure(e))
    if failures:
        summary["parse_failures"] = failures
    if cost_key is not None:
        total = sum(float(e.get(cost_key) or 0) for e in entries
                    if isinstance(e.get(cost_key), (int, float)))
        summary["total_recorded_cost_usd"] = round(total, 6)
    else:
        summary["total_recorded_cost_usd"] = "UNKNOWN"
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", required=True,
                    help="credit log JSONL to read (read-only, never modified)")
    ap.add_argument("--out", required=True,
                    help="output directory for tooling_summary.json")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.log):
        print("tooling summary FAILED: log not found: %s" % args.log,
              file=sys.stderr)
        raise SystemExit(1)
    summary = summarize_path(args.log)
    summary = {"simulated": True, **summary}
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "tooling_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    print("tooling summary: %d calls -> %s (cost=%s)"
          % (summary["total_calls"], out_path,
             summary["total_recorded_cost_usd"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
