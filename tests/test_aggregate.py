"""Dependency-free tests for the local-LLM usage aggregator.
Run: python3 tests/test_aggregate.py  (or pytest)."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
from super_token_meter import aggregate  # noqa: E402


def _write_log(rows):
    td = tempfile.mkdtemp()
    log = os.path.join(td, "usage.jsonl")
    with open(log, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return td, log


def test_rollup_sums_and_groups_by_model():
    td, log = _write_log([
        {"ts": 1790000000, "model": "qwen2.5", "input_tokens": 40, "output_tokens": 200},
        {"ts": 1790000050, "model": "qwen2.5", "input_tokens": 10, "output_tokens": 20},
        {"ts": 1790000060, "model": "llama3.1", "input_tokens": 57, "output_tokens": 123},
    ])
    out = os.path.join(td, "local_usage.json")
    s = aggregate.aggregate(log, out)
    assert s["records"] == 3, s
    assert s["input_tokens"] == 107 and s["output_tokens"] == 343, s
    d = json.load(open(out))
    assert d["source"] == "local"
    assert d["totals"]["requests"] == 3
    assert set(d["by_model"]) == {"qwen2.5", "llama3.1"}, d["by_model"]
    assert d["by_model"]["qwen2.5"]["requests"] == 2
    assert d["by_model"]["qwen2.5"]["output_tokens"] == 220


def test_empty_and_missing_log_are_graceful():
    td, log = _write_log([])  # empty file exists
    out = os.path.join(td, "local_usage.json")
    s = aggregate.aggregate(log, out)
    assert s["records"] == 0 and json.load(open(out))["totals"]["requests"] == 0
    # a log path that does not exist at all must not raise
    s2 = aggregate.aggregate(os.path.join(td, "nope.jsonl"), out)
    assert s2["records"] == 0


def test_malformed_and_tsless_lines_are_skipped():
    td = tempfile.mkdtemp()
    log = os.path.join(td, "usage.jsonl")
    with open(log, "w") as fh:
        fh.write('{"ts":1790000000,"model":"m","input_tokens":5,"output_tokens":5}\n')
        fh.write("not json at all\n")
        fh.write('{"model":"m","input_tokens":9}\n')  # no ts -> skipped
        fh.write("\n")
    out = os.path.join(td, "local_usage.json")
    s = aggregate.aggregate(log, out)
    assert s["records"] == 1, s  # only the first valid, ts-bearing line counts


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"ALL PASS ({len(fns)} tests)")
