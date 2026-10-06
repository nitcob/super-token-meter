#!/usr/bin/env python3
"""
collector.py  --  Super Token Meter: Claude Code usage collector

Purpose : Parse the local Claude Code session logs in ~/.claude/projects/**/*.jsonl,
          aggregate token usage (input / output / cache / thinking) and the EQUIVALENT
          API cost per day / model / project, and emit a single claude_usage.json that
          the dashboard consumes.
          Local-first: reads local files only. No API key, no account, no network.
Usage   : cc_usage_collect.py [--output PATH] [--state PATH] [--root DIR] [--dry-run]
Notes   : stdlib-only (no pip deps). Incremental: remembers the last byte offset parsed
          per file so re-runs are cheap even with multi-hundred-MB session files.
          "Cost" is the EQUIVALENT API cost (what these tokens would bill at API rates) --
          Claude Code itself is typically subscription-flat; the real comparison is
          "$X of tokens through the cloud" vs "$0 local".
"""

import argparse
import glob
import json
import os
import socket
import sys
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Pricing is loaded from pricing.json (bundled next to this module) so prices can
# be updated without touching code. An embedded fallback keeps it working if the
# file is missing. USD per 1,000,000 tokens; emitted into the output so the
# dashboard shows exactly which rates/date were used.
# ---------------------------------------------------------------------------
_FALLBACK_PRICING = {
    "verified_date": "2026-10-05",
    "cache_multipliers": {"read": 0.10, "write_5m": 1.25, "write_1h": 2.0},
    "default": {"input": 5.0, "output": 25.0},
    "models": {
        "claude-opus-4-8": {"input": 5.0, "output": 25.0},
        "claude-opus-5":   {"input": 5.0, "output": 25.0},
        "claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.20},
        "claude-fable-5":  {"input": 10.0, "output": 50.0},
        "claude-sonnet-5": {"input": 2.0, "output": 10.0, "cache_read": 0.20},
        "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    },
}


def _load_pricing():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pricing.json")
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return _FALLBACK_PRICING


_PRICING = _load_pricing()
PRICING = _PRICING.get("models", _FALLBACK_PRICING["models"])
CACHE_MULT = _PRICING.get("cache_multipliers", _FALLBACK_PRICING["cache_multipliers"])
DEFAULT_RATE = _PRICING.get("default", _FALLBACK_PRICING["default"])
PRICING_VERIFIED = _PRICING.get("verified_date", "")
# Models that are not billed / not real API models -> excluded from cost + usage.
SKIP_MODELS = {"<synthetic>", "", None}

LOG_PREFIX = "[cc-collect]"

import re
_DATE_SUFFIX = re.compile(r"-\d{6,8}$")


def normalize_model(model):
    """Strip a trailing -YYYYMMDD (or -YYYYMM) snapshot suffix so e.g.
    'claude-haiku-4-5-20251001' prices and groups as 'claude-haiku-4-5'."""
    if not isinstance(model, str):
        return model
    return _DATE_SUFFIX.sub("", model)


def log(msg):
    print(f"{LOG_PREFIX} [{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", file=sys.stderr)


def rate_for(model):
    return PRICING.get(model, DEFAULT_RATE)


def cost_for(model, inp, out, cache_read, eph5m, eph1h):
    """Equivalent API cost in USD for one message's token counts."""
    r = rate_for(model)
    inrate = r["input"]
    read_rate = r.get("cache_read", inrate * CACHE_MULT["read"])
    w5 = r.get("cache_write_5m", inrate * CACHE_MULT["write_5m"])
    w1 = r.get("cache_write_1h", inrate * CACHE_MULT["write_1h"])
    return (
        inp * inrate
        + out * r["output"]
        + cache_read * read_rate
        + eph5m * w5
        + eph1h * w1
    ) / 1_000_000.0


def project_label(obj, filepath, root):
    """A short, friendly project name. Prefer the record's cwd basename."""
    cwd = obj.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        base = os.path.basename(cwd.rstrip("/"))
        if base:
            return base
    # Fall back to the mangled project dir name under ~/.claude/projects/
    rel = os.path.relpath(filepath, root)
    top = rel.split(os.sep)[0]
    # e.g. "-home-user-code-myapp" -> "myapp"
    parts = [p for p in top.split("-") if p]
    return parts[-1] if parts else top


def iter_usage_records(filepath):
    """Yield (timestamp_str, model, usage_dict, raw_obj) for assistant usage lines.
    Returns the byte offset of the last COMPLETE line consumed (for incremental state).
    """
    results = []
    with open(filepath, "rb") as fh:
        for raw in fh:
            if not raw.endswith(b"\n"):
                break  # incomplete trailing line; stop (don't advance past it)
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            model = msg.get("model")
            if model in SKIP_MODELS:
                continue
            results.append((obj.get("timestamp"), model, usage, obj))
    return results


def offset_of_last_complete_line(filepath):
    """Byte offset just past the final newline (= start of any partial tail)."""
    size = os.path.getsize(filepath)
    if size == 0:
        return 0
    with open(filepath, "rb") as fh:
        # read backwards in a small window to find the last '\n'
        window = min(size, 65536)
        fh.seek(size - window)
        data = fh.read(window)
    idx = data.rfind(b"\n")
    if idx == -1:
        return 0
    return (size - window) + idx + 1


def iter_usage_from_offset(filepath, start):
    """Like iter_usage_records but only lines fully contained after `start`."""
    results = []
    with open(filepath, "rb") as fh:
        fh.seek(start)
        for raw in fh:
            if not raw.endswith(b"\n"):
                break
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            model = msg.get("model")
            if model in SKIP_MODELS:
                continue
            results.append((obj.get("timestamp"), model, usage, obj))
    return results


def to_local_date(ts):
    """ISO-8601 UTC string -> local YYYY-MM-DD (buckets by the user's day)."""
    if not ts:
        return None
    try:
        s = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d")
    except Exception:
        return None


def extract_counts(usage):
    inp = int(usage.get("input_tokens", 0) or 0)
    out = int(usage.get("output_tokens", 0) or 0)
    cread = int(usage.get("cache_read_input_tokens", 0) or 0)
    cc = usage.get("cache_creation")
    if isinstance(cc, dict):
        eph5m = int(cc.get("ephemeral_5m_input_tokens", 0) or 0)
        eph1h = int(cc.get("ephemeral_1h_input_tokens", 0) or 0)
    else:
        eph5m = int(usage.get("cache_creation_input_tokens", 0) or 0)
        eph1h = 0
    details = usage.get("output_tokens_details") or {}
    think = int(details.get("thinking_tokens", 0) or 0) if isinstance(details, dict) else 0
    return inp, out, cread, eph5m, eph1h, think


def blank_bucket():
    return {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_write_5m_tokens": 0, "cache_write_1h_tokens": 0,
        "thinking_tokens": 0, "cost_usd": 0.0, "requests": 0,
    }


def add_record(buckets, key, model, inp, out, cread, eph5m, eph1h, think):
    b = buckets[key]
    b["input_tokens"] += inp
    b["output_tokens"] += out
    b["cache_read_tokens"] += cread
    b["cache_write_5m_tokens"] += eph5m
    b["cache_write_1h_tokens"] += eph1h
    b["thinking_tokens"] += think
    b["cost_usd"] += cost_for(model, inp, out, cread, eph5m, eph1h)
    b["requests"] += 1


def main():
    ap = argparse.ArgumentParser(description="Collect Claude Code token usage (local logs only).")
    default_root = os.path.expanduser("~/.claude/projects")
    # Per-user data dir (override with STM_DATA_DIR); never touches the repo.
    data_dir = os.environ.get("STM_DATA_DIR", os.path.expanduser("~/.super-token-meter/data"))
    ap.add_argument("--root", default=default_root, help="Claude Code projects dir")
    ap.add_argument("--output", default=os.path.join(data_dir, "claude_usage.json"))
    ap.add_argument("--state", default=os.path.join(data_dir, ".cc_state.json"))
    ap.add_argument("--dry-run", action="store_true", help="parse but do not write output/state")
    ap.add_argument("--full", action="store_true", help="ignore state, reparse everything")
    args = ap.parse_args()

    root = os.path.expanduser(args.root)
    if not os.path.isdir(root):
        log(f"ERROR: root not found: {root}")
        return 2

    # Load prior state (incremental aggregates + per-file offsets)
    state = {"files": {}, "daily": {}, "generated_at": None}
    if os.path.exists(args.state) and not args.full:
        try:
            with open(args.state) as fh:
                state = json.load(fh)
        except Exception as e:
            log(f"WARN: could not read state ({e}); starting fresh")
            state = {"files": {}, "daily": {}, "generated_at": None}
    state.setdefault("files", {})
    state.setdefault("daily", {})  # "date\x00model\x00project" -> bucket
    state.setdefault("sessions", {})  # sessionId -> per-session aggregate (for $/session, top sessions)

    # Rebuild daily buckets from persisted dict (keys are tab-joined)
    daily = defaultdict(blank_bucket)
    for k, v in state["daily"].items():
        daily[k].update(v)

    files = sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True))
    new_msgs = 0
    scanned = 0
    for fp in files:
        try:
            size = os.path.getsize(fp)
            inode = os.stat(fp).st_ino
        except OSError:
            continue
        rec = state["files"].get(fp)
        start = 0
        if rec and not args.full and rec.get("inode") == inode and rec.get("offset", 0) <= size:
            start = rec.get("offset", 0)
        if start >= size:
            continue  # nothing new
        scanned += 1
        records = iter_usage_from_offset(fp, start)
        for ts, model, usage, obj in records:
            date = to_local_date(ts)
            if not date:
                continue
            model = normalize_model(model)
            proj = project_label(obj, fp, root)
            inp, out, cread, eph5m, eph1h, think = extract_counts(usage)
            key = f"{date}\t{model}\t{proj}"
            add_record(daily, key, model, inp, out, cread, eph5m, eph1h, think)
            # per-session aggregate (for $/session + costliest-sessions view)
            sid = obj.get("sessionId") or obj.get("session_id") or "unknown"
            sb = state["sessions"].get(sid)
            if sb is None:
                sb = {"requests": 0, "input_tokens": 0, "output_tokens": 0,
                      "cache_read_tokens": 0, "cache_write_5m_tokens": 0, "cache_write_1h_tokens": 0,
                      "thinking_tokens": 0, "cost_usd": 0.0, "first": date, "last": date, "project": proj}
                state["sessions"][sid] = sb
            sb["requests"] += 1
            sb["input_tokens"] += inp; sb["output_tokens"] += out
            sb["cache_read_tokens"] += cread
            sb["cache_write_5m_tokens"] += eph5m; sb["cache_write_1h_tokens"] += eph1h
            sb["thinking_tokens"] += think
            sb["cost_usd"] += cost_for(model, inp, out, cread, eph5m, eph1h)
            sb["last"] = date
            new_msgs += 1
        state["files"][fp] = {"inode": inode, "offset": offset_of_last_complete_line(fp), "size": size}

    # --- build output document -------------------------------------------
    daily_list = []
    by_model = defaultdict(blank_bucket)
    by_project = defaultdict(blank_bucket)
    totals = blank_bucket()
    for key, b in daily.items():
        date, model, proj = key.split("\t")
        rowb = dict(b); rowb["cost_usd"] = round(b["cost_usd"], 6)
        daily_list.append({"date": date, "model": model, "project": proj, **rowb})
        for field in b:
            by_model[model][field] += b[field]
            by_project[proj][field] += b[field]
            totals[field] += b[field]
    daily_list.sort(key=lambda r: (r["date"], r["model"], r["project"]))

    def rounded(d):
        out = {}
        for k, v in d.items():
            vv = dict(v); vv["cost_usd"] = round(v["cost_usd"], 6)
            out[k] = vv
        return out

    totals["cost_usd"] = round(totals["cost_usd"], 6)
    sessions = state["sessions"]
    totals["sessions"] = len(sessions)
    top = sorted(sessions.items(), key=lambda kv: -kv[1]["cost_usd"])[:10]
    top_sessions = []
    for sid, v in top:
        toks = (v["input_tokens"] + v["output_tokens"] + v["cache_read_tokens"]
                + v["cache_write_5m_tokens"] + v["cache_write_1h_tokens"])
        top_sessions.append({"id": sid[:8], "project": v["project"], "first": v["first"], "last": v["last"],
                             "requests": v["requests"], "input_tokens": v["input_tokens"],
                             "output_tokens": v["output_tokens"], "cache_read_tokens": v["cache_read_tokens"],
                             "tokens": toks, "cost_usd": round(v["cost_usd"], 4)})
    doc = {
        "source": "claude_code",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": socket.gethostname(),  # cross-platform (os.uname() is Unix-only -> crashes on Windows)
        "pricing": {"models": PRICING, "cache_multipliers": CACHE_MULT, "default": DEFAULT_RATE,
                    "verified_date": PRICING_VERIFIED,
                    "note": "USD per 1e6 tokens; cost is EQUIVALENT API cost (Claude Code is subscription-flat)."},
        # models seen in the logs that are NOT in the pricing table (priced at the default rate -> may be wrong)
        "unpriced_models": sorted(m for m in by_model if m not in PRICING),
        "totals": totals,
        "by_model": rounded(by_model),
        "by_project": rounded(by_project),
        "top_sessions": top_sessions,
        "daily": daily_list,
    }

    log(f"files={len(files)} scanned_with_new={scanned} new_messages={new_msgs} "
        f"all_time_cost=${totals['cost_usd']:.2f} requests={totals['requests']}")

    if args.dry_run:
        log("DRY-RUN: not writing output or state")
        print(json.dumps({k: doc[k] for k in ("source", "generated_at", "totals")}, indent=2))
        return 0

    # persist state (store daily buckets back for next incremental run)
    state["daily"] = {k: v for k, v in daily.items()}
    state["generated_at"] = doc["generated_at"]
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.state)), exist_ok=True)
    tmp = args.output + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    os.replace(tmp, args.output)
    tmp = args.state + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, separators=(",", ":"))
    os.replace(tmp, args.state)
    log(f"wrote {args.output} ({os.path.getsize(args.output)} bytes) and state")
    return 0


if __name__ == "__main__":
    sys.exit(main())
