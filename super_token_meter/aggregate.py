#!/usr/bin/env python3
"""
aggregate.py  --  Super Token Meter: roll the Ollama proxy log into local_usage.json

Purpose : Read the append-only usage.jsonl emitted by ollama_logger.py and produce a
          local_usage.json with the SAME shape as the Claude-side claude_usage.json, so
          the dashboard can combine them. Local inference is free, so cost_usd = 0 and
          the cache/thinking fields are 0 (Ollama has no prompt caching here).
Part of Super Token Meter (stdlib-only).
Date    : 2026-10-02
Usage   : aggregate_local.py [--log PATH] [--output PATH]
Notes   : stdlib only. Idempotent -- re-reads the whole (small) log each run. If the log
          does not exist yet, emits an empty-but-valid doc so the dashboard shows
          "no local data yet" instead of erroring.
"""

import argparse
import json
import os
import socket
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone


def blank_bucket():
    return {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_write_5m_tokens": 0, "cache_write_1h_tokens": 0,
        "thinking_tokens": 0, "cost_usd": 0.0, "requests": 0,
    }


def local_date(epoch):
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d")


def aggregate(log_path, output_path):
    """Read the proxy's usage.jsonl and (atomically) write local_usage.json.
    Returns a short summary dict. Safe to call repeatedly (idempotent)."""
    daily = defaultdict(blank_bucket)
    by_model = defaultdict(blank_bucket)
    totals = blank_bucket()
    n = 0
    if os.path.exists(log_path):
        with open(log_path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                model = r.get("model") or "unknown"
                inp = int(r.get("input_tokens", 0) or 0)
                out = int(r.get("output_tokens", 0) or 0)
                ts = int(r.get("ts", 0) or 0)
                if not ts:
                    continue
                date = local_date(ts)
                key = f"{date}\t{model}"
                for tgt in (daily[key], by_model[model], totals):
                    tgt["input_tokens"] += inp
                    tgt["output_tokens"] += out
                    tgt["requests"] += 1
                n += 1

    daily_list = []
    for key, b in daily.items():
        date, model = key.split("\t")
        daily_list.append({"date": date, "model": model, "project": "local", **b})
    daily_list.sort(key=lambda r: (r["date"], r["model"]))

    doc = {
        "source": "local",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": socket.gethostname(),  # cross-platform (os.uname() is Unix-only -> crashes on Windows)
        "totals": totals,
        "by_model": dict(by_model),
        "by_project": {"local": dict(totals)},
        "daily": daily_list,
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    tmp = output_path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    os.replace(tmp, output_path)
    return {"records": n, "days": len(daily_list), "models": list(by_model),
            "input_tokens": totals["input_tokens"], "output_tokens": totals["output_tokens"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=os.environ.get("LOG_PATH", os.path.expanduser(os.path.join(os.environ.get("STM_DATA_DIR","~/.super-token-meter/data"),"usage.jsonl"))))
    ap.add_argument("--output", default=os.path.expanduser(os.path.join(os.environ.get("STM_DATA_DIR","~/.super-token-meter/data"),"local_usage.json")))
    args = ap.parse_args()
    s = aggregate(args.log, args.output)
    sys.stderr.write(f"[aggregate-local] [{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                     f"records={s['records']} days={s['days']} models={s['models']} "
                     f"in={s['input_tokens']} out={s['output_tokens']} -> {args.output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
