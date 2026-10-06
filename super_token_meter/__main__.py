"""Super Token Meter CLI.

  python3 -m super_token_meter serve      # collect + open the local dashboard
  python3 -m super_token_meter collect    # just refresh the data (for a scheduler)
  python3 -m super_token_meter demo        # render bundled sample data (no real logs)
  python3 -m super_token_meter proxy       # log a local LLM's usage (Ollama/OpenAI-compat)
  python3 -m super_token_meter aggregate   # roll the proxy log into local_usage.json

Local-first: reads local files only, binds 127.0.0.1, no API key, no network (except an
optional, user-triggered pricing refresh).
"""
import argparse
import os
import shutil
import sys

from . import __version__, collector, server

_DEFAULT_DATA = os.environ.get("STM_DATA_DIR", os.path.expanduser("~/.super-token-meter/data"))
_HERE = os.path.dirname(os.path.abspath(__file__))
_EXAMPLES = os.path.join(os.path.dirname(_HERE), "examples")


def _run(mod, argv):
    old = sys.argv
    sys.argv = [getattr(mod, "__name__", "stm")] + argv
    try:
        return mod.main()
    finally:
        sys.argv = old


def build_parser():
    ap = argparse.ArgumentParser(
        prog="super-token-meter",
        description="Local-first, private AI token usage & cost dashboard. No API key, no cloud.")
    ap.add_argument("--version", action="version", version=f"super-token-meter {__version__}")
    # shared option so `<cmd> --data-dir X` works (argparse needs it on each subparser)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", default=_DEFAULT_DATA,
                        help="where data is stored/read (default: ~/.super-token-meter/data)")
    sub = ap.add_subparsers(dest="cmd")

    c = sub.add_parser("collect", parents=[common], help="parse ~/.claude logs -> claude_usage.json")
    c.add_argument("--full", action="store_true", help="reparse everything (ignore incremental state)")

    s = sub.add_parser("serve", parents=[common], help="collect, then open the local dashboard")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8722)
    s.add_argument("--no-collect", action="store_true", help="serve existing data without re-collecting")
    s.add_argument("--no-browser", action="store_true")

    d = sub.add_parser("demo", parents=[common], help="render bundled sample data (no real logs needed)")
    d.add_argument("--port", type=int, default=8722)
    d.add_argument("--no-browser", action="store_true")

    p = sub.add_parser("proxy", parents=[common], help="log a local LLM's token usage (Ollama/OpenAI-compatible)")
    p.add_argument("--upstream", default=os.environ.get("STM_UPSTREAM", "http://127.0.0.1:11434"))
    p.add_argument("--listen", default=os.environ.get("STM_LISTEN", "127.0.0.1:11435"))

    sub.add_parser("aggregate", parents=[common], help="roll the proxy log into local_usage.json")
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 0

    data_dir = a.data_dir
    os.makedirs(data_dir, exist_ok=True)
    out = os.path.join(data_dir, "claude_usage.json")
    state = os.path.join(data_dir, ".cc_state.json")

    if a.cmd == "collect":
        return _run(collector, ["--output", out, "--state", state] + (["--full"] if a.full else []))

    if a.cmd == "serve":
        if not a.no_collect:
            _run(collector, ["--output", out, "--state", state])
        server.serve(a.host, a.port, data_dir, open_browser=not a.no_browser)
        return 0

    if a.cmd == "demo":
        copied = 0
        for fn in ("claude_usage.json", "local_usage.json"):
            src = os.path.join(_EXAMPLES, fn)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(data_dir, fn))
                copied += 1
        print(f"[super-token-meter] demo: copied {copied} sample file(s) -> {data_dir}")
        server.serve("127.0.0.1", a.port, data_dir, open_browser=not a.no_browser)
        return 0

    if a.cmd == "proxy":
        os.environ["UPSTREAM"] = a.upstream
        os.environ["LISTEN"] = a.listen
        os.environ["LOG_PATH"] = os.path.join(data_dir, "usage.jsonl")
        os.environ["AGG_OUTPUT"] = os.path.join(data_dir, "local_usage.json")
        os.environ.setdefault("INJECT_USAGE", "1")
        from . import proxy  # lazy: reads env at import
        return proxy.main()

    if a.cmd == "aggregate":
        from . import aggregate
        return _run(aggregate, ["--log", os.path.join(data_dir, "usage.jsonl"),
                                 "--output", os.path.join(data_dir, "local_usage.json")])
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
