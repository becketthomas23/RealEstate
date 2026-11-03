"""Write every example deal as an importable Excel underwriting in the demo kit.

The example pipeline that ``seed_examples.py`` loads through the API is also
useful as files: each deal version becomes one workbook in the Deal Scope
import template, so a demonstration can import a deal from disk, and a new
user has worked examples of what a complete underwriting looks like. Every
workbook is parsed back through the importer before it is written, so the
files always reproduce the figures in ``seed_examples.py``. Run from
``backend``:

    uv run python scripts/build_demo_examples.py ../demo/examples
"""

from __future__ import annotations

import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.examples import EXAMPLE_DEALS as EXAMPLES  # noqa: E402
from backend.workbook_import import parse_underwriting_workbook, underwriting_workbook  # noqa: E402


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _workbook_values(example: dict, version: dict) -> tuple[dict, list, list, list]:
    underwriting = version["underwriting"]
    operating = underwriting["operating"]
    detail = version.get("supporting_detail") or {}
    prop = detail.get("property") or {}
    rent_roll = [(line["unit_type"], line["units"], float(line["average_square_feet"]), float(line["current_monthly_rent"]), float(line["market_monthly_rent"])) for line in detail.get("rent_roll", [])]
    other_income = [(line["category"], float(line["annual_amount"]), line.get("note") or "") for line in detail.get("other_income", [])]
    expenses = [(line["category"], float(line["annual_amount"]), line.get("note") or "") for line in detail.get("operating_expenses", [])]
    # Income is entered as a total: a partial rent roll or no rent roll at all
    # cannot roll up to it, so the figure goes in the cell and the detail
    # sheets stay informational. Expenses roll up when the lines sum exactly.
    expense_total = sum(amount for _, amount, _ in expenses)
    values = {
        "property_name": prop.get("name") or example["name"],
        "address": prop.get("address") or "",
        "property_type": version["property_type"],
        "property_class": prop.get("property_class") or "",
        "units": prop.get("units"),
        "rentable_square_feet": float(prop["rentable_square_feet"]) if prop.get("rentable_square_feet") else None,
        "year_built": prop.get("year_built"),
        "purchase_price": float(underwriting["purchase_price"]),
        "closing_cost_rate": float(underwriting["closing_cost_rate"]),
        "hold_period_years": operating["hold_period_years"],
        "exit_cap_rate": float(underwriting["exit_cap_rate"]),
        "selling_cost_rate": float(underwriting["selling_cost_rate"]),
        "current_potential_gross_income": float(operating["current_potential_gross_income"]),
        "current_operating_expenses": None if expenses and expense_total == float(operating["current_operating_expenses"]) else float(operating["current_operating_expenses"]),
        "vacancy_rate": float(operating["vacancy_rate"]),
        "rent_growth_rate": float(operating["rent_growth_rate"]),
        "expense_growth_rate": float(operating["expense_growth_rate"]),
        "annual_rent_growth_rates": "",
        "year_one_convention": "Current",
        "loan_to_value": float(underwriting["loan_to_value"]),
        "annual_interest_rate": float(underwriting["annual_interest_rate"]),
        "amortization_years": underwriting["amortization_years"],
        "target_levered_irr": float(example["targets"]["target_levered_irr"]),
        "minimum_dscr": float(example["targets"]["minimum_dscr"]),
        "label": version["label"],
        "source": version["source"],
        "effective_date": date.fromisoformat(version["effective_date"]),
        "confidence_level": version["confidence_level"].capitalize(),
    }
    return values, rent_roll, other_income, expenses


def build(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for example in EXAMPLES:
        for version in example["versions"]:
            values, rent_roll, other_income, expenses = _workbook_values(example, version)
            contents = underwriting_workbook(values, rent_roll, other_income, expenses).getvalue()
            _check_round_trip(example, version, contents)
            suffix = "" if len(example["versions"]) == 1 else f" - {version['label']}"
            path = output_dir / f"{_slug(example['name'] + suffix)}.xlsx"
            path.write_bytes(contents)
            written.append(path)
    return written


def _check_round_trip(example: dict, version: dict, contents: bytes) -> None:
    """Fail loudly if the importer would not reproduce the seeded figures."""
    imported = parse_underwriting_workbook(contents)
    expected = version["underwriting"]
    got = imported.underwriting
    checks = {
        "purchase_price": (got.purchase_price, expected["purchase_price"]),
        "potential_gross_income": (got.operating.current_potential_gross_income, expected["operating"]["current_potential_gross_income"]),
        "operating_expenses": (got.operating.current_operating_expenses, expected["operating"]["current_operating_expenses"]),
        "exit_cap_rate": (got.exit_cap_rate, expected["exit_cap_rate"]),
        "loan_to_value": (got.loan_to_value, expected["loan_to_value"]),
        "target_levered_irr": (imported.targets["target_levered_irr"], example["targets"]["target_levered_irr"]),
    }
    for name, (actual, wanted) in checks.items():
        if Decimal(str(actual)) != Decimal(str(wanted)):
            raise SystemExit(f"{example['name']} / {version['label']}: {name} round-trips as {actual}, expected {wanted}")
    if imported.version["label"] != version["label"]:
        raise SystemExit(f"{example['name']}: label round-trips as {imported.version['label']!r}")


if __name__ == "__main__":
    for path in build(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()):
        print("wrote", path)
