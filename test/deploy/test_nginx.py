"""NGINX_BIN=/path/to/nginx python -m unittest discover -s test/deploy -p test_nginx.py -v"""

import http.client
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NGINX = os.environ.get("NGINX_BIN") or shutil.which("nginx")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@unittest.skipUnless(NGINX, "Set NGINX_BIN to run the real Nginx integration test")
class NginxTest(unittest.TestCase):
    def test_routes_headers_compression_and_proxy(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = self.path.encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "public, max-age=7")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        backend = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=backend.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                static = root / "static"
                (static / "assets").mkdir(parents=True)
                (static / "index.html").write_text("SPA shell")
                (static / "logo.svg").write_text("<svg/>")
                (static / "assets/app-ABC12345.js").write_text(
                    'console.log("test");' * 300
                )
                (static / ".secret.js").write_text("secret")
                cert, key = root / "cert.pem", root / "key.pem"
                subprocess.run(
                    [
                        "openssl",
                        "req",
                        "-x509",
                        "-newkey",
                        "rsa:2048",
                        "-nodes",
                        "-subj",
                        "/CN=localhost",
                        "-days",
                        "1",
                        "-keyout",
                        str(key),
                        "-out",
                        str(cert),
                    ],
                    check=True,
                    capture_output=True,
                )
                http_port, https_port = free_port(), free_port()
                site = (ROOT / "deploy/nginx.conf").read_text()
                site = site.replace("listen 80;", f"listen 127.0.0.1:{http_port};")
                site = site.replace(
                    "listen 443 ssl;", f"listen 127.0.0.1:{https_port} ssl;"
                )
                site = site.replace(
                    "127.0.0.1:3000", f"127.0.0.1:{backend.server_port}"
                )
                site = site.replace(
                    "/var/www/random-2hu-stuff/frontend/dist", str(static)
                )
                site = site.replace(
                    "/etc/letsencrypt/live/random-2hu-stuff.randomneet.me/fullchain.pem",
                    str(cert),
                )
                site = site.replace(
                    "/etc/letsencrypt/live/random-2hu-stuff.randomneet.me/privkey.pem",
                    str(key),
                )
                site = site.replace(
                    "/var/log/nginx/random-2hu-stuff.access.log",
                    str(root / "access.log"),
                )
                site = site.replace(
                    "/var/log/nginx/random-2hu-stuff.error.log", str(root / "error.log")
                )
                config = root / "nginx.conf"
                config.write_text(
                    f"pid {root}/nginx.pid;\nerror_log {root}/error.log;\nevents {{}}\nhttp {{ access_log off; default_type text/plain; {site} }}"
                )
                result = subprocess.run(
                    [NGINX, "-e", "stderr", "-t", "-p", str(root), "-c", str(config)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                process = subprocess.Popen(
                    [
                        NGINX,
                        "-e",
                        "stderr",
                        "-p",
                        str(root),
                        "-c",
                        str(config),
                        "-g",
                        "daemon off;",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                try:
                    for _ in range(100):
                        try:
                            with socket.create_connection(
                                ("127.0.0.1", https_port), timeout=0.1
                            ):
                                break
                        except OSError:
                            time.sleep(0.02)

                    def request(path, headers=None):
                        conn = http.client.HTTPSConnection(
                            "127.0.0.1",
                            https_port,
                            context=ssl._create_unverified_context(),
                        )
                        conn.request("GET", path, headers=headers or {})
                        res = conn.getresponse()
                        body = res.read()
                        values = dict((k.lower(), v) for k, v in res.getheaders())
                        conn.close()
                        return res.status, values, body

                    for path in ("/", "/authors/123", "/index.html", "/logo.svg"):
                        status, headers, body = request(path)
                        self.assertEqual(status, 200, path)
                        self.assertEqual(headers["cache-control"], "no-cache")
                        self.assertEqual(headers["x-content-type-options"], "nosniff")
                    status, headers, _ = request(
                        "/assets/app-ABC12345.js", {"Accept-Encoding": "gzip"}
                    )
                    self.assertEqual(status, 200)
                    self.assertIn("immutable", headers["cache-control"])
                    self.assertEqual(headers["content-encoding"], "gzip")
                    self.assertEqual(headers["x-frame-options"], "DENY")
                    for path in (
                        "/assets/missing-ABC12345.js",
                        "/missing.js",
                        "/missing.png",
                    ):
                        status, headers, body = request(path)
                        self.assertEqual(status, 404)
                        self.assertNotIn("immutable", headers["cache-control"])
                        self.assertNotEqual(body, b"SPA shell")
                    self.assertEqual(request("/.secret.js")[0], 403)
                    for path in ("/api/test.js?q=1", "/api/test?q=2"):
                        status, headers, body = request(path)
                        self.assertEqual(status, 200)
                        self.assertEqual(body.decode(), path)
                        self.assertEqual(headers["cache-control"], "public, max-age=7")
                    self.assertEqual(request("/health")[1]["cache-control"], "no-store")
                finally:
                    process.terminate()
                    process.communicate(timeout=5)
        finally:
            backend.shutdown()
            backend.server_close()
