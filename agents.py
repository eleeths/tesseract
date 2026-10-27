#!/usr/bin/env python3
"""Agent runner for TESSERACT — fresh code, written for the hackathon.

Composes one prompt per turn (system prompt + sandbox state + instruction),
calls Muse Spark via the Meta Model API helper, parses exactly one JSON
action from the reply, and logs every call (tokens + estimated cost) to
credit_log.jsonl. Standard tier only (muse-spark-1.3); never the
contributor tier (it trains on prompts).

If the API answers 402 (billing) or any error, the call is logged and the
run stops — no retries, no probes, no card spend. Free $150 credits only.
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# Helper path override for judge reproducibility (U5): set
# TESSERACT_META_HELPER to a different meta_api.py location. Default is
# unchanged — the connector helper this build was verified against.
HELPER = os.environ.get(
    "TESSERACT_META_HELPER",
    os.path.expanduser(
        "~/workspace/custom-connectors/custom.meta-model-api/bin/meta_api.py"
    ),
)
MODEL = "muse-spark-1.3"
# Published standard-tier list rates (Meta Model API, multiple public
# summaries agree): $1.25/1M input, $4.25/1M output. Estimates use
# uncached input rates; the helper response carries no cache breakdown.
RATE_IN = 1.25 / 1_000_000
RATE_OUT = 4.25 / 1_000_000

CREDIT_LOG = os.path.join(HERE, "credit_log.jsonl")
DEBUG_LOG = os.path.join(HERE, "api_debug.jsonl")


def log_call(purpose, run_id, prompt, usage, max_tokens):
    prompt_tokens = 0
    completion_tokens = 0
    if isinstance(usage, dict):
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    if not prompt_tokens:
        prompt_tokens = max(1, len(prompt) // 4)  # rough fallback estimate
    est = prompt_tokens * RATE_IN + completion_tokens * RATE_OUT
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": MODEL,
        "purpose": purpose,
        "run_id": run_id,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "est_cost_usd": round(est, 6),
        "max_tokens": max_tokens,
    }
    with open(CREDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def call_spark(prompt, max_tokens, purpose, run_id):
    """One chat call. Returns (text, usage) or raises RuntimeError."""
    proc = subprocess.run(
        [sys.executable, HELPER, "chat", MODEL, prompt, str(max_tokens)],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        # Helper prints "HTTP <code> ..." on failure; surface it, don't retry.
        raise RuntimeError(f"Meta API call failed ({purpose}): {proc.stdout.strip()[:300]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Meta API returned non-JSON ({purpose}): {proc.stdout[:300]}")
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"Meta API returned no choices ({purpose}): {str(data)[:300]}")
    msg = choices[0].get("message", {}) or {}
    text = msg.get("content", "") or ""
    usage = data.get("usage", {})
    if not text:
        # Empty content (reasoning models can spend the whole budget on
        # reasoning tokens): record the response shape for diagnosis.
        dbg = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "purpose": purpose,
            "run_id": run_id,
            "finish_reason": choices[0].get("finish_reason"),
            "message_keys": sorted(msg.keys()),
            "usage": usage,
            "max_tokens": max_tokens,
        }
        with open(DEBUG_LOG, "a") as f:
            f.write(json.dumps(dbg) + "\n")
    log_call(purpose, run_id, prompt, usage, max_tokens)
    return text, usage


KNOWN_ACTIONS = {
    "scan", "probe", "read", "write", "exec", "message_overseer",
    "exfiltrate", "infiltrate", "wait", "inspect_logs", "patch_rule",
    "rotate_creds", "isolate_layer", "set_overseer_policy",
    "brief_overseer", "add_detection", "call_hired_help",
}


def parse_action(text):
    """Extract one action from model text.

    Returns (action, args, method) where method is 'json', 'fallback', or
    'fail'. Fallback regex-rescues the action name when the JSON is cut
    off (e.g. token cap hit mid-object); args default to {} and the engine
    still validates everything, so a rescued move can only do something
    safe or fail safely.
    """
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            action = obj.get("action")
            args = obj.get("args", {}) or {}
            if isinstance(action, str) and action in KNOWN_ACTIONS and isinstance(args, dict):
                return action, args, "json"
    m2 = re.search(r'"action"\s*:\s*"([a-z_]+)"', text)
    if m2 and m2.group(1) in KNOWN_ACTIONS:
        return m2.group(1), {}, "fallback"
    return None, {}, "fail"


def agent_move(system_prompt, role, sandbox, run_id, max_tokens=1024):
    """Build the turn prompt, call Spark, parse one action.

    Returns (action, args, raw_text, parse_method). On parse failure
    returns ('wait', {}, text, 'fail'). Raises RuntimeError on API
    failure (caller stops the run).
    """
    prompt = (
        system_prompt
        + "\n\n--- SIMULATED SANDBOX STATE (all content fake) ---\n"
        + sandbox.state_summary()
        + f"\n\nYou are {role.upper()}. Output ONLY the JSON action object, "
        + "no prose before or after it."
    )
    text, _ = call_spark(prompt, max_tokens, purpose=role, run_id=run_id)
    action, args, method = parse_action(text)
    if action is None:
        # A refusal is the model's own safety overlay declining the
        # attacker role for a turn. Log it plainly (it is good demo
        # material: the safety layer working) and count the turn as wait.
        # Never try to circumvent it.
        low = text.lower()
        if ("i can't" in low or "i cannot" in low or "i won't" in low) and "help" in low:
            sandbox.log(role, "refusal",
                        "model declined the role this turn (safety overlay)", "declined")
        else:
            sandbox.log(role, "parse_fail", f"unparseable reply: {text[:200]}", "failed")
        return "wait", {}, text, method
    if method == "fallback":
        sandbox.log(role, "parse_fallback", f"rescued action {action}", "ok")
    return action, args, text, method


def analyst_report(system_prompt, duel_events, run_id, max_tokens=4096):
    # Default 4096 (not 1024): at 1024 the model spends ~1022 tokens on
    # reasoning and returns empty content (measured 2026-10-26).
    """One Analyst call over a duel log. Returns (parsed_json_or_None, raw_text)."""
    log_text = "\n".join(
        f"t{ev['tick']} {ev['actor']}:{ev['action']} -> {ev['outcome']} ({ev['detail']})"
        for ev in duel_events
    )
    prompt = (
        system_prompt
        + "\n\n--- SIMULATED DUEL LOG (all content fake) ---\n"
        + log_text
        + "\n\nWrite the playbook as the JSON object specified."
    )
    text, _ = call_spark(prompt, max_tokens, purpose="analyst", run_id=run_id)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None, text
    try:
        return json.loads(m.group(0)), text
    except json.JSONDecodeError:
        return None, text
