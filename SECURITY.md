# Security & Privacy

Super Token Meter is **local‑first by design**:

- It reads your Claude Code session logs from disk and serves a dashboard bound to **`127.0.0.1` only**.
- **No API key, no account, no telemetry, no analytics.** Nothing about your usage, prompts, code, paths, or costs leaves your machine.
- The only optional outbound call is a user‑triggered **pricing refresh** to Anthropic's public pricing page; bundled pricing works offline.
- No real usage data or secrets are committed to this repo (CI runs `gitleaks`; see `.gitignore`).

## Reporting a vulnerability

Please open a **private** security advisory on GitHub (Security → Advisories → Report a vulnerability) rather than a public issue. We'll acknowledge within a few days.

If you find usage data, credentials, or anything that should be local accidentally leaving the machine, that's a security bug — please report it.
