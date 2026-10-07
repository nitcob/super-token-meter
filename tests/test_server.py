"""Dependency-free tests for the dashboard HTTP server (serving + path-traversal guard).
Run: python3 tests/test_server.py  (or pytest)."""
import http.client
import http.server
import json
import os
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
from super_token_meter import server  # noqa: E402


def _start():
    td = tempfile.mkdtemp()
    with open(os.path.join(td, "claude_usage.json"), "w") as fh:
        json.dump({"totals": {"requests": 7}}, fh)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), server._make_handler(td))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def _get(port, raw_path):
    # http.client sends the path largely as-is (unlike urllib, which would normalize
    # "../" client-side), so this actually exercises the server's own guard.
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request("GET", raw_path)
    r = c.getresponse()
    body = r.read()
    c.close()
    return r.status, body


def test_serves_index_and_data():
    httpd, port = _start()
    try:
        st, body = _get(port, "/")
        assert st == 200 and b"Super Token Meter" in body, (st, body[:80])
        st, body = _get(port, "/data/claude_usage.json")
        assert st == 200 and json.loads(body)["totals"]["requests"] == 7, (st, body[:80])
    finally:
        httpd.shutdown()


def test_path_traversal_is_blocked():
    httpd, port = _start()
    try:
        for bad in ("/data/../../../../../../etc/passwd",
                    "/../../../../../../etc/passwd",
                    "/data/..%2f..%2f..%2fetc%2fpasswd"):
            st, body = _get(port, bad)
            assert b"root:" not in body, f"traversal leaked a system file via {bad}"
            # the guard falls back to the dashboard, not the requested escape target
            assert b"Super Token Meter" in body or st in (403, 404), (bad, st, body[:60])
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok  ", fn.__name__)
    print(f"ALL PASS ({len(fns)} tests)")
