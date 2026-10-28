import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.api.main as api_main
from backend.api.access import hash_password, password_matches, validate_access_configuration
from backend.persistence import Database


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

PROTECTED_ENVIRONMENT = {
    "APP_REQUIRE_AUTH": "true",
    "APP_SESSION_SECRET": "test-session-secret",
    "APP_SESSION_COOKIE_SECURE": "false",
    "APP_ADMIN_EMAIL": "Admin@Example.com",
    "APP_ADMIN_NAME": "Demo Admin",
    "APP_ADMIN_PASSWORD": "demo-password-1",
}


class PasswordHashingTests(unittest.TestCase):
    def test_hashes_are_salted_and_verify(self) -> None:
        first, second = hash_password("correct horse"), hash_password("correct horse")
        self.assertNotEqual(first, second)
        self.assertTrue(password_matches("correct horse", first))
        self.assertFalse(password_matches("wrong", first))
        self.assertFalse(password_matches("correct horse", "not-a-hash"))

    def test_rejects_short_passwords(self) -> None:
        with self.assertRaisesRegex(ValueError, "8 characters"):
            hash_password("short")


class AccessControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.original_database = api_main.database
        api_main.database = Database(f"sqlite:///{(Path(self.temp_directory.name) / 'auth.db').as_posix()}")
        self.environment = patch.dict(os.environ, PROTECTED_ENVIRONMENT, clear=False)
        self.environment.start()
        self.client_context = TestClient(api_main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.environment.stop()
        api_main.database.dispose()
        api_main.database = self.original_database
        self.temp_directory.cleanup()

    def sign_in(self, email="admin@example.com", password="demo-password-1"):
        return self.client.post("/v1/auth/login", json={"email": email, "password": password})

    def test_bootstraps_the_first_admin_and_requires_sign_in(self) -> None:
        self.assertEqual(self.client.post("/v1/underwriting", json=UNDERWRITING_REQUEST).status_code, 401)
        session = self.client.get("/v1/auth/session").json()
        self.assertEqual(session, {"required": True, "authenticated": False, "user": None})
        self.assertEqual(self.sign_in(password="wrong").status_code, 401)

        signed_in = self.sign_in()

        self.assertEqual(signed_in.status_code, 200)
        self.assertEqual(signed_in.json()["user"]["email"], "admin@example.com")
        self.assertEqual(signed_in.json()["user"]["role"], "admin")
        self.assertEqual(self.client.post("/v1/underwriting", json=UNDERWRITING_REQUEST).status_code, 200)
        session = self.client.get("/v1/auth/session").json()
        self.assertTrue(session["authenticated"])
        self.assertEqual(session["user"]["name"], "Demo Admin")
        self.assertEqual(self.client.post("/v1/auth/logout").json(), {"authenticated": False})
        self.assertEqual(self.client.post("/v1/underwriting", json=UNDERWRITING_REQUEST).status_code, 401)

    def test_admin_manages_users_and_analysts_cannot(self) -> None:
        self.sign_in()
        created = self.client.post("/v1/users", json={"email": "analyst@example.com", "name": "Avery Analyst", "password": "analyst-pass-1"})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["role"], "analyst")
        self.assertEqual(self.client.post("/v1/users", json={"email": "analyst@example.com", "name": "Dup", "password": "analyst-pass-1"}).status_code, 409)
        self.assertEqual(len(self.client.get("/v1/users").json()), 2)
        admin_id = self.client.get("/v1/auth/session").json()["user"]["id"]
        self.assertEqual(self.client.patch(f"/v1/users/{admin_id}", json={"is_active": False}).status_code, 400)
        self.client.post("/v1/auth/logout")

        self.sign_in("analyst@example.com", "analyst-pass-1")
        self.assertEqual(self.client.get("/v1/users").status_code, 403)
        deal = self.client.post("/v1/deals", json={"name": "Analyst deal"})
        self.assertEqual(deal.status_code, 201)
        self.assertEqual(deal.json()["created_by"], "analyst@example.com")
        version = self.client.post(f"/v1/deals/{deal.json()['id']}/assumption-sets", json={"underwriting": UNDERWRITING_REQUEST})
        self.assertEqual(version.json()["created_by"], "analyst@example.com")
        changed = self.client.post("/v1/auth/password", json={"current_password": "analyst-pass-1", "new_password": "analyst-pass-2"})
        self.assertEqual(changed.status_code, 200)
        self.client.post("/v1/auth/logout")
        self.assertEqual(self.sign_in("analyst@example.com", "analyst-pass-1").status_code, 401)
        self.assertEqual(self.sign_in("analyst@example.com", "analyst-pass-2").status_code, 200)
        self.client.post("/v1/auth/logout")

        self.sign_in()
        deactivated = self.client.patch(f"/v1/users/{created.json()['id']}", json={"is_active": False})
        self.assertFalse(deactivated.json()["is_active"])
        self.client.post("/v1/auth/logout")
        self.assertEqual(self.sign_in("analyst@example.com", "analyst-pass-2").status_code, 401)


class AccessConfigurationTests(unittest.TestCase):
    def test_protected_mode_fails_closed_when_the_session_secret_is_missing(self) -> None:
        with patch.dict(os.environ, {"APP_REQUIRE_AUTH": "true"}, clear=True):
            with self.assertRaises(RuntimeError):
                validate_access_configuration()

    def test_open_mode_reports_that_sign_in_is_not_required(self) -> None:
        with patch.dict(os.environ, {"APP_REQUIRE_AUTH": "false"}, clear=False):
            with TestClient(api_main.app) as client:
                self.assertEqual(client.get("/v1/auth/session").json(), {"required": False, "authenticated": True, "user": None})
                self.assertEqual(client.post("/v1/auth/login", json={"email": "a@b.c", "password": "x"}).status_code, 400)
                self.assertEqual(client.get("/v1/users").status_code, 400)
