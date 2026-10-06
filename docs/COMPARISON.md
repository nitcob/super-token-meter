# Super Token Meter vs. `splunk/token-meter`

A side‑by‑side of what each tool does, so it's clear what Super Token Meter **leads on**,
where it's **behind**, and what "cover their features plus ours" concretely means. The plan
to close the gaps lives in [`ROADMAP.md`](../ROADMAP.md).

> **Sources.** All `splunk/token-meter` claims are from its README
> (`https://raw.githubusercontent.com/splunk/token-meter/main/README.md`, read 2026‑10‑06).
> All Super Token Meter claims are from this repo's shipped code
> (`super_token_meter/dashboard/index.html`, `README.md`, `super_token_meter/*.py`).
> Both projects are MIT‑licensed and local‑first.

## Two different philosophies

Feature counts mislead here, because the two tools aim at different things:

- **`splunk/token-meter` — a broad, multi‑agent observability platform.** Six agents, a native
  menu‑bar/tray app, an MCP server, budgets, git integration, and dedicated per‑tool / per‑subagent
  pages. Wide and operational.
- **Super Token Meter — deep single‑agent (Claude) cost analysis with a privacy thesis.** Grounded,
  cited benchmarks; a cloud‑vs‑local **privacy split**; **local‑LLM** tapping; and a **model‑mix
  what‑if**. Narrow and analytical.

## Feature matrix

| Capability                                                                      | `splunk/token-meter`                                                                            | Super Token Meter                                                                      |
| ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Agents covered**                                                              | 6: Claude Code + Desktop/Cowork, Codex CLI + desktop, Cursor Agent/Composer, OpenCode, Kiro, Pi | 1: Claude Code **+ any local LLM** (Ollama / OpenAI‑compatible)                        |
| **Data collection**                                                             | File‑parse local runtime stores, no key                                                         | File‑parse `~/.claude/**/*.jsonl` **+ a streaming proxy** for local LLMs, no key       |
| **No API key / local‑first**                                                    | Yes                                                                                             | Yes                                                                                    |
| **Privacy: binds 127.0.0.1, no telemetry**                                      | Yes (update‑check every 10 min, opt‑in auto‑install)                                            | Yes (**no** auto‑update; only a user‑triggered pricing refresh)                        |
| **Equivalent / estimated cost**                                                 | Yes — "public API‑equivalent rates"                                                             | Yes — + explicit **"notional list price, not a bill"** framing                         |
| **Exact cache 5m/1h multipliers**                                               | Cost shown; cache detail light                                                                  | Explicit ×0.1 read / ×1.25 (5m) / ×2 (1h) in `pricing.json`                            |
| **Cache‑hit efficiency**                                                        | "Cache hit ratio"                                                                               | Yes + **grounded 81–90% healthy band**                                                 |
| **Context load / tokens‑per‑request**                                           | "Context load" (input÷output)                                                                   | "Tokens/request" (all‑incl‑cache) + "overhead ×"                                       |
| **Reasoning / thinking ratio**                                                  | "Reasoning ratio"                                                                               | Thinking tokens **collected**, not yet surfaced as a ratio                             |
| **Output efficiency**                                                           | "Output / $"                                                                                    | "$/M output" (inverse)                                                                 |
| **Grounded, cited benchmarks**                                                  | No — "higher/lower is better"                                                                   | **$13/$30 active‑day target + 8 Anthropic references**, with bands and a "You" value   |
| **Cloud‑vs‑local privacy split**                                                | No                                                                                              | Donut: % of content tokens kept on‑prem                                                |
| **Local‑LLM usage tracking**                                                    | No                                                                                              | Yes — via the proxy tap                                                                |
| **Model‑mix what‑if (Opus→Sonnet)**                                             | No                                                                                              | Interactive slider with projected savings                                              |
| **By‑model / by‑project tables**                                                | Models page (+ git‑by‑project)                                                                  | Both                                                                                   |
| **Costliest sessions**                                                          | Sessions page                                                                                   | Table                                                                                  |
| **Time grouping**                                                               | Preset ranges (Today/Yesterday/7/30/90/Month/Last month/All/custom)                             | Calendar buckets (Day/Week/Month/Quarter/Year)                                         |
| **Per‑session "Run view"** (context pressure, wait, output pace, tool evidence) | Yes                                                                                             | No                                                                                     |
| **Wait time / Work time (durations)**                                           | Yes                                                                                             | No                                                                                     |
| **Subagents page** (role hierarchy over time)                                   | Yes                                                                                             | No                                                                                     |
| **Tools page** (calls, failures, repeats, skill‑pack activation)                | Yes                                                                                             | No                                                                                     |
| **Git integration** (pushes ↔ spend)                                            | Yes                                                                                             | No                                                                                     |
| **Budgets + threshold alerts** (monthly + per‑session)                          | Yes                                                                                             | No (roadmap)                                                                           |
| **MCP server** (agent queries its own usage/budget)                             | Yes — 10 read‑only tools                                                                        | No (roadmap)                                                                           |
| **Native menu‑bar / tray app**                                                  | Yes                                                                                             | No — browser only                                                                      |
| **Raw data API / export**                                                       | MCP read‑only; no bulk export                                                                   | Serves raw JSON at `/data/*.json`                                                      |
| **Packaging**                                                                   | git clone + install; Windows beta via WinGet; `--backend-only`; no pip/Docker                   | git clone + install (launchd / systemd / **Task Scheduler**); pipx + Docker on roadmap |
| **License**                                                                     | MIT                                                                                             | MIT                                                                                    |

`splunk/token-meter` MCP tools (read‑only): `check`, `usage`, `budget`, `set_session_budget`,
`set_default_session_budget`, `capabilities`, `sessions`, `trace`, `stats`, `schema`.

## The three buckets

### Only Super Token Meter has it (the moat — lead with these)

- **Cloud‑vs‑local privacy split** and the **local‑LLM proxy tap** — the whole "how much of my AI
  stays on my machine" thesis. `splunk/token-meter` has no local‑model story.
- **Grounded, cited benchmarks** ($13/$30 active‑day, cache 81–90%) with "You" values and bands.
- **Model‑mix what‑if** slider (actionable savings).
- **Exact cache 5m/1h pricing** and the honest **"equivalent list price, not a bill"** framing.
- **Raw JSON at `/data/`** — trivially scriptable without an MCP.

### Only `splunk/token-meter` has it (the gap list — see ROADMAP)

1. **Multi‑agent** (Codex, Cursor, OpenCode, Kiro, Pi) — biggest scope gap.
2. **MCP server** (read‑only tools) — lets an agent self‑query spend/budget.
3. **Budgets + alerts** (monthly + per‑session threshold notifications).
4. **Git integration** (pair pushes with spend → cost per shipped change).
5. **Subagents page** (role hierarchy) and **Tools page** (per‑tool calls/failures/skill‑packs).
6. **Per‑session Run view** with context pressure, **wait/work durations**, output pace.
7. **Native tray app** + **Windows WinGet** bootstrap.

### Both have it (parity)

Local‑first / no key · 127.0.0.1 privacy · equivalent cost · cache‑hit + context‑load efficiency ·
by‑model / by‑project · costliest sessions · time‑range grouping · git‑clone + install · MIT.

## Bottom line

Super Token Meter is **ahead on analytical depth and privacy** (local split, grounded benchmarks,
what‑if) and **behind on breadth and operational tooling** (agents, MCP, budgets, git, tray).
The [roadmap](../ROADMAP.md) closes most of the perceived gap (items 1–4 above) while the
differentiators stay unique.
