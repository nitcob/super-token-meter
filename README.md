# Super Token Meter

[![CI](https://github.com/nitcob/super-token-meter/actions/workflows/ci.yml/badge.svg)](https://github.com/nitcob/super-token-meter/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Deps: stdlib only](https://img.shields.io/badge/deps-stdlib%20only-blue.svg)
![Local-first](https://img.shields.io/badge/local--first-no%20API%20key-brightgreen.svg)

**Local‑first, private dashboard for AI coding‑agent token usage & cost.** See how many tokens you burn in **Claude Code** (and your **local LLMs**), what it would cost at API rates, how efficient you are against **grounded benchmarks**, and how much of your AI stays **on your own machine**.

> **No API key. No account. No cloud. Nothing leaves your machine.** It reads the session logs your agent already writes to disk. Python standard library only — zero dependencies.

---

## Quickstart

```bash
git clone https://github.com/nitcob/super-token-meter.git
cd super-token-meter

# See it immediately with bundled sample data (no real logs touched):
python3 -m super_token_meter demo

# Or run it on your real Claude Code usage:
python3 -m super_token_meter serve
```

That opens the dashboard at **http://127.0.0.1:8722** (localhost‑only). To keep it fresh, run `collect` on a schedule (see [deploy/](deploy/) — macOS launchd · Linux systemd · Windows Task Scheduler).

```
super-token-meter serve      # collect + open the dashboard
super-token-meter collect    # just refresh the data (for a scheduler)
super-token-meter demo       # render bundled sample data
super-token-meter proxy      # log a local LLM's usage (Ollama / OpenAI-compatible)
super-token-meter aggregate  # roll the proxy log into local_usage.json
```

## How it connects (and why there's no API key)

Claude Code already records **every message's exact token usage** to `~/.claude/projects/**/*.jsonl` on your machine. Super Token Meter **auto‑discovers and reads those files** — that's the whole "connection." Nothing is sent anywhere.

| What                                       | Needs a key? | How                                                                       |
| ------------------------------------------ | ------------ | ------------------------------------------------------------------------- |
| Your usage & cost                          | **No**       | reads local Claude Code logs on disk                                      |
| Pricing (the $ figures)                    | **No**       | bundled [`pricing.json`](super_token_meter/pricing.json), works offline   |
| Local‑LLM tracking                         | **No**       | point your Ollama / OpenAI‑compatible client at `super-token-meter proxy` |
| _(optional, future)_ real **billed** spend | Yes          | only if you opt into a cloud billing API                                  |

## What it shows

- **Overview** — cloud equivalent cost, cloud vs **local** token volume, and the **privacy split** (% of content tokens kept on‑prem).
- **Efficiency** with **benchmarks** — cost/active‑day, cache‑hit rate, $/request, tokens/request, overhead ×, $/M, each with a **"You" value** and optimal/watch/high bands. The grounded ones are labeled ◆ (see below); the rest are clearly marked heuristics.
- **Where the cost goes** (by token type), an **efficiency‑over‑time** trend, a **model‑mix what‑if** slider (route Opus → Sonnet and see the projected savings), **costliest sessions**, by‑model / by‑project tables.
- **Usage by period** — group everything by **day / week / month / quarter / year**.

## Benchmarks are grounded, not invented

The one metric with a published target is **cost per active day**: Anthropic reports Claude Code averages **~$13/developer/active‑day** and stays **under $30 for 90% of users** ([source](https://code.claude.com/docs/en/costs)). Cache‑hit rate uses Anthropic's published healthy range for agent loops (**81–90%**). Everything else (`$/request`, `tokens/request`, `overhead ×`) is a **derived heuristic** — Anthropic publishes no official target — and is labeled as such on the dashboard. Cost is **equivalent list price** (Claude Code is usually subscription‑flat), and Anthropic frames efficiency as **cost per task, not per token** — see the References on the page.

## Privacy

- The dashboard binds **`127.0.0.1` only**. No telemetry, no analytics, no account.
- The **only** optional outbound call is a user‑triggered pricing refresh to Anthropic's _public_ pricing page. Bundled pricing works fully offline, so it's skippable. (There is **no** auto‑update.)
- No real usage data is in this repo — the `demo` data under [`examples/`](examples/) is synthetic.

## Configuration

Sensible defaults; override with env vars or flags:

| Env            | Default                     | Meaning                                |
| -------------- | --------------------------- | -------------------------------------- |
| `STM_DATA_DIR` | `~/.super-token-meter/data` | where data is stored/read              |
| `STM_UPSTREAM` | `http://127.0.0.1:11434`    | local‑LLM proxy upstream (e.g. Ollama) |
| `STM_LISTEN`   | `127.0.0.1:11435`           | where the proxy listens                |

## Status & roadmap

v0.1 — Claude Code + local LLMs, dashboard, pricing, demo. Planned: read‑only **MCP server** (so an agent can query its own usage/budget), **budgets + local alerts**, subagent/tool‑call breakdown, more agents (Codex, Cursor, …), `pipx` + Docker packaging.

See [`ROADMAP.md`](ROADMAP.md) for the full plan with milestones, effort, and acceptance criteria.

## Prior art / credit

Inspired by [`splunk/token-meter`](https://github.com/splunk/token-meter) (MIT) — a broader, multi‑agent local‑first dashboard. Super Token Meter is an independent project that leans into exact Claude cache pricing, the cloud‑vs‑local **privacy split**, grounded cited benchmarks, local‑model tapping, and the model‑mix what‑if.

A detailed, feature‑by‑feature comparison is in [`docs/COMPARISON.md`](docs/COMPARISON.md).

## License

[MIT](LICENSE).
