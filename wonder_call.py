#!/usr/bin/env python3
"""Call the Meta Model API from a prompt file, with a hard free-credit cap.

Usage:
  wonder_call.py MODEL PROMPT_FILE MAX_TOKENS PURPOSE [RUN_ID] [OUTPUT_MD]

Safety rules (do not weaken):
- Prompt comes from a file, never from argv, and is never printed or logged.
- Refuses if the prompt looks like it contains a credential.
- Refuses if the estimated cost would push cumulative spend past $150 of
  free credits. Cumulative spend is read from credit_log.jsonl in this dir.
- Appends the call's actual usage + estimated cost to credit_log.jsonl
  using the same schema as the existing log.
- Pricing below is list price, used as credit-value accounting:
  muse-wonder-1.0: $4 / $20 per 1M input/output tokens.
  Unknown models are refused (never guess a price).
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

PROVIDER = "custom.meta-model-api"
HOSTS = ["api.meta.ai"]
BASE = "https://api.meta.ai/v1"
FREE_CREDIT_CAP_USD = 150.0
PRICING = {
    "muse-wonder-1.0": (4.0, 20.0),
}
LOG = Path(__file__).resolve().parent / "credit_log.jsonl"
CRED_RE = re.compile(r"LLM_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{10,}|0x[a-fA-F0-9]{40}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def cumulative_spend():
    total = 0.0
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:
                total += float(json.loads(line).get("est_cost_usd", 0.0))
            except (ValueError, TypeError):
                continue
    return total


def main(argv):
    if len(argv) < 5:
        print(__doc__)
        return 2
    model, prompt_file, max_tokens, purpose = argv[1], argv[2], int(argv[3]), argv[4]
    run_id = argv[5] if len(argv) > 5 else ""
    output_md = argv[6] if len(argv) > 6 else ""
    if model not in PRICING:
        print(f"REFUSED: no known price for model {model}; refusing rather than guessing.")
        return 3
    prompt = Path(prompt_file).read_text()
    if CRED_RE.search(prompt):
        print("REFUSED: prompt looks like it contains a credential.")
        return 3
    in_price, out_price = PRICING[model]
    used = cumulative_spend()
    est_in_tokens = len(prompt) / 3  # conservative: overestimates input tokens
    est_cost = (est_in_tokens / 1e6) * in_price + (max_tokens / 1e6) * out_price
    print(f"credit check: used=${used:.4f} cap=${FREE_CREDIT_CAP_USD:.2f} "
          f"est_this_call=${est_cost:.4f} prompt_chars={len(prompt)}", file=sys.stderr)
    if used + est_cost > FREE_CREDIT_CAP_USD:
        print(f"REFUSED: this call would exceed the ${FREE_CREDIT_CAP_USD} free-credit cap.")
        return 3
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    add_surrogate_to_request(req, PROVIDER, allowed_hosts=HOSTS)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=300) as resp:
            data = read_json_response(resp)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {e.reason}: {e.read().decode('utf-8', 'replace')}")
        return 1
    usage = data.get("usage", {}) if isinstance(data, dict) else {}
    pt = int(usage.get("prompt_tokens", 0))
    ct = int(usage.get("completion_tokens", 0))
    cost = (pt / 1e6) * in_price + (ct / 1e6) * out_price
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "purpose": purpose,
        "run_id": run_id,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": int(usage.get("total_tokens", pt + ct)),
        "est_cost_usd": round(cost, 6),
        "max_tokens": max_tokens,
    }
    with LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"cost: this_call=${cost:.4f} cumulative=${used + cost:.4f} "
          f"free_left=${FREE_CREDIT_CAP_USD - used - cost:.4f}", file=sys.stderr)
    if output_md:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = ""
        if content:
            Path(output_md).write_text(content)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
