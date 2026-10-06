# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added

- CI status / License / stdlib-only / local-first badges in the README.
- Pull request template and issue templates (bug report, feature request).
- This changelog.

## [0.1.0] - 2026-10-06

Initial release.

### Added

- **Collector** — parses local Claude Code session logs (`~/.claude/projects/**/*.jsonl`),
  incrementally, with equivalent-cost pricing from a bundled `pricing.json`.
- **Local dashboard** served on `127.0.0.1` — overview, efficiency KPIs with grounded
  benchmarks (cost/active-day, cache-hit rate) and clearly-labeled heuristics, cost-by-token-type,
  model-mix what-if, costliest sessions, and group-by day/week/month/quarter/year.
- **Cloud-vs-local privacy split** and optional **local-LLM logging proxy** (Ollama / OpenAI-compatible).
- **CLI**: `serve`, `collect`, `demo`, `proxy`, `aggregate`. Standard library only, no API key.
- Synthetic demo data, tests, CI (compile + tests + gitleaks), and launchd/systemd templates.

[Unreleased]: https://github.com/nitcob/super-token-meter/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nitcob/super-token-meter/releases/tag/v0.1.0
