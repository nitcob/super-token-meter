# Super Token Meter — Roadmap

Where this goes next. The goal is to **cover the useful parts of `splunk/token-meter`'s broader
feature set while keeping Super Token Meter's differentiators** (grounded benchmarks, the
cloud‑vs‑local privacy split, local‑LLM tapping, the model‑mix what‑if). The full side‑by‑side is
in [`docs/COMPARISON.md`](docs/COMPARISON.md).

Items are ordered by **value per effort** against the current stdlib‑only architecture.

## Principles (guardrails for every item)

- **Local‑first, no key, no account, no cloud.** Core features never require an API key and nothing
  leaves the machine. New network calls are opt‑in and user‑triggered only.
- **No telemetry, no auto‑update.** The dashboard binds `127.0.0.1`.
- **Python standard library only.** Zero runtime dependencies; cross‑platform (macOS / Linux /
  Windows), verified in CI.
- **Honest numbers.** Equivalent cost is a notional list‑price yardstick, not a bill. Benchmarks are
  either grounded + cited or clearly labeled heuristics.

## Shipped — v0.1

Claude Code + local‑LLM collection · dashboard (Overview, Efficiency with grounded benchmarks,
Where‑the‑cost‑goes, Efficiency‑over‑time, model‑mix what‑if, Usage‑by‑period, privacy split,
by‑model / by‑project, costliest sessions, references) · bundled offline pricing with cache 5m/1h
multipliers · `demo` mode · cross‑platform scheduled collection (launchd / systemd / Task
Scheduler) · raw JSON served at `/data/`.

## v0.2 — cheap gap‑closers (mostly UI over data we already collect)

### 1. Reasoning‑ratio metric + per‑session Run view

- **Why:** closes two `splunk/token-meter` gaps (reasoning ratio, per‑session detail) with data the
  collector already captures.
- **What:** surface `thinking_tokens / output_tokens` as an Efficiency KPI; add a per‑session drill‑in
  (cost, tokens by type, cache hit, tokens/req, model, time span) built from `top_sessions` / `sessions`.
- **Effort:** low. **Acceptance:** reasoning ratio renders with a band; clicking a costliest session
  opens its breakdown; 0 console errors; works in `demo`.

### 2. Budgets + local alerts

- **Why:** matches their monthly + per‑session budgets; high day‑to‑day value.
- **What:** a `budgets.json` (monthly cap + optional per‑project/per‑session caps); `collect` evaluates
  spend vs. cap and writes a status; dashboard shows a budget bar; optional local notification
  (macOS `osascript`, Linux `notify-send`, Windows toast — all stdlib/OS, no deps) at threshold %.
- **Effort:** low–medium. **Acceptance:** a cap is read, status shown, threshold fires a local
  notification once per period; no network.

## v0.3 — operational parity

### 3. Read‑only MCP server

- **Why:** lets an agent query its own usage/budget, like theirs.
- **What:** a small stdlib MCP over the JSON already emitted — tools e.g. `usage`, `sessions`,
  `budget`, `stats`. Read‑only; returns derived numbers only (no prompts/responses/paths).
- **Effort:** medium. **Acceptance:** an MCP client can read totals, a session, and budget state;
  nothing writable exposed; localhost only.

### 4. Git integration (pushes ↔ spend)

- **Why:** "cost per shipped change," local‑only — fits the privacy stance.
- **What:** read local `git log` / reflog in the active project(s), attribute equivalent spend to the
  day/branch of successful pushes; a "by commit/day" view. Local git evidence only, never remote.
- **Effort:** medium. **Acceptance:** spend attributes to pushes for a repo with history; no remote
  calls; handles non‑git dirs gracefully.

## v0.4 — breakdown depth

### 5. Subagents + Tools breakdown

- **Why:** matches their Subagents and Tools pages.
- **What:** parse `tool_use` / subagent signals already present in Claude Code's JSONL into two tables
  — tool calls (counts, failures, repeats) and a subagent/role hierarchy over time.
- **Effort:** medium. **Acceptance:** both tables populate from real logs; totals reconcile with the
  session totals.

## v0.5 — multi‑agent proof

### 6. A second agent (Codex or Cursor)

- **Why:** turns "single‑agent" into "multi‑agent" without a rewrite.
- **What:** generalize the collector behind a small per‑agent log‑format adapter; add one more agent's
  local store; agent becomes a dimension on existing views.
- **Effort:** medium–high. **Acceptance:** a second agent's usage appears alongside Claude with correct
  pricing; Claude path unchanged.

## v1.0 — distribution polish

### 7. Native tray app + `pipx` / Docker packaging

- **Why:** lowest analytical value, highest convenience; last.
- **What:** `pipx install` and a Docker image for the backend; an optional minimal menu‑bar/tray
  launcher (kept optional so the stdlib‑only core stays intact).
- **Effort:** high. **Acceptance:** `pipx install super-token-meter && super-token-meter serve` works
  on all three OSes; tray is optional and never required.

## Explicit non‑goals

- No cloud backend, no hosted/SaaS mode, no account system.
- No telemetry or usage analytics phoned home, ever.
- No required third‑party service to read or price your own usage.
- No heavy runtime dependencies in the core (a tray/packaging extra may add some, but `serve` /
  `collect` / `proxy` stay stdlib‑only).
