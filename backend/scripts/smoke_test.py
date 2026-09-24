"""Verify a deployed application without modifying its saved deal data."""

from __future__ import annotations

import argparse
import json
import os
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener


UNDERWRITING_REQUEST = {
    "purchase_price": "1000000",
    "closing_cost_rate": "0.02",
    "loan_to_value": "0.60",
    "annual_interest_rate": "0",
    "amortization_years": 5,
    "exit_cap_rate": "0.10",
    "selling_cost_rate": "0.02",
    "operating": {
        "current_potential_gross_income": "200000",
        "current_operating_expenses": "50000",
        "vacancy_rate": "0.10",
        "rent_growth_rate": "0",
        "expense_growth_rate": "0",
        "hold_period_years": 5,
    },
}


def request(opener, url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, str, dict | None]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    with opener.open(Request(url, data=body, headers=headers, method=method), timeout=15) as response:
        response_body = response.read().decode()
        content_type = response.headers.get_content_type()
        return response.status, content_type, json.loads(response_body) if content_type == "application/json" else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test a deployed CRE price solver.")
    parser.add_argument("base_url", help="Public application URL, for example https://cre-price-solver.onrender.com")
    parser.add_argument("--password", default=os.getenv("SMOKE_TEST_PASSWORD"), help="Optional shared password; prefer SMOKE_TEST_PASSWORD")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    try:
        health_status, _, health = request(opener, f"{base_url}/health")
        site_status, site_type, _ = request(opener, f"{base_url}/")
        if args.password:
            login_status, _, login = request(opener, f"{base_url}/v1/auth/login", method="POST", payload={"password": args.password})
            if login_status != 200 or login != {"authenticated": True}:
                raise SystemExit(f"Sign-in check failed: status={login_status}, body={login}")
        calculation_status, _, calculation = request(opener, f"{base_url}/v1/underwriting", method="POST", payload=UNDERWRITING_REQUEST)
    except (HTTPError, URLError, TimeoutError) as error:
        raise SystemExit(f"Smoke test failed: {error}") from error

    if health_status != 200 or health != {"status": "ok"}:
        raise SystemExit(f"Health check failed: status={health_status}, body={health}")
    if site_status != 200 or site_type != "text/html":
        raise SystemExit(f"Frontend check failed: status={site_status}, content-type={site_type}")
    if calculation_status != 200 or calculation is None or calculation.get("terminal_noi") != "130000.00":
        raise SystemExit(f"Underwriting check failed: status={calculation_status}, body={calculation}")

    print("Smoke test passed: protected access, frontend, health endpoint, and underwriting calculation are working.")


if __name__ == "__main__":
    main()
