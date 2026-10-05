#!/usr/bin/env python3
"""
proxy.py  --  Super Token Meter: transparent logging proxy for a local LLM

Purpose : Sit between a client (a coding agent or chat UI) and a local LLM server
          (Ollama or any OpenAI-compatible endpoint), relay every request/response
          byte-for-byte WITHOUT buffering (streaming UX preserved), and record per-inference
          token counts (prompt_eval_count / eval_count, or usage{}) to a JSONL. This is the
          reliable source of local-model token usage when the client doesn't expose it.
Config  : env UPSTREAM   (default http://127.0.0.1:11434)  -- the real LLM server (e.g. Ollama)
          env LISTEN     (default 127.0.0.1:11435)          -- where this proxy listens (localhost)
          env LOG_PATH   (default ~/.super-token-meter/data/usage.jsonl)  -- append-only usage log
Design  : stdlib only. If the upstream is unreachable the proxy returns 502 and logs it;
          it never crashes, so the client degrades gracefully (rollback is just repointing
          the client back to the direct upstream URL).
"""

import http.client
import http.server
import json
import os
import socketserver
import sys
import threading
import time
from urllib.parse import urlparse

UPSTREAM = os.environ.get("UPSTREAM", "http://127.0.0.1:11434")
LISTEN = os.environ.get("LISTEN", "127.0.0.1:11435")
LOG_PATH = os.environ.get("LOG_PATH", os.path.expanduser(os.path.join(os.environ.get("STM_DATA_DIR","~/.super-token-meter/data"),"usage.jsonl")))
# For OpenAI-compatible upstreams (LM Studio etc.), streamed responses only carry
# token `usage` when the client asks for it. Set INJECT_USAGE=1 so this proxy adds
# stream_options.include_usage to streaming /chat/completions requests.
INJECT_USAGE = os.environ.get("INJECT_USAGE", "0").lower() in ("1", "true", "yes")

_up = urlparse(UPSTREAM)
UP_HOST = _up.hostname or "127.0.0.1"
UP_PORT = _up.port or 11434
_l_host, _, _l_port = LISTEN.partition(":")
LISTEN_HOST = _l_host or "127.0.0.1"
LISTEN_PORT = int(_l_port or "11434")

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}
TAIL_CAP = 65536            # keep only the last 64 KiB to find the final usage line
BODY_CAP = 8 * 1024 * 1024  # max request body we buffer to forward

_log_lock = threading.Lock()


def log_line(obj):
    with _log_lock:
        try:
            os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
            with open(LOG_PATH, "a") as fh:
                fh.write(json.dumps(obj, separators=(",", ":")) + "\n")
        except Exception as e:
            sys.stderr.write(f"[ollama-logger] log write failed: {e}\n")


def stderr(msg):
    sys.stderr.write(f"[ollama-logger] [{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    sys.stderr.flush()


def extract_usage(tail_bytes, path):
    """Return (model, input_tokens, output_tokens) or None from a response tail.
    Handles Ollama native (/api/chat,/api/generate: prompt_eval_count/eval_count,
    whether streamed NDJSON or a single object) and OpenAI-compatible (/v1/...: usage{}).
    """
    try:
        text = tail_bytes.decode("utf-8", "replace")
    except Exception:
        return None
    best = None
    for line in text.splitlines():
        line = line.strip()
        if not line or not (line.startswith("{") or line.startswith("data:")):
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
            if line == "[DONE]":
                continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        model = obj.get("model")
        # Ollama native
        if "eval_count" in obj or "prompt_eval_count" in obj:
            best = (model, int(obj.get("prompt_eval_count", 0) or 0),
                    int(obj.get("eval_count", 0) or 0))
        # OpenAI-compatible
        u = obj.get("usage")
        if isinstance(u, dict) and ("completion_tokens" in u or "prompt_tokens" in u):
            best = (model, int(u.get("prompt_tokens", 0) or 0),
                    int(u.get("completion_tokens", 0) or 0))
    return best


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ollama-logger/1.0"

    def log_message(self, *a):
        pass  # quiet default access log; we do our own

    def _relay(self):
        method = self.command
        path = self.path
        # read request body (Content-Length only; Ollama clients set it)
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(min(length, BODY_CAP)) if length else None

        # Optionally force usage reporting on streaming OpenAI-compatible calls.
        if (body and INJECT_USAGE and method == "POST"
                and ("/chat/completions" in path or path.endswith("/completions"))):
            try:
                j = json.loads(body)
                if isinstance(j, dict) and j.get("stream") is True:
                    so = j.get("stream_options") or {}
                    if not so.get("include_usage"):
                        so["include_usage"] = True
                        j["stream_options"] = so
                        body = json.dumps(j).encode()
            except Exception:
                pass

        fwd_headers = {}
        for k, v in self.headers.items():
            if k.lower() in HOP_BY_HOP or k.lower() == "host":
                continue
            fwd_headers[k] = v
        fwd_headers["Host"] = f"{UP_HOST}:{UP_PORT}"
        if body is not None:
            fwd_headers["Content-Length"] = str(len(body))  # body may have been rewritten

        try:
            conn = http.client.HTTPConnection(UP_HOST, UP_PORT, timeout=900)
            conn.request(method, path, body=body, headers=fwd_headers)
            resp = conn.getresponse()
        except Exception as e:
            stderr(f"upstream error {method} {path}: {e}")
            msg = json.dumps({"error": f"ollama-logger upstream unreachable: {e}"}).encode()
            try:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(msg)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                pass
            self.close_connection = True
            return

        # mirror status + headers (drop hop-by-hop + length/encoding; we stream to EOF)
        self.send_response(resp.status)
        content_length = None
        for k, v in resp.getheaders():
            kl = k.lower()
            if kl in HOP_BY_HOP or kl == "content-length":
                continue
            self.send_header(k, v)
        if resp.getheader("Content-Length") is not None:
            content_length = resp.getheader("Content-Length")
            self.send_header("Content-Length", content_length)
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()

        tail = b""
        total = 0
        try:
            while True:
                # read1() returns each chunk as it arrives (read() would block trying
                # to fill the full buffer, defeating streaming).
                chunk = resp.read1(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
                total += len(chunk)
                tail = (tail + chunk)[-TAIL_CAP:]
        except (BrokenPipeError, ConnectionResetError):
            pass  # client hung up mid-stream; still try to log what we captured
        except Exception as e:
            stderr(f"relay error {method} {path}: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

        # tap usage for real inference endpoints only
        if method == "POST" and ("/api/chat" in path or "/api/generate" in path
                                 or "/chat/completions" in path or "/completions" in path
                                 or "/api/embed" in path):
            info = extract_usage(tail, path)
            if info:
                model, inp, out = info
                log_line({
                    "ts": int(time.time()),
                    "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "model": model,
                    "input_tokens": inp,
                    "output_tokens": out,
                    "endpoint": path,
                    "client": self.client_address[0],
                    "resp_bytes": total,
                })

    # route every verb through the relay
    do_GET = _relay
    do_POST = _relay
    do_PUT = _relay
    do_DELETE = _relay
    do_HEAD = _relay
    do_OPTIONS = _relay
    do_PATCH = _relay


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def aggregation_loop():
    """Roll usage.jsonl -> local_usage.json on a timer, so no external cron is needed.
    Controlled by AGG_OUTPUT (default alongside the log) and AGG_INTERVAL seconds."""
    out = os.environ.get("AGG_OUTPUT", os.path.join(os.path.dirname(LOG_PATH) or ".", "local_usage.json"))
    interval = int(os.environ.get("AGG_INTERVAL", "120") or "120")
    if interval <= 0:
        stderr("aggregation loop disabled (AGG_INTERVAL<=0) — this proxy only logs")
        return
    try:
        from . import aggregate as aggregate_local
    except Exception as e:
        stderr(f"aggregation disabled (import failed: {e})")
        return
    while True:
        try:
            s = aggregate_local.aggregate(LOG_PATH, out)
            stderr(f"aggregated -> {out}: records={s['records']} in={s['input_tokens']} out={s['output_tokens']}")
        except Exception as e:
            stderr(f"aggregation error: {e}")
        time.sleep(interval)


def main():
    stderr(f"listening on {LISTEN_HOST}:{LISTEN_PORT} -> upstream {UP_HOST}:{UP_PORT}; log={LOG_PATH}")
    t = threading.Thread(target=aggregation_loop, daemon=True)
    t.start()
    srv = Server((LISTEN_HOST, LISTEN_PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
