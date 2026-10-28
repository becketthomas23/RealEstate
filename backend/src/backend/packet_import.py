"""Read a deal packet PDF (offering memorandum) that carries a Deal Scope Data Sheet.

Brokers' offering memoranda are narrative documents; the numbers an
underwriter needs are scattered through tables that no parser can read
reliably. Deal Scope therefore defines a one-to-two page **Data Sheet**
appendix: plain ``Label: Value`` lines plus pipe-delimited rent roll, other
income and operating expense tables. Any packet that includes the sheet can be
read straight into a version, and the sheet doubles as a checklist of what the
model needs. The labels are matched with the same aliases as the Excel
template, so a sheet typed by hand still works.
"""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any

from pypdf import PdfReader

from .workbook_import import EXPENSE_COLUMNS, INCOME_COLUMNS, RENT_ROLL_COLUMNS, WorkbookImport, _ALIAS_LOOKUP, _normalize, build_import


DATA_SHEET_MARKER = "deal scope data sheet"
TABLE_HEADERS = {
    "rent roll": RENT_ROLL_COLUMNS,
    "other income": INCOME_COLUMNS,
    "operating expenses": EXPENSE_COLUMNS,
}


def parse_deal_packet(contents: bytes) -> WorkbookImport:
    """Extract the data sheet from a PDF packet and build an import from it."""
    try:
        reader = PdfReader(BytesIO(contents))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as error:  # pypdf raises several unrelated types for bad files
        raise ValueError("the file is not a readable PDF") from error
    text = "\n".join(pages)
    start = text.lower().find(DATA_SHEET_MARKER)
    if start < 0:
        raise ValueError(
            "no Deal Scope Data Sheet was found in the packet; add the data-sheet appendix (download the template from the Inputs tab) or import the Excel template instead"
        )
    sheet = text[start:]
    raw, sources, tables = _parse_sheet(sheet, page_count=len(pages))
    if not raw:
        raise ValueError("the Deal Scope Data Sheet contained no recognised Label: Value lines")
    result = build_import(raw, sources, tables.get("rent roll", []), tables.get("other income", []), tables.get("operating expenses", []))
    result.sources["_packet"] = f"{len(pages)}-page PDF packet; data sheet parsed from page text"
    return result


def _parse_sheet(sheet: str, page_count: int) -> tuple[dict[str, Any], dict[str, str], dict[str, list[tuple[Any, ...]]]]:
    """Walk the sheet line by line.

    Page footers, page numbers and blank lines can land anywhere in extracted
    PDF text, so a table only ends at the next table heading, the next
    recognised ``Label: Value`` line, or the end marker.
    """
    raw: dict[str, Any] = {}
    sources: dict[str, str] = {}
    tables: dict[str, list[tuple[Any, ...]]] = {}
    current_table: str | None = None
    for line in sheet.splitlines():
        text = line.strip()
        if not text:
            continue
        lowered = _normalize(text)
        if lowered in TABLE_HEADERS:
            current_table = lowered
            tables.setdefault(current_table, [])
            continue
        if lowered.startswith("end of data sheet"):
            break
        if current_table and "|" in text:
            cells = [cell.strip() for cell in text.split("|")]
            if _normalize(cells[0]) == _normalize(TABLE_HEADERS[current_table][0]):
                continue  # header row
            if _normalize(cells[0]) in {"total", "totals", "total weighted"}:
                continue
            tables[current_table].append(tuple(_coerce(cell) for cell in cells))
            continue
        match = re.match(r"^([^:|]{2,80}):\s*(.+)$", text)
        if not match:
            continue  # narrative, footer, or page number
        label, value = match.group(1).strip(), match.group(2).strip()
        key = _ALIAS_LOOKUP.get(_normalize(label))
        if key is None:
            continue
        current_table = None
        placeholder = value.lower() in {"n/a", "na", "-", "—", "tbd"} or value.startswith("(")
        if key not in raw and value and not placeholder:
            raw[key] = _coerce(value)
            sources[key] = f"PDF data sheet ‘{label}’"
    return raw, sources, tables


DATA_SHEET_TEMPLATE_LINES = (
    "DEAL SCOPE DATA SHEET  (version 1)",
    "Append this page to any deal packet. One Label: Value per line; tables use | between columns.",
    "Percentages may be written as 5%, 5 or 0.05. Leave a value blank or n/a to skip it.",
    "",
    "Property name: ",
    "Address: ",
    "Property type: Multifamily",
    "Property class: ",
    "Units: ",
    "Rentable square feet: ",
    "Year built: ",
    "",
    "Purchase price (asking or guide): ",
    "Closing costs: 2%",
    "Hold period: 5",
    "Exit cap rate: ",
    "Selling costs: 2%",
    "",
    "Current potential gross income: (roll up from rent roll and other income)",
    "Current operating expenses: (roll up from operating expenses)",
    "Vacancy and credit loss: 5%",
    "Rent growth: 3%",
    "Expense growth: 2.5%",
    "Rent growth schedule: n/a",
    "Year 1 convention: Current",
    "",
    "Loan-to-value: 60%",
    "Interest rate: ",
    "Amortization: 30",
    "",
    "Target levered IRR: 12%",
    "Minimum DSCR: 1.25",
    "",
    "Version label: Broker OM base case",
    "Source or document reference: ",
    "Effective date: ",
    "Confidence: Medium",
    "",
    "RENT ROLL",
    "Unit type | Units | Average square feet | Current monthly rent | Market monthly rent",
    "",
    "OTHER INCOME",
    "Category | Annual amount | Note",
    "",
    "OPERATING EXPENSES",
    "Category | Annual amount | Note",
    "",
    "END OF DATA SHEET",
)


def data_sheet_template_pdf() -> BytesIO:
    """Render the blank data sheet as a one-page PDF appendix."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer

    output = BytesIO()
    styles = getSampleStyleSheet()
    mono = ParagraphStyle("mono", parent=styles["Code"], fontName="Courier", fontSize=9, leading=12)
    doc = SimpleDocTemplate(output, pagesize=letter, title="Deal Scope Data Sheet template")
    doc.build(
        [
            Paragraph("Deal Scope Data Sheet — template", styles["Title"]),
            Paragraph(
                "Fill in the values below, keep the layout, and include the page in the deal packet. Deal Scope reads it directly; "
                "labels are matched flexibly, so common broker terms (LTV, GPR, OpEx, terminal cap rate) also work.",
                styles["BodyText"],
            ),
            Spacer(1, 10),
            Preformatted("\n".join(DATA_SHEET_TEMPLATE_LINES), mono),
        ]
    )
    output.seek(0)
    return output


def _coerce(value: str) -> Any:
    text = value.strip()
    if not text:
        return None
    cleaned = text.replace(",", "").replace("$", "")
    if re.fullmatch(r"-?\d+(\.\d+)?%?", cleaned):
        return text if cleaned.endswith("%") else (int(cleaned) if re.fullmatch(r"-?\d+", cleaned) else float(cleaned))
    return text
