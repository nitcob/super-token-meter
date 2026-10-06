<!-- Thanks for contributing! Keep it small, dependency-free, and local-first. -->

## What & why

<!-- What does this change and why? Link any issue. -->

## Checklist

- [ ] No new runtime dependencies (standard library only)
- [ ] No telemetry / no new outbound calls (except the existing optional pricing refresh)
- [ ] No real usage data or secrets committed (only synthetic `examples/`)
- [ ] `python3 tests/test_collector.py` passes
- [ ] Any new "target" number cites an Anthropic source, or is labeled a heuristic
- [ ] Prices changed only in `super_token_meter/pricing.json` (with `verified_date` + `source_url`)

## Screenshots / notes

<!-- Optional. For dashboard changes, a screenshot helps. -->
