"""Dependency-free tests for the collector. Run: python3 tests/test_collector.py (or pytest)."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
COLLECTOR = os.path.join(REPO, "super_token_meter", "collector.py")
FIXTURES = os.path.join(HERE, "fixtures")


def _collect():
    td = tempfile.mkdtemp()
    out = os.path.join(td, "o.json")
    subprocess.run([sys.executable, COLLECTOR, "--root", FIXTURES, "--output", out,
                    "--state", os.path.join(td, "s.json"), "--full"], check=True, cwd=REPO)
    return json.load(open(out))


def test_totals():
    t = _collect()["totals"]
    assert t["requests"] == 2, t["requests"]              # 2 assistant msgs (user + <synthetic> excluded)
    assert t["input_tokens"] == 15
    assert t["output_tokens"] == 150
    assert t["cache_read_tokens"] == 1500
    assert t["thinking_tokens"] == 20


def test_model_normalization_and_skip():
    by_model = set(_collect()["by_model"])
    # date suffix stripped (claude-haiku-4-5-20251001 -> claude-haiku-4-5); <synthetic> excluded
    assert by_model == {"claude-opus-5", "claude-haiku-4-5"}, by_model


def test_cost_and_pricing():
    d = _collect()
    # opus-5: 10*5 + 100*25 + 1000*0.5 + 200*6.25 + 300*10 = 7300  ;  haiku: 5*1 + 50*5 + 500*0.1 = 305
    assert abs(d["totals"]["cost_usd"] - 0.007605) < 1e-6, d["totals"]["cost_usd"]
    assert d["pricing"]["verified_date"], "pricing must carry a verified_date"
    assert d["unpriced_models"] == [], d["unpriced_models"]


def test_project_and_sessions():
    d = _collect()
    assert "demoproj" in d["by_project"], list(d["by_project"])
    assert d["totals"]["sessions"] == 1, d["totals"]["sessions"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"ALL PASS ({len(fns)} tests)")
