"""Write frontend/config.js from an API URL (used after sam deploy)."""

from __future__ import annotations

import argparse
from pathlib import Path

TEMPLATE = """window.APP_CONFIG = {{
  apiUrl: {url!r},
}};
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("api_url", help="Full POST URL, e.g. https://abc.execute-api.us-east-1.amazonaws.com/prod/contact")
    args = parser.parse_args()
    dest = Path(__file__).resolve().parents[1] / "frontend" / "config.js"
    dest.write_text(TEMPLATE.format(url=args.api_url.strip()), encoding="utf-8")
    print(f"Wrote {dest}")


if __name__ == "__main__":
    main()
