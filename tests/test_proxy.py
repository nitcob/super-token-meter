"""Dependency-free integration test for the local-LLM logging proxy.

Stands up a fake upstream (Ollama-native NDJSON + OpenAI-compatible SSE) and the real
proxy in front of it, then asserts: streamed bytes relay intact, token usage is logged
for both shapes, stream_options.include_usage is injected, and an unreachable upstream
yields a graceful 502. Run: python3 tests/test_proxy.py  (or pytest).
"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

_last_req = {}


class _Upstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            _last_req[self.path] = json.loads(raw)
        except Exception:
            _last_req[self.path] = None
        if self.path.startswith("/api/"):  # Ollama native (NDJSON)
            ctype = "application/x-ndjson"
            body = ("\n".join([
                json.dumps({"model": "llama3.1", "done": False, "message": {"content": "Hi"}}),
                json.dumps({"model": "llama3.1", "done": True, "prompt_eval_count": 57, "eval_count": 123}),
            ]) + "\n").encode()
        else:  # OpenAI-compatible (SSE)
            ctype = "text/event-stream"
            body = ("\n\n".join([
                'data: {"model":"qwen2.5","choices":[{"delta":{"content":"Hi"}}]}',
                'data: {"model":"qwen2.5","choices":[],"usage":{"prompt_tokens":40,"completion_tokens":200}}',
                "data: [DONE]",
            ]) + "\n\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Connection", "close")
        self.end_headers()
        for i in range(0, len(body), 8):  # dribble it out to mimic streaming
            self.wfile.write(body[i:i + 8])
            self.wfile.flush()


# --- start the fake upstream, THEN set env, THEN import the proxy (it reads env at import) ---
_UP = ThreadingHTTPServer(("127.0.0.1", 0), _Upstream)
_UP_PORT = _UP.server_address[1]
threading.Thread(target=_UP.serve_forever, daemon=True).start()

_TD = tempfile.mkdtemp()
_LOG = os.path.join(_TD, "usage.jsonl")
os.environ["UPSTREAM"] = f"http://127.0.0.1:{_UP_PORT}"
os.environ["LISTEN"] = "127.0.0.1:0"
os.environ["LOG_PATH"] = _LOG
os.environ["INJECT_USAGE"] = "1"
from super_token_meter import proxy  # noqa: E402

_SRV = proxy.Server(("127.0.0.1", 0), proxy.Handler)  # bind port 0 -> no LISTEN race
_PORT = _SRV.server_address[1]
threading.Thread(target=_SRV.serve_forever, daemon=True).start()


def _read_log():
    return [json.loads(x) for x in open(_LOG)] if os.path.exists(_LOG) else []


def _post(path, payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{_PORT}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def _wait_for(model):
    for _ in range(50):
        rows = [r for r in _read_log() if r.get("model") == model]
        if rows:
            return rows
        time.sleep(0.1)
    return []


def test_1_ollama_native_relays_and_logs():
    st, body = _post("/api/chat", {"model": "llama3.1", "stream": True, "messages": []})
    assert st == 200, (st, body[:120])
    assert "Hi" in body and '"eval_count":123' in body.replace(" ", ""), body[:200]
    rows = _wait_for("llama3.1")
    assert rows and rows[-1]["input_tokens"] == 57 and rows[-1]["output_tokens"] == 123, rows


def test_2_openai_compat_logs_and_injects_usage():
    st, body = _post("/v1/chat/completions", {"model": "qwen2.5", "stream": True, "messages": []})
    assert st == 200 and "[DONE]" in body, (st, body[:120])
    rows = _wait_for("qwen2.5")
    assert rows and rows[-1]["input_tokens"] == 40 and rows[-1]["output_tokens"] == 200, rows
    inj = (_last_req.get("/v1/chat/completions") or {}).get("stream_options") or {}
    assert inj.get("include_usage") is True, _last_req.get("/v1/chat/completions")


def test_3_upstream_down_returns_502():
    _UP.shutdown()
    _UP.server_close()  # fully free the port -> connection refused
    st, body = _post("/api/chat", {"model": "x", "stream": True})
    assert st == 502 and "unreachable" in body.lower(), (st, body[:120])
    assert _SRV.fileno() != -1  # proxy itself is still alive


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"ALL PASS ({len(fns)} tests)")
