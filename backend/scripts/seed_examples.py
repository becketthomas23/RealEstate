"""Fill a Deal Scope pipeline with fictional example deals.

Each example is a complete deal: a named property with supporting detail, one
or two immutable assumption versions, and a solved maximum price, so the Deals
page shows a realistic pipeline for a demonstration or a fresh install. The
same deals are written as importable Excel files by build_demo_examples.py.

    uv run python scripts/seed_examples.py http://127.0.0.1:8000 --reset
    uv run python scripts/seed_examples.py https://your-host --email you@firm.com

With ``--reset`` every existing deal is deleted first. Credentials are read
from ``--email`` / ``--password`` or ``SEED_EMAIL`` / ``SEED_PASSWORD`` when
the deployment requires sign-in. Every property, firm, and figure is invented.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.examples import EXAMPLE_DEALS as EXAMPLES  # noqa: E402


class Client:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(self, path: str, *, method: str | None = None, payload: dict | None = None) -> tuple[int, object]:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if body else {}
        request = Request(self.base_url + path, data=body, headers=headers, method=method or ("POST" if body else "GET"))
        try:
            with self.opener.open(request, timeout=120) as response:
                raw = response.read()
                return response.status, (json.loads(raw) if raw else None)
        except HTTPError as error:
            raw = error.read()
            try:
                return error.code, json.loads(raw)
            except ValueError:
                return error.code, raw.decode(errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base_url", help="API origin, e.g. http://127.0.0.1:8000")
    parser.add_argument("--email", default=os.getenv("SEED_EMAIL"), help="Account email when sign-in is required; prefer SEED_EMAIL")
    parser.add_argument("--password", default=os.getenv("SEED_PASSWORD"), help="Account password; prefer SEED_PASSWORD")
    parser.add_argument("--reset", action="store_true", help="Delete every existing deal before seeding")
    args = parser.parse_args()

    client = Client(args.base_url)
    try:
        status, session = client.call("/v1/auth/session")
    except URLError as error:
        print(f"Cannot reach {args.base_url}: {error.reason}", file=sys.stderr)
        return 1
    if status != 200:
        print(f"Unexpected session response {status}: {session}", file=sys.stderr)
        return 1
    if session["required"] and not session["authenticated"]:
        if not (args.email and args.password):
            print("This deployment requires sign-in; pass --email and --password (or SEED_EMAIL / SEED_PASSWORD).", file=sys.stderr)
            return 1
        status, body = client.call("/v1/auth/login", payload={"email": args.email, "password": args.password})
        if status != 200:
            print(f"Sign-in failed ({status}): {body}", file=sys.stderr)
            return 1
        print(f"Signed in as {body['user']['email']}")

    if args.reset:
        status, deals = client.call("/v1/deals")
        if status != 200:
            print(f"Could not list deals ({status}): {deals}", file=sys.stderr)
            return 1
        for deal in deals:
            status, body = client.call(f"/v1/deals/{deal['id']}", method="DELETE")
            if status != 204:
                print(f"Could not delete {deal['name']} ({status}): {body}", file=sys.stderr)
                return 1
        print(f"Deleted {len(deals)} existing deal(s)")

    for example in EXAMPLES:
        status, deal = client.call("/v1/deals", payload={"name": example["name"]})
        if status != 201:
            print(f"Could not create {example['name']} ({status}): {deal}", file=sys.stderr)
            return 1
        for version in example["versions"]:
            status, saved = client.call(f"/v1/deals/{deal['id']}/assumption-sets", payload=version)
            if status != 201:
                print(f"Could not save version for {example['name']} ({status}): {saved}", file=sys.stderr)
                return 1
            status, solved = client.call(f"/v1/assumption-sets/{saved['id']}/maximum-price", payload=example["targets"])
            if status != 201:
                print(f"Could not solve {example['name']} ({status}): {solved}", file=sys.stderr)
                return 1
            result = solved["result"]
            price = float(result["maximum_purchase_price"])
            print(f"{example['name']:<30} v{saved['version']} {version['label']:<20} max price ${price:>14,.0f}  bound by {result['binding_constraint']}")
    print(f"Seeded {len(EXAMPLES)} example deal(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
