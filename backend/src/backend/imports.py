"""Strict, auditable CSV import for one stabilized-underwriting assumption set."""

import csv
from io import StringIO

from .api.schemas import UnderwritingRequest


CSV_FIELDS = (
    "purchase_price",
    "closing_cost_rate",
    "loan_to_value",
    "annual_interest_rate",
    "amortization_years",
    "exit_cap_rate",
    "selling_cost_rate",
    "current_potential_gross_income",
    "current_operating_expenses",
    "vacancy_rate",
    "rent_growth_rate",
    "expense_growth_rate",
    "hold_period_years",
    "annual_rent_growth_rates",
)


def underwriting_csv_template() -> str:
    """Return a documented header and a valid example row.

    Rates are decimal values (``0.05`` means 5%). A rent-growth schedule is
    optional; when supplied, separate annual values with semicolons.
    """
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "purchase_price": "1000000",
            "closing_cost_rate": "0.02",
            "loan_to_value": "0.60",
            "annual_interest_rate": "0.05",
            "amortization_years": "30",
            "exit_cap_rate": "0.06",
            "selling_cost_rate": "0.02",
            "current_potential_gross_income": "200000",
            "current_operating_expenses": "50000",
            "vacancy_rate": "0.05",
            "rent_growth_rate": "0.03",
            "expense_growth_rate": "0.02",
            "hold_period_years": "5",
            "annual_rent_growth_rates": "",
        }
    )
    return output.getvalue()


def parse_underwriting_csv(contents: bytes) -> UnderwritingRequest:
    """Parse exactly one complete CSV row into the canonical API contract."""
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("CSV must be UTF-8 encoded") from error
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV must include a header row")
    fields = tuple(field.strip() for field in reader.fieldnames)
    if set(fields) != set(CSV_FIELDS) or len(fields) != len(CSV_FIELDS):
        raise ValueError("CSV headers must exactly match the underwriting template")
    rows = [row for row in reader if any((value or "").strip() for value in row.values())]
    if len(rows) != 1:
        raise ValueError("CSV must contain exactly one underwriting row")
    row = {key: (value or "").strip() for key, value in rows[0].items()}
    schedule = row.pop("annual_rent_growth_rates")
    if schedule:
        row["annual_rent_growth_rates"] = [item.strip() for item in schedule.split(";") if item.strip()]
    else:
        row["annual_rent_growth_rates"] = None
    return UnderwritingRequest.model_validate(
        {
            "purchase_price": row.pop("purchase_price"),
            "closing_cost_rate": row.pop("closing_cost_rate"),
            "loan_to_value": row.pop("loan_to_value"),
            "annual_interest_rate": row.pop("annual_interest_rate"),
            "amortization_years": row.pop("amortization_years"),
            "exit_cap_rate": row.pop("exit_cap_rate"),
            "selling_cost_rate": row.pop("selling_cost_rate"),
            "operating": row,
        }
    )
