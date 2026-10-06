# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

_Nothing yet._

## [0.1.0] - 2026-10-06

Initial release.

### Added

- **Collector** — parses local Claude Code session logs (`~/.claude/projects/**/*.jsonl`),
  incrementally, with equivalent-cost pricing from a bundled `pricing.json` (exact cache
  5m/1h multipliers; date-suffixed model IDs normalized; unpriced models flagged).
- **Local dashboard** served on `127.0.0.1` — overview, efficiency KPIs with **grounded,
  cited benchmarks** (cost/active-day, cache-hit rate) and clearly-labeled heuristics, each with a
  "You" value; cost-by-token-type; efficiency-over-time; **model-mix what-if**; costliest sessions;
  by-model / by-project; and **group-by day / week / month / quarter / year**.
- **Cloud-vs-local privacy split** and an optional **local-LLM logging proxy**
  (Ollama / OpenAI-compatible) that preserves streaming and taps token counts.
- **CLI**: `serve`, `collect`, `demo`, `proxy`, `aggregate`. Python standard library only, no API key.
- **Cross-platform scheduled collection** — macOS launchd, Linux systemd, Windows Task Scheduler;
  the install scripts pass `--data-dir` explicitly so a custom `STM_DATA_DIR` is honored by the
  scheduled job.
- **Optional Docker image + `compose.yaml`** — localhost-only on the host (port mapped to
  `127.0.0.1`), zero runtime dependencies.
- Synthetic demo data (`examples/`) and tests.
- **CI**: cross-platform test matrix (Windows / macOS / Linux, Python 3.9 + 3.12),
  `ruff` + `mypy` lint (dev-only; runtime stays zero-dependency), `gitleaks` secrets scan, and a
  Docker build + smoke test.
- **Docs**: README, [`docs/COMPARISON.md`](docs/COMPARISON.md) (vs `splunk/token-meter`),
  [`ROADMAP.md`](ROADMAP.md) (features + a Stack & tooling policy), CONTRIBUTING, SECURITY, and
  pull-request / issue templates.

### Notes

- Equivalent cost is a **notional list-price yardstick** (Claude Code is usually subscription-flat),
  not a bill. Anthropic frames efficiency as **cost per task, not per token**.

[Unreleased]: https://github.com/nitcob/super-token-meter/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nitcob/super-token-meter/releases/tag/v0.1.0
