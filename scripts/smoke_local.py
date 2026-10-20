"""Smoke-test the local server. Does not call AWS."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8080"


def post(payload: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        BASE + "/contact",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def main() -> None:
    with urllib.request.urlopen(BASE + "/") as response:
        html = response.read()
        print("GET /", response.status, "bytes", len(html))
        assert b"Cloud Contact Form" in html

    status, body = post(
        {
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "message": "Please send internship details for the cloud track.",
        }
    )
    print("POST valid", status, body)
    assert status == 200 and body.get("ok") is True

    status, body = post({"name": "x", "email": "bad", "message": "no"})
    print("POST invalid", status, body)
    assert status == 400 and body.get("ok") is False and "fields" in body

    print("smoke ok")


if __name__ == "__main__":
    main()
