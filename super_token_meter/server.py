"""server.py -- Super Token Meter: tiny stdlib web server for the local dashboard.

Serves the single-file dashboard at `/` and the generated JSON at `/data/*`, bound to
127.0.0.1 by default. No external deps, no telemetry, no outbound calls.
"""
import http.server
import os
import threading
import webbrowser

_HERE = os.path.dirname(os.path.abspath(__file__))
_DASHBOARD = os.path.join(_HERE, "dashboard")


def _make_handler(data_dir):
    dash_root = os.path.realpath(_DASHBOARD)
    data_root = os.path.realpath(data_dir)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def translate_path(self, path):
            path = path.split("?", 1)[0].split("#", 1)[0]
            if path in ("/", ""):
                return os.path.join(_DASHBOARD, "index.html")
            if path.startswith("/data/"):
                base, rel = data_root, path[len("/data/"):]
            else:
                base, rel = dash_root, path.lstrip("/")
            full = os.path.realpath(os.path.join(base, rel))
            # deny path traversal outside the intended root
            if full != base and not full.startswith(base + os.sep):
                return os.path.join(_DASHBOARD, "index.html")
            return full

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    return Handler


def serve(host="127.0.0.1", port=8722, data_dir=None, open_browser=True):
    data_dir = data_dir or os.path.expanduser("~/.super-token-meter/data")
    os.makedirs(data_dir, exist_ok=True)
    httpd = http.server.ThreadingHTTPServer((host, port), _make_handler(data_dir))
    url = f"http://{host}:{port}/"
    print(f"[super-token-meter] dashboard at {url}  (data: {data_dir})")
    print("[super-token-meter] local-first: 127.0.0.1 only, no telemetry. Ctrl+C to stop.")
    if open_browser:
        try:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[super-token-meter] stopped.")
