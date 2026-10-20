"""
Local development server (no AWS charges).

Serves the frontend and POSTs /contact through the same Lambda handler used in AWS.

  python local/server.py
  Then open http://127.0.0.1:8080
"""

from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

from handler import lambda_handler  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _api_path(self) -> str:
        return self.path.split("?", 1)[0].rstrip("/")

    def do_GET(self) -> None:  # noqa: N802
        if self._api_path() == "/contact":
            payload = json.dumps(
                {
                    "ok": True,
                    "service": "cloud-contact-form",
                    "message": "API is running. Submit the form with POST JSON: name, email, message.",
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self._api_path() == "/contact":
            self._write_lambda({"requestContext": {"http": {"method": "OPTIONS"}}})
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self._api_path() != "/contact":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8")
        event = {
            "body": body,
            "isBase64Encoded": False,
            "requestContext": {"http": {"method": "POST", "sourceIp": self.client_address[0]}},
        }
        self._write_lambda(event)

    def _write_lambda(self, event: dict) -> None:
        context = SimpleNamespace(aws_request_id="local")
        result = lambda_handler(event, context)
        status = int(result.get("statusCode", 500))
        headers = result.get("headers") or {}
        body = result.get("body") or ""
        if isinstance(body, str):
            payload = body.encode("utf-8")
        else:
            payload = json.dumps(body).encode("utf-8")

        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if status != 204:
            self.wfile.write(payload)


def main() -> None:
    host, port = "127.0.0.1", 8080
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Cloud Contact Form (local)  http://{host}:{port}")
    print("API endpoint                 http://{host}:{port}/contact".format(host=host, port=port))
    print("Press Ctrl+C to stop. DynamoDB is skipped unless CONTACT_TABLE is set.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()
