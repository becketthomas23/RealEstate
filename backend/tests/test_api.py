import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

import backend.api.main as api_main
from backend.api.main import app
from backend.persistence import Database


client = TestClient(app)

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


class ApiTests(unittest.TestCase):
    def test_health_check(self) -> None:
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_local_frontend_origin_is_allowed(self) -> None:
        response = client.options(
            "/v1/underwriting",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")

    def test_underwriting_endpoint_returns_precise_financial_values(self) -> None:
        response = client.post("/v1/underwriting", json=UNDERWRITING_REQUEST)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["terminal_noi"], "130000.00")
        self.assertEqual(body["annual_cash_flows"][-1], "1284000.00")
        self.assertEqual(body["returns"]["minimum_dscr"], "1.083333333333333333333333333")

    def test_maximum_price_endpoint_returns_dscr_limited_price(self) -> None:
        response = client.post(
            "/v1/maximum-price",
            json={
                "underwriting": UNDERWRITING_REQUEST,
                "target_levered_irr": "0.10",
                "minimum_dscr": "1.00",
                "minimum_purchase_price": "500000",
                "maximum_purchase_price": "1500000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertLess(abs(float(response.json()["maximum_purchase_price"]) - 1083333.33), 0.01)

    def test_sensitivity_endpoint_returns_one_way_price_cases(self) -> None:
        response = client.post(
            "/v1/sensitivities",
            json={
                "underwriting": UNDERWRITING_REQUEST,
                "target_levered_irr": "0.10",
                "minimum_dscr": "1.00",
                "minimum_purchase_price": "500000",
                "maximum_purchase_price": "1500000",
            },
        )

        self.assertEqual(response.status_code, 200)
        dimensions = response.json()["dimensions"]
        self.assertEqual([dimension["key"] for dimension in dimensions], ["rent_growth_rate", "exit_cap_rate", "annual_interest_rate"])
        self.assertEqual(dimensions[0]["points"][1]["label"], "Base")
        self.assertGreater(
            float(dimensions[0]["points"][2]["maximum_purchase_price"]),
            float(dimensions[0]["points"][0]["maximum_purchase_price"]),
        )

    def test_api_returns_validation_error_for_unbracketed_solver_range(self) -> None:
        response = client.post(
            "/v1/maximum-price",
            json={
                "underwriting": UNDERWRITING_REQUEST,
                "target_levered_irr": "0.10",
                "minimum_dscr": "0.50",
                "minimum_purchase_price": "500000",
                "maximum_purchase_price": "600000",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("higher bound", response.json()["detail"])


class PersistedUnderwritingApiTests(unittest.TestCase):
    """Exercise durable deal history separately from the stateless calculator endpoints."""

    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.original_database = api_main.database
        database_path = Path(self.temp_directory.name) / "underwriting.db"
        api_main.database = Database(f"sqlite:///{database_path.as_posix()}")
        self.client_context = TestClient(api_main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        api_main.database.dispose()
        api_main.database = self.original_database
        self.temp_directory.cleanup()

    def test_versions_inputs_and_results_are_persisted(self) -> None:
        deal = self.client.post("/v1/deals", json={"name": "Maple Apartments"})

        self.assertEqual(deal.status_code, 201)
        deal_id = deal.json()["id"]
        assumption_set = self.client.post(
            f"/v1/deals/{deal_id}/assumption-sets",
            json={
                "label": "IC base case",
                "source": "Broker OM",
                "effective_date": "2026-09-24",
                "confidence_level": "medium",
                "underwriting": UNDERWRITING_REQUEST,
            },
        )

        self.assertEqual(assumption_set.status_code, 201)
        assumptions = assumption_set.json()
        self.assertEqual(assumptions["version"], 1)
        self.assertEqual(assumptions["underwriting"]["purchase_price"], "1000000")

        calculation = self.client.post(f"/v1/assumption-sets/{assumptions['id']}/underwriting")

        self.assertEqual(calculation.status_code, 201)
        body = calculation.json()
        self.assertEqual(body["calculation_run"]["status"], "completed")
        self.assertEqual(body["result"]["annual_cash_flows"][-1], "1284000.00")

        saved_run = self.client.get(f"/v1/calculation-runs/{body['calculation_run']['id']}")
        self.assertEqual(saved_run.status_code, 200)
        self.assertEqual(saved_run.json()["result"], body["result"])

        sensitivity = self.client.post(
            f"/v1/assumption-sets/{assumptions['id']}/sensitivities",
            json={
                "target_levered_irr": "0.10",
                "minimum_dscr": "1.00",
                "minimum_purchase_price": "500000",
                "maximum_purchase_price": "1500000",
            },
        )
        self.assertEqual(sensitivity.status_code, 201)
        self.assertEqual(sensitivity.json()["calculation_run"]["calculation_type"], "sensitivity")
        self.assertEqual(len(sensitivity.json()["result"]["dimensions"]), 3)

        run_history = self.client.get(f"/v1/assumption-sets/{assumptions['id']}/calculation-runs")
        self.assertEqual(run_history.status_code, 200)
        self.assertEqual(
            [run["id"] for run in run_history.json()],
            [sensitivity.json()["calculation_run"]["id"], body["calculation_run"]["id"]],
        )

        next_version = self.client.post(
            f"/v1/deals/{deal_id}/assumption-sets",
            json={"underwriting": {**UNDERWRITING_REQUEST, "purchase_price": "1100000"}},
        )
        self.assertEqual(next_version.status_code, 201)
        self.assertEqual(next_version.json()["version"], 2)

        detail = self.client.get(f"/v1/deals/{deal_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual([item["version"] for item in detail.json()["assumption_sets"]], [2, 1])
