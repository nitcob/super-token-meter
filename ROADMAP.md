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

## Stack & tooling

"Are we modernizing the stack?" — **the runtime is deliberately _not_ modernized, and that is the
product.** Stdlib‑only, no framework, no build, no DB is what makes this auditable, zero‑install,
offline, cross‑platform, and private. Modernization happens in the **dev** and **distribution**
layers, which never touch the zero‑dependency runtime.

**Locked (do not change — this is the moat):**

- **Runtime:** Python standard library only (`dependencies = []`); `http.server` for serving.
- **Frontend:** one self‑contained static `index.html` — vanilla JS + inline SVG, **no framework,
  no bundler, no CDN**.
- **Data:** plain JSON files on disk — **no database**.

**Now (landed):**

- **`ruff`** (lint: pyflakes + import order) and **`mypy`** (lenient type‑check) run in CI as a
  dedicated `lint` job. They are **dev‑only** (`pip install -e ".[dev]"`); the shipped runtime stays
  zero‑dependency. Ruleset starts high‑signal/low‑noise and tightens over time.

**Planned (dev + distribution only):**

- **Distribution** (the real user‑facing modernization; tracked in v1.0): publish to **PyPI** →
  `pipx install` / `uv tool install`, plus a **Docker** image. Replaces "git clone + run a script".
- **Dev tooling:** tighten the `ruff` ruleset (add `E` / `UP` / `B`, then adopt `ruff format`); add
  coverage. Keep all of it dev‑only.
- **Python floor:** `requires-python = ">=3.9"`, but **3.9 reached end‑of‑life in Oct 2025** and modern
  tooling already drops it (e.g. `mypy` refuses `--python-version 3.9`). Plan a conscious bump to
  **3.11** (keeps broad reach, unlocks modern typing + speed) — a decision to make, not drift.
- **Frontend scaling rule:** as pages grow (v0.2+), **do not** adopt a SPA framework or bundler. If
  one HTML file stops being enough, split into a few **static files served as‑is** (still no build
  step), not React/Vite.
- **Data contract:** publish a documented **JSON schema** for the data files — helps the future MCP
  server and anyone scripting against `/data/`.

## Shipped — v0.1

Claude Code + local‑LLM collection · dashboard (Overview, Efficiency with grounded benchmarks,
Where‑the‑cost‑goes, Efficiency‑over‑time, model‑mix what‑if, Usage‑by‑period, privacy split,
by‑model / by‑project, costliest sessions, references) · bundled offline pricing with cache 5m/1h
multipliers · `demo` mode · cross‑platform scheduled collection (launchd / systemd / Task
Scheduler) · raw JSON served at `/data/`.

## Hardening backlog (from the v0.1 engineering review)

A principal‑level review scored v0.1 at **~72/100** — a clean, well‑CI'd foundation that is not yet
production‑hardened. These are the specific items to reach **~90+ ("I'd trust this in production")**,
ordered by points‑per‑effort. Several overlap the feature milestones below.

1. **Test depth → ~80% coverage (biggest win, +8–10).** Only `collector` is unit‑tested today;
   `proxy`, `aggregate`, `server`, and CLI routing have no in‑repo tests, and the ~630‑line dashboard
   JS (benchmark math, what‑if, period bucketing) is untested. Commit the proxy fake‑upstream harness,
   add `test_aggregate`/`test_server`, extract the dashboard math into a testable unit, and add a
   coverage gate in CI.
2. **Governance + supply‑chain pack (+4).** `dependabot.yml` (pip + actions), **pin GitHub Actions to
   SHAs** (not moving tags), `release.yml` (auto GitHub Release on tag), `CODEOWNERS`, `py.typed`,
   `.editorconfig`, `CODE_OF_CONDUCT.md`.
3. **Real type hints (+3).** Annotate public functions and the usage doc (`TypedDict`); take `mypy`
   off lenient once clean — today it passes trivially because nothing is annotated.
4. **Prove distribution (+2).** Publish to PyPI; add a CI step that installs the wheel and runs
   `super-token-meter --version`; document `pipx` / `uv tool` install. (See v1.0.)
5. **Docs polish (+2).** A dashboard screenshot/GIF in the README, an `ARCHITECTURE.md`, and a
   documented JSON schema for `/data/` (also unblocks the MCP).
6. **Robustness nits (+2).** Log swallowed exceptions (don't `except: pass` silently); verify the
   daily **date basis** is consistent between the cloud collector and the local aggregator; note
   state‑file concurrency.
7. **Python floor bump 3.9 → 3.11/3.12.** Verified 2026‑10‑06 via
   [endoflife.date/python](https://endoflife.date/python): **3.9 EOL'd 31 Oct 2025 and 3.10 on
   1 Oct 2026** — the current `3.9 + 3.12` matrix runs an EOL version. 3.11 is supported to Oct 2027,
   3.12 to Oct 2028.

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
