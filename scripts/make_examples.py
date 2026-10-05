#!/usr/bin/env python3
"""Generate deterministic synthetic sample data for `super-token-meter demo`.
Writes examples/claude_usage.json + examples/local_usage.json. Run: python3 scripts/make_examples.py
No real data is ever committed; this is fake-but-plausible data that exercises every view.
"""
import json
import os
import random
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PRICING = json.load(open(os.path.join(REPO, "super_token_meter", "pricing.json")))
MODELS_P = PRICING["models"]
MULT = PRICING["cache_multipliers"]
rnd = random.Random(42)

MODELS = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"]
WEIGHTS = [0.7, 0.25, 0.05]
PROJECTS = ["webapp", "cli-tool", "notes-site"]


def rate(m):
    return MODELS_P.get(m, PRICING["default"])


def cost(m, inp, out, cr, w5, w1):
    r = rate(m)
    rd = r.get("cache_read", r["input"] * MULT["read"])
    return (inp * r["input"] + out * r["output"] + cr * rd
            + w5 * r["input"] * MULT["write_5m"] + w1 * r["input"] * MULT["write_1h"]) / 1e6


def blank():
    return {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
            "cache_write_5m_tokens": 0, "cache_write_1h_tokens": 0,
            "thinking_tokens": 0, "cost_usd": 0.0, "requests": 0}


daily = []
by_model = defaultdict(blank)
by_project = defaultdict(blank)
totals = blank()
sessions = defaultdict(lambda: {"requests": 0, "cost_usd": 0.0, "tokens": 0,
                                "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                                "first": None, "last": None, "project": None})

end = date(2026, 10, 5)
start = end - timedelta(days=95)
d = start
sid_pool = [f"{i:08x}" + "-demo" for i in range(6)]
while d <= end:
    # ~55% of days are active, heavier in the last 3 weeks
    active_p = 0.8 if (end - d).days < 21 else 0.45
    if rnd.random() < active_p:
        n_rows = rnd.randint(1, 3)
        for _ in range(n_rows):
            m = rnd.choices(MODELS, WEIGHTS)[0]
            proj = rnd.choice(PROJECTS)
            reqs = rnd.randint(20, 400)
            out = reqs * rnd.randint(800, 2500)
            inp = reqs * rnd.randint(2, 40)
            cr = reqs * rnd.randint(120000, 520000)          # cache reads dominate (realistic)
            w1 = reqs * rnd.randint(8000, 16000)
            w5 = int(w1 * 0.05)
            think = int(out * rnd.uniform(0.05, 0.2))
            c = cost(m, inp, out, cr, w5, w1)
            row = {"date": d.isoformat(), "model": m, "project": proj,
                   "input_tokens": inp, "output_tokens": out, "cache_read_tokens": cr,
                   "cache_write_5m_tokens": w5, "cache_write_1h_tokens": w1,
                   "thinking_tokens": think, "cost_usd": round(c, 6), "requests": reqs}
            daily.append(row)
            for tgt in (by_model[m], by_project[proj], totals):
                for k in blank():
                    tgt[k] += row[k]
            sid = rnd.choice(sid_pool)
            s = sessions[sid]
            s["requests"] += reqs; s["cost_usd"] += c
            s["input_tokens"] += inp; s["output_tokens"] += out; s["cache_read_tokens"] += cr
            s["tokens"] += inp + out + cr + w5 + w1
            s["project"] = proj
            s["first"] = min(s["first"] or d.isoformat(), d.isoformat())
            s["last"] = max(s["last"] or d.isoformat(), d.isoformat())
    d += timedelta(days=1)

for agg in (by_model, by_project, totals):
    pass
totals["cost_usd"] = round(totals["cost_usd"], 6)
totals["sessions"] = len(sessions)


def rounded(dd):
    out = {}
    for k, v in dd.items():
        vv = dict(v); vv["cost_usd"] = round(v["cost_usd"], 6); out[k] = vv
    return out


top = sorted(sessions.items(), key=lambda kv: -kv[1]["cost_usd"])[:10]
top_sessions = [{"id": sid[:8], "project": v["project"], "first": v["first"], "last": v["last"],
                 "requests": v["requests"], "input_tokens": v["input_tokens"],
                 "output_tokens": v["output_tokens"], "cache_read_tokens": v["cache_read_tokens"],
                 "tokens": v["tokens"], "cost_usd": round(v["cost_usd"], 4)} for sid, v in top]

doc = {
    "source": "claude_code", "generated_at": datetime.now(timezone.utc).isoformat(),
    "host": "demo", "pricing": PRICING, "unpriced_models": [],
    "totals": totals, "by_model": rounded(by_model), "by_project": rounded(by_project),
    "top_sessions": top_sessions, "daily": sorted(daily, key=lambda r: (r["date"], r["model"]))}

os.makedirs(os.path.join(REPO, "examples"), exist_ok=True)
json.dump(doc, open(os.path.join(REPO, "examples", "claude_usage.json"), "w"), separators=(",", ":"))

# local usage (so the privacy split isn't 0)
ldaily = []
lby = defaultdict(blank); ltot = blank()
d = end - timedelta(days=20)
while d <= end:
    if rnd.random() < 0.5:
        m = rnd.choice(["llama3.1:8b", "qwen2.5:14b"])
        reqs = rnd.randint(3, 40)
        row = blank(); row["input_tokens"] = reqs * rnd.randint(300, 900)
        row["output_tokens"] = reqs * rnd.randint(400, 1500); row["requests"] = reqs
        r = {"date": d.isoformat(), "model": m, "project": "local", **row}
        ldaily.append(r)
        for tgt in (lby[m], ltot):
            for k in blank():
                tgt[k] += r[k]
    d += timedelta(days=1)
ldoc = {"source": "local", "generated_at": datetime.now(timezone.utc).isoformat(), "host": "demo",
        "totals": ltot, "by_model": dict(lby), "by_project": {"local": dict(ltot)}, "daily": ldaily}
json.dump(ldoc, open(os.path.join(REPO, "examples", "local_usage.json"), "w"), separators=(",", ":"))

print(f"wrote examples: claude ${totals['cost_usd']:.0f} over {totals['requests']} req / {len(daily)} daily rows / "
      f"{totals['sessions']} sessions; local in={ltot['input_tokens']} out={ltot['output_tokens']}")
