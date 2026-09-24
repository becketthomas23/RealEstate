import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.access import validate_access_configuration
from backend.api.main import app


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


class AccessControlTests(unittest.TestCase):
    protected_environment = {
        "APP_REQUIRE_AUTH": "true",
        "APP_ACCESS_PASSWORD": "test-password",
        "APP_SESSION_SECRET": "test-session-secret",
        "APP_SESSION_COOKIE_SECURE": "false",
    }

    def test_protected_api_requires_a_valid_password_session(self) -> None:
        with patch.dict(os.environ, self.protected_environment, clear=False):
            with TestClient(app) as client:
                self.assertEqual(client.post("/v1/underwriting", json=UNDERWRITING_REQUEST).status_code, 401)
                self.assertEqual(client.post("/v1/auth/login", json={"password": "wrong"}).status_code, 401)
                self.assertEqual(client.post("/v1/auth/login", json={"password": "test-password"}).json(), {"authenticated": True})
                self.assertEqual(client.post("/v1/underwriting", json=UNDERWRITING_REQUEST).status_code, 200)

    def test_protected_mode_fails_closed_when_secrets_are_missing(self) -> None:
        with patch.dict(os.environ, {"APP_REQUIRE_AUTH": "true"}, clear=True):
            with self.assertRaises(RuntimeError):
                validate_access_configuration()
