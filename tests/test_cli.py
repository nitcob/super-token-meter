"""Dependency-free tests for the CLI dispatch (super_token_meter.__main__).
Covers the non-blocking subcommands; serve/demo/proxy are exercised by the
docker build+smoke job in CI (they bind a socket and block).
Run: python3 tests/test_cli.py  (or pytest)."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
from super_token_meter import __main__ as cli  # noqa: E402


def test_no_command_prints_help_and_returns_zero():
    assert cli.main([]) == 0


def test_version_flag_exits_zero():
    try:
        cli.main(["--version"])  # argparse 'version' action raises SystemExit(0)
        raise AssertionError("expected SystemExit from --version")
    except SystemExit as e:
        assert e.code in (0, None), e.code


def test_aggregate_dispatch_writes_zero_doc_when_no_log():
    td = tempfile.mkdtemp()
    rc = cli.main(["aggregate", "--data-dir", td])
    assert rc in (0, None), rc
    out = os.path.join(td, "local_usage.json")
    assert os.path.exists(out), "aggregate should write local_usage.json even with no usage log"
    assert json.load(open(out))["totals"]["requests"] == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"ALL PASS ({len(fns)} tests)")
