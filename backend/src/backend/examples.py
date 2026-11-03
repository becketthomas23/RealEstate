"""The fictional example deals that fill a fresh pipeline.

Eight deals across multifamily, industrial, retail, office, and self storage,
each with supporting detail, one or two sourced versions, and pricing
targets. ``POST /v1/examples`` creates them server-side, ``scripts/seed_examples.py``
loads them through the API, and ``scripts/build_demo_examples.py`` writes
each one as an Excel import in ``demo/examples/``. Every property, firm, and
figure is invented; Maple Street Apartments is the demo kit deal whose
figures also appear in the mock offering memorandums.
"""

from __future__ import annotations

from typing import Any


def _expense_lines(total: int, weights: dict[str, float]) -> list[dict[str, object]]:
    """Split an operating-expense total into named lines that sum exactly."""
    lines: list[dict[str, object]] = []
    allocated = 0
    categories = list(weights.items())
    for category, weight in categories[:-1]:
        amount = round(total * weight)
        allocated += amount
        lines.append({"category": category, "annual_amount": str(amount)})
    lines.append({"category": categories[-1][0], "annual_amount": str(total - allocated)})
    return lines


MULTIFAMILY_EXPENSES = {
    "Real estate taxes": 0.30,
    "Insurance": 0.08,
    "Repairs and maintenance": 0.14,
    "Utilities": 0.12,
    "Payroll": 0.13,
    "Management fee": 0.09,
    "Marketing and administrative": 0.06,
    "Turnover and contract services": 0.05,
    "Replacement reserves": 0.03,
}
COMMERCIAL_EXPENSES = {
    "Real estate taxes": 0.36,
    "Insurance": 0.09,
    "Common area maintenance": 0.22,
    "Utilities": 0.10,
    "Management fee": 0.11,
    "Administrative": 0.06,
    "Replacement reserves": 0.06,
}


def _version(
    *,
    label: str,
    source: str,
    effective_date: str,
    confidence: str,
    property_type: str,
    value_bucket: str,
    price: int,
    pgi: int,
    opex: int,
    vacancy: str,
    rent_growth: str,
    expense_growth: str,
    hold: int,
    ltv: str,
    rate: str,
    amortization: int,
    exit_cap: str,
    closing: str = "0.02",
    selling: str = "0.02",
    detail: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "label": label,
        "source": source,
        "effective_date": effective_date,
        "confidence_level": confidence,
        "property_type": property_type,
        "value_bucket": value_bucket,
        "underwriting": {
            "purchase_price": str(price),
            "closing_cost_rate": closing,
            "loan_to_value": ltv,
            "annual_interest_rate": rate,
            "amortization_years": amortization,
            "exit_cap_rate": exit_cap,
            "selling_cost_rate": selling,
            "operating": {
                "current_potential_gross_income": str(pgi),
                "current_operating_expenses": str(opex),
                "vacancy_rate": vacancy,
                "rent_growth_rate": rent_growth,
                "expense_growth_rate": expense_growth,
                "hold_period_years": hold,
            },
        },
        "supporting_detail": detail,
    }


def _rent_roll(rows: list[tuple[str, int, int, int, int]]) -> list[dict[str, object]]:
    return [
        {
            "unit_type": unit_type,
            "units": units,
            "average_square_feet": str(square_feet),
            "current_monthly_rent": str(rent),
            "market_monthly_rent": str(market),
        }
        for unit_type, units, square_feet, rent, market in rows
    ]


PINE_HOLLOW_DETAIL = {
    "property": {"name": "Pine Hollow Townhomes", "address": "310 Pine Hollow Ln, Greenville, SC", "units": 24, "rentable_square_feet": "31200", "year_built": 2016, "property_class": "A"},
    "rent_roll": _rent_roll([("2BR / 2.5BA townhome", 16, 1_250, 1_950, 2_025), ("3BR / 2.5BA townhome", 8, 1_400, 2_250, 2_350)]),
    "operating_expenses": _expense_lines(236_000, MULTIFAMILY_EXPENSES),
}

MAPLE_STREET_DETAIL = {
    "property": {"name": "Maple Street Apartments", "address": "100 Maple Street, Springfield", "units": 48, "rentable_square_feet": "42000", "year_built": 1998, "property_class": "B"},
    "rent_roll": _rent_roll([("Studio", 8, 480, 1_150, 1_225), ("1 bed / 1 bath", 24, 690, 1_395, 1_450), ("2 bed / 2 bath", 16, 980, 1_795, 1_875)]),
    "other_income": [{"category": "Parking", "annual_amount": "28800", "note": "48 reserved spaces at $50 per month"}, {"category": "Laundry", "annual_amount": "9600", "note": "Third-party route contract"}, {"category": "Pet rent and fees", "annual_amount": "14400", "note": "Average of trailing twelve months"}],
    "operating_expenses": [
        {"category": "Real estate taxes", "annual_amount": "118000", "note": "Trailing; reassessed on sale"}, {"category": "Insurance", "annual_amount": "34000", "note": "Renewed June 2026"}, {"category": "Utilities", "annual_amount": "52000", "note": "Common area and vacant units"},
        {"category": "Repairs and maintenance", "annual_amount": "48000", "note": "Includes turnover"}, {"category": "Contract services", "annual_amount": "18000", "note": "Landscaping, pest, trash"}, {"category": "Payroll", "annual_amount": "72000", "note": "On-site manager and maintenance"},
        {"category": "Management fee", "annual_amount": "31000", "note": "3% of effective gross income"}, {"category": "General and administrative", "annual_amount": "12000"}, {"category": "Marketing", "annual_amount": "6000"}, {"category": "Replacement reserves", "annual_amount": "14400", "note": "$300 per unit"},
    ],
    "notes": "The demo kit deal. The same figures are in the short and full mock offering memorandums and the Excel import in demo/.",
}

STARTER_DEAL_NAME = "Maple Street Apartments"


def starter_example() -> dict[str, Any]:
    """The deal every new account starts with: the demo kit's Maple Street."""
    return next(example for example in EXAMPLE_DEALS if example["name"] == STARTER_DEAL_NAME)


EXAMPLE_DEALS: list[dict[str, Any]] = [
    {
        "name": "Maple Street Apartments",
        "targets": {"target_levered_irr": "0.12", "minimum_dscr": "1.25"},
        "versions": [
            _version(
                label="Broker OM base case",
                source="Northgate Capital Advisors offering memorandum, October 2026 (mock)",
                effective_date="2026-09-30",
                confidence="medium",
                property_type="Multifamily",
                value_bucket="$5M-$10M",
                price=8_500_000,
                pgi=909_600,
                opex=405_400,
                vacancy="0.05",
                rent_growth="0.03",
                expense_growth="0.025",
                hold=5,
                ltv="0.60",
                rate="0.06",
                amortization=30,
                exit_cap="0.065",
                detail=MAPLE_STREET_DETAIL,
            )
        ],
    },
    {
        "name": "Riverbend Commons",
        "targets": {"target_levered_irr": "0.13", "minimum_dscr": "1.25"},
        "versions": [
            _version(
                label="Base case",
                source="Keystone Realty Advisors offering memorandum, September 2026",
                effective_date="2026-09-18",
                confidence="medium",
                property_type="Multifamily",
                value_bucket="$10M-$25M",
                price=14_200_000,
                pgi=1_958_400,
                opex=822_000,
                vacancy="0.06",
                rent_growth="0.03",
                expense_growth="0.03",
                hold=7,
                ltv="0.60",
                rate="0.061",
                amortization=30,
                exit_cap="0.0675",
                detail={
                    "property": {"name": "Riverbend Commons", "address": "4100 Riverbend Pkwy, Round Rock, TX", "units": 96, "rentable_square_feet": "84200", "year_built": 2004, "property_class": "B"},
                    "rent_roll": _rent_roll([("1BR / 1BA", 40, 720, 1_450, 1_525), ("2BR / 2BA", 48, 980, 1_875, 1_950), ("3BR / 2BA", 8, 1_210, 2_400, 2_475)]),
                    "other_income": [{"category": "Parking and storage", "annual_amount": "38400"}, {"category": "Utility reimbursements", "annual_amount": "61200"}],
                    "operating_expenses": _expense_lines(822_000, MULTIFAMILY_EXPENSES),
                    "notes": "Garden-style community, 2004 vintage, value-add on 30 unrenovated units.",
                },
            )
        ],
    },
    {
        "name": "Harbor Point Industrial",
        "targets": {"target_levered_irr": "0.12", "minimum_dscr": "1.30"},
        "versions": [
            _version(
                label="Base case",
                source="Meridian Industrial Partners OM, broker call 2026-10-02",
                effective_date="2026-10-02",
                confidence="high",
                property_type="Industrial",
                value_bucket="$10M-$25M",
                price=11_800_000,
                pgi=1_152_000,
                opex=265_000,
                vacancy="0.05",
                rent_growth="0.035",
                expense_growth="0.03",
                hold=5,
                ltv="0.55",
                rate="0.063",
                amortization=30,
                exit_cap="0.065",
                detail={
                    "property": {"name": "Harbor Point Industrial", "address": "2201 Harbor Point Rd, Savannah, GA", "units": 3, "rentable_square_feet": "120000", "year_built": 2011, "property_class": "B"},
                    "other_income": [{"category": "CAM recoveries", "annual_amount": "148000"}],
                    "operating_expenses": _expense_lines(265_000, COMMERCIAL_EXPENSES),
                    "notes": "Three-tenant rear-load warehouse, 28 ft clear, 4.2 years weighted average lease term.",
                },
            )
        ],
    },
    {
        "name": "Cedar Plaza Shopping Center",
        "targets": {"target_levered_irr": "0.13", "minimum_dscr": "1.30"},
        "versions": [
            _version(
                label="Base case",
                source="Listing package, Brightline Retail Group",
                effective_date="2026-09-30",
                confidence="low",
                property_type="Retail",
                value_bucket="$5M-$10M",
                price=6_400_000,
                pgi=760_000,
                opex=230_000,
                vacancy="0.08",
                rent_growth="0.025",
                expense_growth="0.03",
                hold=7,
                ltv="0.60",
                rate="0.066",
                amortization=25,
                exit_cap="0.075",
                detail={
                    "property": {"name": "Cedar Plaza", "address": "880 Cedar Ave, Chandler, AZ", "units": 14, "rentable_square_feet": "42000", "year_built": 1998, "property_class": "B"},
                    "operating_expenses": _expense_lines(230_000, COMMERCIAL_EXPENSES),
                    "notes": "Grocery-shadowed neighborhood center; two inline vacancies at underwriting.",
                },
            )
        ],
    },
    {
        "name": "Northgate Medical Office",
        "targets": {"target_levered_irr": "0.12", "minimum_dscr": "1.25"},
        "versions": [
            _version(
                label="Base case",
                source="Seller financials, trailing twelve months to August 2026",
                effective_date="2026-09-12",
                confidence="medium",
                property_type="Office",
                value_bucket="$5M-$10M",
                price=9_100_000,
                pgi=1_330_000,
                opex=520_000,
                vacancy="0.07",
                rent_growth="0.025",
                expense_growth="0.03",
                hold=6,
                ltv="0.60",
                rate="0.065",
                amortization=25,
                exit_cap="0.0775",
                detail={
                    "property": {"name": "Northgate Medical Office", "address": "1500 Northgate Blvd, Raleigh, NC", "units": 11, "rentable_square_feet": "38000", "year_built": 2007, "property_class": "A"},
                    "operating_expenses": _expense_lines(520_000, COMMERCIAL_EXPENSES),
                    "notes": "Hospital-adjacent, anchored by an orthopedic group through 2032.",
                },
            )
        ],
    },
    {
        "name": "Summit Self Storage",
        "targets": {"target_levered_irr": "0.14", "minimum_dscr": "1.25"},
        "versions": [
            _version(
                label="Base case",
                source="Operator P&L and unit mix, Summit Storage Partners",
                effective_date="2026-10-08",
                confidence="medium",
                property_type="Self Storage",
                value_bucket="$1M-$5M",
                price=4_600_000,
                pgi=690_000,
                opex=245_000,
                vacancy="0.12",
                rent_growth="0.03",
                expense_growth="0.03",
                hold=5,
                ltv="0.60",
                rate="0.064",
                amortization=30,
                exit_cap="0.07",
                detail={
                    "property": {"name": "Summit Self Storage", "address": "77 Summit Ridge Rd, Boise, ID", "units": 520, "rentable_square_feet": "61500", "year_built": 2015, "property_class": "B"},
                    "other_income": [{"category": "Tenant insurance and fees", "annual_amount": "31000"}],
                    "operating_expenses": _expense_lines(245_000, MULTIFAMILY_EXPENSES),
                    "notes": "Climate-controlled share 40%; lease-up on the 2024 expansion still in progress.",
                },
            )
        ],
    },
    {
        "name": "Pine Hollow Townhomes",
        "targets": {"target_levered_irr": "0.13", "minimum_dscr": "1.25"},
        "versions": [
            _version(
                label="Base case",
                source="Keystone Realty Advisors OM, August 2026",
                effective_date="2026-08-26",
                confidence="medium",
                property_type="Multifamily",
                value_bucket="$1M-$5M",
                price=3_900_000,
                pgi=590_400,
                opex=236_000,
                vacancy="0.05",
                rent_growth="0.03",
                expense_growth="0.03",
                hold=7,
                ltv="0.65",
                rate="0.062",
                amortization=30,
                exit_cap="0.065",
                detail={**PINE_HOLLOW_DETAIL, "notes": "Newer townhome community; the broker underwrites rent growth above the submarket."},
            ),
            _version(
                label="Broker rent growth",
                source="Broker pro forma, 4.5% rent growth",
                effective_date="2026-09-04",
                confidence="low",
                property_type="Multifamily",
                value_bucket="$1M-$5M",
                price=3_900_000,
                pgi=590_400,
                opex=236_000,
                vacancy="0.05",
                rent_growth="0.045",
                expense_growth="0.03",
                hold=7,
                ltv="0.65",
                rate="0.062",
                amortization=30,
                exit_cap="0.065",
                detail={**PINE_HOLLOW_DETAIL, "notes": "Sensitivity version using the broker rent growth; compare against the base case."},
            ),
        ],
    },
    {
        "name": "Westfield Logistics Center",
        "targets": {"target_levered_irr": "0.115", "minimum_dscr": "1.35"},
        "versions": [
            _version(
                label="Base case",
                source="Confidential OM, Atlas Capital Markets, October 2026",
                effective_date="2026-10-14",
                confidence="high",
                property_type="Industrial",
                value_bucket="$25M-$50M",
                price=26_500_000,
                pgi=2_310_000,
                opex=480_000,
                vacancy="0.04",
                rent_growth="0.035",
                expense_growth="0.03",
                hold=10,
                ltv="0.55",
                rate="0.060",
                amortization=30,
                exit_cap="0.0625",
                closing="0.015",
                selling="0.015",
                detail={
                    "property": {"name": "Westfield Logistics Center", "address": "9800 Westfield Industrial Dr, Columbus, OH", "units": 2, "rentable_square_feet": "210000", "year_built": 2019, "property_class": "A"},
                    "other_income": [{"category": "Expense recoveries", "annual_amount": "402000"}],
                    "operating_expenses": _expense_lines(480_000, COMMERCIAL_EXPENSES),
                    "notes": "Cross-dock distribution building; two credit tenants, 7.1 years weighted average lease term.",
                },
            )
        ],
    },
]
