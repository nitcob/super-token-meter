# Contributing

Thanks for your interest! Super Token Meter is deliberately **small and dependency‑free** (Python standard library only) and **local‑first** (nothing leaves the machine). Please keep contributions in that spirit.

## Dev loop

```bash
git clone https://github.com/<you>/super-token-meter.git
cd super-token-meter
python3 -m super_token_meter demo       # render the dashboard with sample data
python3 tests/test_collector.py          # run tests (no pytest needed)
python3 scripts/make_examples.py         # regenerate synthetic sample data
```

## Ground rules

- **No new runtime dependencies** without discussion — stdlib only is a feature.
- **No telemetry / no outbound calls** except the existing optional pricing refresh.
- **Never commit real usage data or secrets.** Only the synthetic `examples/` data is allowed. CI runs `gitleaks`.
- **Benchmarks must stay honest** — anything presented as a target must cite an Anthropic source, or be clearly labeled a heuristic (see the dashboard's References/Definitions).
- Update `super_token_meter/pricing.json` (with `verified_date` + `source_url`) when prices change; don't hardcode rates in code.

## Good first issues

Adding a new agent parser (Codex, Cursor, …), the read‑only MCP server, budgets + local alerts, or cross‑platform scheduler templates. Open an issue to discuss the shape first.
