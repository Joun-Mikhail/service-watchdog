"""Local test services that fail in different ways, for demos and end-to-end tests.

    python demo/lab.py                                         # terminal 1
    python watchdog.py --config demo/config.yaml --dry-run     # terminal 2

Every service listens on 127.0.0.1 only. The TLS service needs the openssl CLI
and is skipped if it is not installed.
"""

from __future__ import annotations

import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HEALTHY_PAGE = "<h1>Welcome to the demo shop</h1>"

DEFAULT_PORTS = {
    "healthy": 8081,
    "error": 8082,
    "slow": 8083,
    "maintenance": 8084,
    "flaky": 8085,
    "tls": 8443,
}


class LabHandler(BaseHTTPRequestHandler):
    """Base handler; subclasses set `behaviour`."""

    behaviour = "healthy"
    slow_seconds = 1.5
    flaky_failures = 3

    def do_GET(self):
        """Respond according to the service's failure mode."""
        if self.behaviour == "error":
            self._reply(503, "Service Unavailable")
        elif self.behaviour == "slow":
            time.sleep(self.slow_seconds)
            self._reply(200, HEALTHY_PAGE)
        elif self.behaviour == "maintenance":
            self._reply(200, "<h1>Down for scheduled maintenance</h1>")
        elif self.behaviour == "flaky":
            with self.server.lock:
                self.server.requests += 1
                failing = self.server.requests <= self.flaky_failures
            self._reply(500 if failing else 200, "Internal Server Error" if failing else HEALTHY_PAGE)
        else:
            self._reply(200, HEALTHY_PAGE)

    def _reply(self, status, body):
        """Send an HTML response."""
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        """Silence per-request logging."""


def _self_signed_context(workdir):
    """Create a throwaway self-signed certificate and return a server SSLContext, or None."""
    if not shutil.which("openssl"):
        return None
    cert, key = os.path.join(workdir, "cert.pem"), os.path.join(workdir, "key.pem")
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-keyout",
            key,
            "-out",
            cert,
        ],
        check=True,
        capture_output=True,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    return context


def start(ports=None):
    """Start every lab service in background threads.

    ports maps service name to port; port 0 picks a free port. Returns a dict of
    service name to base URL, and a stop() function.
    """
    ports = dict(DEFAULT_PORTS if ports is None else ports)
    workdir = tempfile.mkdtemp(prefix="watchdog-lab-")
    servers, urls = [], {}

    for name, port in ports.items():
        scheme = "http"
        handler = type(f"{name.title()}Handler", (LabHandler,), {"behaviour": name})
        server = ThreadingHTTPServer(("127.0.0.1", port), handler)
        server.daemon_threads = True
        server.lock, server.requests = threading.Lock(), 0

        if name == "tls":
            context = _self_signed_context(workdir)
            if context is None:
                server.server_close()
                continue
            server.socket = context.wrap_socket(server.socket, server_side=True)
            scheme = "https"

        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        urls[name] = f"{scheme}://127.0.0.1:{server.server_address[1]}/"

    def stop():
        for server in servers:
            server.shutdown()
            server.server_close()
        shutil.rmtree(workdir, ignore_errors=True)

    return urls, stop


def main():
    """Run the lab until Ctrl+C."""
    urls, stop = start()
    print("Demo lab running (Ctrl+C to stop):")
    for name, url in urls.items():
        print(f"  {name:<12} {url}")
    if "tls" not in urls:
        print("  tls          skipped (openssl not found)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
