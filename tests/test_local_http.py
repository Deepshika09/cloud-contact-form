"""In-process tests for local/server.py. Does not call AWS or bind a fixed port."""

from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from local.server import Handler  # noqa: E402


class LocalHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _post(self, payload, raw=None):
        body = raw if raw is not None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base + "/contact",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    def test_get_contact_explains_post(self):
        with urllib.request.urlopen(self.base + "/contact") as response:
            body = json.loads(response.read().decode())
        self.assertEqual(response.status, 200)
        self.assertTrue(body["ok"])
        self.assertIn("POST", body["message"])

    def test_serves_contact_form_html(self):
        with urllib.request.urlopen(self.base + "/") as response:
            html = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("Contact form", html)
        self.assertIn('id="name"', html)

    def test_valid_post_returns_ok(self):
        status, body = self._post(
            {
                "name": "Ada Lovelace",
                "email": "ada@example.com",
                "message": "Please send details about the contact form.",
            }
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertIn("id", body)

    def test_invalid_post_returns_field_errors(self):
        status, body = self._post({"name": "x", "email": "bad", "message": "no"})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        self.assertIn("name", body["fields"])
        self.assertIn("email", body["fields"])
        self.assertIn("message", body["fields"])

    def test_options_preflight(self):
        req = urllib.request.Request(self.base + "/contact", method="OPTIONS")
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 204)
            self.assertIn("Access-Control-Allow-Origin", response.headers)


if __name__ == "__main__":
    unittest.main()
