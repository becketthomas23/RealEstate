"""Import a near-standard underwriting workbook: assumptions, rent roll, income, and expenses.

The template is deliberately forgiving. Labels are matched through aliases
after normalising case and punctuation, percentages may be entered as 5, 5%
or 0.05, and the aggregate income and expense inputs can be left blank to be
rolled up from the Rent Roll, Other Income, and Operating Expenses sheets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .api.schemas import SupportingDetailRequest, UnderwritingRequest


HEADER_FILL = "166534"
INPUT_FILL = "FFF8DC"
SECTION_FILL = "E6F2EA"

# (section, label, example value, unit, note, key)
ASSUMPTION_ROWS: tuple[tuple[str, str, Any, str, str, str], ...] = (
    ("Property", "Property name", "Maple Street Apartments", "text", "Used as the deal name if you create a deal from this file.", "property_name"),
    ("Property", "Address", "100 Maple Street, Springfield", "text", "", "address"),
    ("Property", "Property type", "Multifamily", "text", "Multifamily, Office, Industrial, Retail, Mixed-use…", "property_type"),
    ("Property", "Property class", "B", "text", "A, B or C", "property_class"),
    ("Property", "Units", 48, "count", "Residential units or suites. Drives per-unit metrics.", "units"),
    ("Property", "Rentable square feet", 42000, "SF", "Drives per-square-foot metrics.", "rentable_square_feet"),
    ("Property", "Year built", 1998, "year", "", "year_built"),
    ("Acquisition", "Purchase price (asking or guide)", 8500000, "USD", "Reference price. The solver finds the maximum supportable price.", "purchase_price"),
    ("Acquisition", "Closing costs", 0.02, "%", "Share of price, funded with equity.", "closing_cost_rate"),
    ("Acquisition", "Hold period", 5, "years", "5 to 10.", "hold_period_years"),
    ("Acquisition", "Exit cap rate", 0.065, "%", "Applied to the year after the hold (forward NOI).", "exit_cap_rate"),
    ("Acquisition", "Selling costs", 0.02, "%", "Share of gross sale price.", "selling_cost_rate"),
    ("Operations", "Current potential gross income", None, "USD / yr", "Leave blank to roll up from the Rent Roll and Other Income sheets.", "current_potential_gross_income"),
    ("Operations", "Current operating expenses", None, "USD / yr", "Leave blank to roll up from the Operating Expenses sheet.", "current_operating_expenses"),
    ("Operations", "Vacancy and credit loss", 0.05, "%", "", "vacancy_rate"),
    ("Operations", "Rent growth", 0.03, "% / yr", "Flat annual rate; overridden by a schedule below.", "rent_growth_rate"),
    ("Operations", "Expense growth", 0.025, "% / yr", "", "expense_growth_rate"),
    ("Operations", "Rent growth schedule", "", "% list", "Optional, e.g. 4, 3, 2. Applies from the first growth year.", "annual_rent_growth_rates"),
    ("Operations", "Year 1 convention", "Current", "text", "Current: Year 1 = entered figures. Forward: grow once before Year 1.", "year_one_convention"),
    ("Financing", "Loan-to-value", 0.60, "%", "0 for all-cash.", "loan_to_value"),
    ("Financing", "Interest rate", 0.06, "%", "Fixed annual note rate, amortized monthly.", "annual_interest_rate"),
    ("Financing", "Amortization", 30, "years", "At least the hold period.", "amortization_years"),
    ("Targets", "Target levered IRR", 0.12, "%", "", "target_levered_irr"),
    ("Targets", "Minimum DSCR", 1.25, "x", "", "minimum_dscr"),
    ("Version", "Version label", "Broker OM base case", "text", "", "label"),
    ("Version", "Source or document reference", "Broker offering memorandum, Sept 2026", "text", "", "source"),
    ("Version", "Effective date", date(2026, 9, 30), "date", "", "effective_date"),
    ("Version", "Confidence", "Medium", "text", "Low, Medium or High", "confidence_level"),
)

ALIASES: dict[str, tuple[str, ...]] = {
    "property_name": ("property name", "asset name", "deal name", "name"),
    "address": ("address", "property address", "location"),
    "property_type": ("property type", "asset type", "asset class", "type"),
    "property_class": ("property class", "class", "building class"),
    "units": ("units", "unit count", "number of units", "total units", "suites"),
    "rentable_square_feet": ("rentable square feet", "rentable sf", "rsf", "square feet", "sf", "nra", "net rentable area", "gla"),
    "year_built": ("year built", "built", "vintage"),
    "purchase_price": ("purchase price", "purchase price asking or guide", "asking price", "guide price", "price", "reference price", "acquisition price"),
    "closing_cost_rate": ("closing costs", "closing cost", "closing costs percent", "acquisition costs", "transaction costs"),
    "hold_period_years": ("hold period", "hold", "holding period", "hold period years"),
    "exit_cap_rate": ("exit cap rate", "exit cap", "terminal cap rate", "reversion cap rate", "terminal cap"),
    "selling_cost_rate": ("selling costs", "sale costs", "disposition costs", "cost of sale", "selling cost"),
    "current_potential_gross_income": ("current potential gross income", "potential gross income", "pgi", "gross potential rent", "gpr", "gross potential income", "potential rental income"),
    "current_operating_expenses": ("current operating expenses", "operating expenses", "opex", "total operating expenses", "expenses"),
    "vacancy_rate": ("vacancy and credit loss", "vacancy", "vacancy rate", "vacancy credit loss", "economic vacancy", "vacancy loss"),
    "rent_growth_rate": ("rent growth", "rent growth rate", "revenue growth", "income growth", "market rent growth"),
    "expense_growth_rate": ("expense growth", "expense growth rate", "opex growth", "expense inflation"),
    "annual_rent_growth_rates": ("rent growth schedule", "annual rent growth schedule", "rent growth by year", "growth schedule"),
    "year_one_convention": ("year 1 convention", "year one convention", "growth convention", "year 1 growth"),
    "loan_to_value": ("loan to value", "ltv", "leverage"),
    "annual_interest_rate": ("interest rate", "annual interest rate", "note rate", "coupon", "loan rate", "rate"),
    "amortization_years": ("amortization", "amortization years", "amortization period", "amort", "amortization term"),
    "target_levered_irr": ("target levered irr", "target irr", "hurdle rate", "required irr", "levered irr target"),
    "minimum_dscr": ("minimum dscr", "min dscr", "dscr floor", "dscr covenant", "required dscr"),
    "label": ("version label", "label", "scenario", "case", "scenario name", "version"),
    "source": ("source or document reference", "source", "document reference", "data source", "reference"),
    "effective_date": ("effective date", "as of date", "as of", "date", "valuation date"),
    "confidence_level": ("confidence", "confidence level", "input confidence"),
}
RATE_KEYS = {
    "closing_cost_rate",
    "exit_cap_rate",
    "selling_cost_rate",
    "vacancy_rate",
    "rent_growth_rate",
    "expense_growth_rate",
    "loan_to_value",
    "annual_interest_rate",
    "target_levered_irr",
}
MONEY_KEYS = {"purchase_price", "current_potential_gross_income", "current_operating_expenses", "rentable_square_feet"}
INTEGER_KEYS = {"hold_period_years", "amortization_years", "units", "year_built"}
REQUIRED_KEYS = (
    "purchase_price",
    "closing_cost_rate",
    "hold_period_years",
    "exit_cap_rate",
    "selling_cost_rate",
    "vacancy_rate",
    "rent_growth_rate",
    "expense_growth_rate",
    "loan_to_value",
    "annual_interest_rate",
    "amortization_years",
)

RENT_ROLL_COLUMNS = ("Unit type", "Units", "Average square feet", "Current monthly rent", "Market monthly rent")
RENT_ROLL_EXAMPLE = (
    ("Studio", 8, 480, 1150, 1225),
    ("1 bed / 1 bath", 24, 690, 1395, 1450),
    ("2 bed / 2 bath", 16, 980, 1795, 1875),
)
INCOME_COLUMNS = ("Category", "Annual amount", "Note")
INCOME_EXAMPLE = (("Parking", 28800, "48 spaces at $50"), ("Laundry", 9600, ""), ("Pet rent and fees", 14400, ""))
EXPENSE_COLUMNS = ("Category", "Annual amount", "Note")
EXPENSE_EXAMPLE = (
    ("Real estate taxes", 118000, "Reassessed on sale; confirm with county"),
    ("Insurance", 34000, ""),
    ("Utilities", 52000, "Common area and vacant units"),
    ("Repairs and maintenance", 48000, ""),
    ("Contract services", 18000, "Landscaping, pest, trash"),
    ("Payroll", 72000, ""),
    ("Management fee", 31000, "3% of EGI"),
    ("General and administrative", 12000, ""),
    ("Marketing", 6000, ""),
    ("Replacement reserves", 14400, "$300 per unit"),
)


@dataclass
class WorkbookImport:
    underwriting: UnderwritingRequest
    supporting_detail: SupportingDetailRequest
    version: dict[str, Any]
    targets: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)


def underwriting_workbook_template() -> BytesIO:
    """Build the import template with an example deal filled in."""
    book = Workbook()
    instructions = book.active
    instructions.title = "Instructions"
    _write_instructions(instructions)
    assumptions = book.create_sheet("Assumptions")
    assumptions.append(["Section", "Input", "Value", "Unit", "Notes"])
    for section, label, value, unit, note, _key in ASSUMPTION_ROWS:
        assumptions.append([section, label, value, unit, note])
    for row in assumptions.iter_rows(min_row=2):
        row[2].fill = PatternFill("solid", fgColor=INPUT_FILL)
        unit = row[3].value
        if unit in {"%", "% / yr"}:
            row[2].number_format = "0.00%"
        elif unit in {"USD", "USD / yr"}:
            row[2].number_format = "#,##0"
        elif unit == "date":
            row[2].number_format = "yyyy-mm-dd"
        elif unit == "x":
            row[2].number_format = "0.00"
    _style_table(assumptions, widths=(14, 36, 22, 10, 64))
    _section_shading(assumptions)

    rent_roll = book.create_sheet("Rent Roll")
    rent_roll.append(list(RENT_ROLL_COLUMNS))
    for line in RENT_ROLL_EXAMPLE:
        rent_roll.append(list(line))
    for row in rent_roll.iter_rows(min_row=2, min_col=2):
        for cell in row:
            cell.number_format = "#,##0"
    _style_table(rent_roll, widths=(24, 10, 20, 22, 22))

    income = book.create_sheet("Other Income")
    income.append(list(INCOME_COLUMNS))
    for line in INCOME_EXAMPLE:
        income.append(list(line))
    for cell in income["B"][1:]:
        cell.number_format = "#,##0"
    _style_table(income, widths=(28, 16, 48))

    expenses = book.create_sheet("Operating Expenses")
    expenses.append(list(EXPENSE_COLUMNS))
    for line in EXPENSE_EXAMPLE:
        expenses.append(list(line))
    for cell in expenses["B"][1:]:
        cell.number_format = "#,##0"
    _style_table(expenses, widths=(32, 16, 48))

    output = BytesIO()
    book.save(output)
    output.seek(0)
    return output


def parse_underwriting_workbook(contents: bytes) -> WorkbookImport:
    """Read the template (or a near match) into validated API contracts."""
    try:
        book = load_workbook(BytesIO(contents), data_only=True, read_only=True)
    except Exception as error:  # openpyxl raises several unrelated types for bad files
        raise ValueError("the file is not a readable .xlsx workbook") from error
    warnings: list[str] = []
    sheet = _find_sheet(book, ("assumptions", "inputs", "summary")) or book.worksheets[0]
    raw, sources = _read_label_values(sheet)
    if not raw:
        raise ValueError("no labelled inputs were found; use the Assumptions sheet layout from the template")

    rent_roll = _read_table(_find_sheet(book, ("rent roll", "rentroll", "unit mix")), RENT_ROLL_COLUMNS)
    other_income = _read_table(_find_sheet(book, ("other income", "income")), INCOME_COLUMNS)
    expense_lines = _read_table(_find_sheet(book, ("operating expenses", "expenses", "opex")), EXPENSE_COLUMNS)

    rent_roll_lines = [
        {
            "unit_type": str(line[0]).strip(),
            "units": _to_int(line[1], "Rent Roll units"),
            "average_square_feet": _to_decimal(line[2]) if _present(line[2]) else None,
            "current_monthly_rent": _to_decimal(line[3]) if _present(line[3]) else Decimal("0"),
            "market_monthly_rent": _to_decimal(line[4]) if len(line) > 4 and _present(line[4]) else None,
        }
        for line in rent_roll
        if _present(line[0])
    ]
    income_lines = [
        {"category": str(line[0]).strip(), "annual_amount": _to_decimal(line[1]), "note": _text(line[2]) if len(line) > 2 else None}
        for line in other_income
        if _present(line[0]) and _present(line[1])
    ]
    expense_detail = [
        {"category": str(line[0]).strip(), "annual_amount": _to_decimal(line[1]), "note": _text(line[2]) if len(line) > 2 else None}
        for line in expense_lines
        if _present(line[0]) and _present(line[1])
    ]

    rolled_income = sum((line["units"] * line["current_monthly_rent"] * 12 for line in rent_roll_lines), Decimal("0")) + sum(
        (line["annual_amount"] for line in income_lines), Decimal("0")
    )
    rolled_expenses = sum((line["annual_amount"] for line in expense_detail), Decimal("0"))

    if not _present(raw.get("current_potential_gross_income")):
        if rolled_income > 0:
            raw["current_potential_gross_income"] = rolled_income
            sources["current_potential_gross_income"] = "rolled up from Rent Roll and Other Income"
        else:
            raise ValueError("enter Current potential gross income or complete the Rent Roll sheet")
    elif rolled_income > 0 and abs(_to_decimal(raw["current_potential_gross_income"]) - rolled_income) > Decimal("1"):
        warnings.append(
            f"Current potential gross income ({_to_decimal(raw['current_potential_gross_income']):,.0f}) differs from the Rent Roll plus Other Income roll-up ({rolled_income:,.0f}); the entered figure was used."
        )
    if not _present(raw.get("current_operating_expenses")):
        if expense_detail:
            raw["current_operating_expenses"] = rolled_expenses
            sources["current_operating_expenses"] = "rolled up from Operating Expenses"
        else:
            raise ValueError("enter Current operating expenses or complete the Operating Expenses sheet")
    elif expense_detail and abs(_to_decimal(raw["current_operating_expenses"]) - rolled_expenses) > Decimal("1"):
        warnings.append(
            f"Current operating expenses ({_to_decimal(raw['current_operating_expenses']):,.0f}) differs from the Operating Expenses roll-up ({rolled_expenses:,.0f}); the entered figure was used."
        )

    missing = [label for key, label in ((key, _label_for(key)) for key in REQUIRED_KEYS) if not _present(raw.get(key))]
    if missing:
        raise ValueError("missing required inputs: " + ", ".join(missing))

    schedule_text = raw.get("annual_rent_growth_rates")
    schedule = _parse_schedule(schedule_text) if _present(schedule_text) else None
    convention = str(raw.get("year_one_convention") or "current").strip().lower()
    underwriting = UnderwritingRequest.model_validate(
        {
            "purchase_price": _to_decimal(raw["purchase_price"]),
            "closing_cost_rate": _to_rate(raw["closing_cost_rate"]),
            "loan_to_value": _to_rate(raw["loan_to_value"]),
            "annual_interest_rate": _to_rate(raw["annual_interest_rate"]),
            "amortization_years": _to_int(raw["amortization_years"], "Amortization"),
            "exit_cap_rate": _to_rate(raw["exit_cap_rate"]),
            "selling_cost_rate": _to_rate(raw["selling_cost_rate"]),
            "operating": {
                "current_potential_gross_income": _to_decimal(raw["current_potential_gross_income"]),
                "current_operating_expenses": _to_decimal(raw["current_operating_expenses"]),
                "vacancy_rate": _to_rate(raw["vacancy_rate"]),
                "rent_growth_rate": _to_rate(raw["rent_growth_rate"]),
                "expense_growth_rate": _to_rate(raw["expense_growth_rate"]),
                "hold_period_years": _to_int(raw["hold_period_years"], "Hold period"),
                "annual_rent_growth_rates": schedule,
                "apply_growth_in_year_one": convention.startswith("forward") or convention.startswith("trailing"),
            },
        }
    )

    property_detail = {
        "name": _text(raw.get("property_name")),
        "address": _text(raw.get("address")),
        "units": _to_int(raw["units"], "Units") if _present(raw.get("units")) else (sum(line["units"] for line in rent_roll_lines) or None),
        "rentable_square_feet": _to_decimal(raw["rentable_square_feet"]) if _present(raw.get("rentable_square_feet")) else _rent_roll_square_feet(rent_roll_lines),
        "year_built": _to_int(raw["year_built"], "Year built") if _present(raw.get("year_built")) else None,
        "property_class": _text(raw.get("property_class")),
    }
    detail = SupportingDetailRequest.model_validate(
        {
            "property": property_detail if any(value is not None for value in property_detail.values()) else None,
            "rent_roll": rent_roll_lines,
            "other_income": income_lines,
            "operating_expenses": expense_detail,
        }
    )
    confidence = str(raw.get("confidence_level") or "medium").strip().lower()
    version = {
        "label": _text(raw.get("label")),
        "source": _text(raw.get("source")),
        "effective_date": _to_date(raw.get("effective_date")),
        "confidence_level": confidence if confidence in {"low", "medium", "high"} else "medium",
        "property_type": _text(raw.get("property_type")),
    }
    targets = {
        "target_levered_irr": _to_rate(raw["target_levered_irr"]) if _present(raw.get("target_levered_irr")) else None,
        "minimum_dscr": _to_decimal(raw["minimum_dscr"]) if _present(raw.get("minimum_dscr")) else None,
    }
    if rent_roll_lines and underwriting.operating.current_potential_gross_income:
        market_income = sum((line["units"] * (line["market_monthly_rent"] or line["current_monthly_rent"]) * 12 for line in rent_roll_lines), Decimal("0"))
        in_place = sum((line["units"] * line["current_monthly_rent"] * 12 for line in rent_roll_lines), Decimal("0"))
        if market_income > in_place:
            warnings.append(f"Rent roll shows {float((market_income / in_place) - 1):.1%} loss-to-lease against market rents; the model grows in-place rent, not market rent.")
    return WorkbookImport(underwriting=underwriting, supporting_detail=detail, version=version, targets=targets, warnings=warnings, sources=sources)


# ---------------------------------------------------------------- helpers

def _write_instructions(sheet: Worksheet) -> None:
    lines = (
        ("CRE Price Solver — underwriting import template", True),
        ("", False),
        ("1. Fill the Assumptions sheet. Labels are matched flexibly (for example LTV, Loan-to-value, or Leverage all work).", False),
        ("2. Percentages may be typed as 5, 5% or 0.05. Dates may be typed or formatted as Excel dates.", False),
        ("3. Leave Current potential gross income blank to roll it up from the Rent Roll (units × current monthly rent × 12) plus Other Income.", False),
        ("4. Leave Current operating expenses blank to roll them up from the Operating Expenses sheet.", False),
        ("5. Rent Roll, Other Income and Operating Expenses are optional, but when supplied they are saved with the version and appear in the Excel export.", False),
        ("6. Rows you do not need can be deleted; extra rows are ignored.", False),
        ("", False),
        ("Conventions: Year 1 equals the entered current figures unless the Year 1 convention is Forward. Closing costs are funded with equity. Debt amortizes monthly.", False),
        ("Educational use only — not financial advice.", False),
    )
    for text, bold in lines:
        sheet.append([text])
        if bold:
            sheet.cell(row=sheet.max_row, column=1).font = Font(bold=True, size=14)
    sheet.column_dimensions["A"].width = 120
    for row in sheet.iter_rows():
        row[0].alignment = Alignment(wrap_text=True, vertical="top")


def _style_table(sheet: Worksheet, widths: tuple[int, ...]) -> None:
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=HEADER_FILL)
    sheet.freeze_panes = "A2"
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width


def _section_shading(sheet: Worksheet) -> None:
    previous = None
    for row in sheet.iter_rows(min_row=2):
        if row[0].value != previous:
            row[0].font = Font(bold=True)
            previous = row[0].value
        row[0].fill = PatternFill("solid", fgColor=SECTION_FILL)
        row[4].alignment = Alignment(wrap_text=True, vertical="top")


def _find_sheet(book, names: tuple[str, ...]):
    for sheet in book.worksheets:
        if _normalize(sheet.title) in {_normalize(name) for name in names}:
            return sheet
    return None


def _normalize(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _label_for(key: str) -> str:
    for _section, label, _value, _unit, _note, row_key in ASSUMPTION_ROWS:
        if row_key == key:
            return label
    return key


_ALIAS_LOOKUP = {_normalize(alias): key for key, aliases in ALIASES.items() for alias in aliases}
_ALIAS_LOOKUP.update({_normalize(label): key for _s, label, _v, _u, _n, key in ASSUMPTION_ROWS})


def _read_label_values(sheet) -> tuple[dict[str, Any], dict[str, str]]:
    """Scan every row for a recognised label followed by a value cell."""
    found: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for row in sheet.iter_rows(values_only=True):
        cells = list(row)
        for index, cell in enumerate(cells[:-1]):
            if not isinstance(cell, str):
                continue
            key = _ALIAS_LOOKUP.get(_normalize(cell))
            if key is None or key in found:
                continue
            value = next((candidate for candidate in cells[index + 1 :] if _present(candidate)), None)
            # A string value that is itself a recognised label means this cell
            # was a section heading (for example Property / Property type).
            if isinstance(value, str) and _ALIAS_LOOKUP.get(_normalize(value)) is not None:
                continue
            if value is None or (
                isinstance(value, str)
                and _normalize(value) in {"text", "count", "sf", "year", "usd", "usd yr", "years", "x", "date", "list", "value", "input", "amount", "unit", "notes"}
            ):
                continue
            found[key] = value
            sources[key] = f"{sheet.title} ‘{cell.strip()}’"
            break
    return found, sources


def _read_table(sheet, columns: tuple[str, ...]) -> list[tuple[Any, ...]]:
    if sheet is None:
        return []
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    header_index = next((index for index, row in enumerate(rows) if row and _normalize(row[0]) == _normalize(columns[0])), None)
    body = rows[header_index + 1 :] if header_index is not None else rows
    return [tuple(row) + (None,) * (len(columns) - len(row)) for row in body if row and any(_present(value) for value in row)]


def _present(value: Any) -> bool:
    return value is not None and not (isinstance(value, str) and not value.strip())


def _text(value: Any) -> str | None:
    if not _present(value):
        return None
    return str(value).strip() if not isinstance(value, (datetime, date)) else value.isoformat()


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise ValueError(f"{value!r} is not a number")
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip().replace(",", "").replace("$", "")
    if text.endswith("%"):
        return Decimal(text[:-1].strip()) / Decimal("100")
    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"{value!r} is not a number") from error


def _to_rate(value: Any) -> Decimal:
    """Accept 5, 5% or 0.05 for five percent."""
    if isinstance(value, str) and value.strip().endswith("%"):
        return _to_decimal(value)
    number = _to_decimal(value)
    return number / Decimal("100") if number > 1 else number


def _to_int(value: Any, label: str) -> int:
    number = _to_decimal(value)
    if number != number.to_integral_value():
        raise ValueError(f"{label} must be a whole number")
    return int(number)


def _to_date(value: Any) -> str | None:
    if not _present(value):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%d %B %Y", "%B %d, %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_schedule(value: Any) -> list[Decimal]:
    if isinstance(value, (int, float, Decimal)):
        return [_to_rate(value)]
    parts = [part for part in re.split(r"[;,\s]+", str(value).strip()) if part]
    return [_to_rate(part) for part in parts]


def _rent_roll_square_feet(lines: list[dict[str, Any]]) -> Decimal | None:
    if not lines or any(line["average_square_feet"] is None for line in lines):
        return None
    return sum((line["units"] * line["average_square_feet"] for line in lines), Decimal("0"))
