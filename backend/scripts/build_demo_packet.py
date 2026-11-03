"""Build the Deal Scope demo kit: a mock offering memorandum PDF and the matching Excel import.

Every figure is fictional and internally consistent with the Excel import
template so the two files tell the same story. Run from ``backend``:

    uv run python scripts/build_demo_packet.py ../demo
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.workbook_import import underwriting_workbook_template  # noqa: E402


GREEN = colors.HexColor("#166534")
GREEN_SOFT = colors.HexColor("#E6F2EA")
INK = colors.HexColor("#16201B")
MUTED = colors.HexColor("#6B746E")
LINE = colors.HexColor("#D9DED8")

PROPERTY = {
    "name": "Maple Street Apartments",
    "address": "100 Maple Street, Springfield",
    "type": "Multifamily",
    "class": "B",
    "units": 48,
    "sf": 42000,
    "year_built": 1998,
    "lot_acres": 2.1,
    "stories": 3,
    "parking": 72,
    "asking": 8_500_000,
}
RENT_ROLL = (("Studio", 8, 480, 1150, 1225), ("1 bed / 1 bath", 24, 690, 1395, 1450), ("2 bed / 2 bath", 16, 980, 1795, 1875))
OTHER_INCOME = (("Parking", 28_800, "48 reserved spaces at $50 per month"), ("Laundry", 9_600, "Third-party route contract"), ("Pet rent and fees", 14_400, "Average of trailing twelve months"))
EXPENSES = (
    ("Real estate taxes", 118_000, "Trailing; reassessed on sale"),
    ("Insurance", 34_000, "Renewed June 2026"),
    ("Utilities", 52_000, "Common area and vacant units"),
    ("Repairs and maintenance", 48_000, "Includes turnover"),
    ("Contract services", 18_000, "Landscaping, pest, trash"),
    ("Payroll", 72_000, "On-site manager and maintenance"),
    ("Management fee", 31_000, "3% of effective gross income"),
    ("General and administrative", 12_000, ""),
    ("Marketing", 6_000, ""),
    ("Replacement reserves", 14_400, "$300 per unit"),
)
ASSUMPTIONS = {
    "closing_costs": 0.02,
    "hold": 5,
    "exit_cap": 0.065,
    "selling_costs": 0.02,
    "vacancy": 0.05,
    "rent_growth": 0.03,
    "expense_growth": 0.025,
    "ltv": 0.60,
    "rate": 0.06,
    "amort": 30,
    "target_irr": 0.12,
    "min_dscr": 1.25,
}
SALE_COMPS = (
    ("Riverside Commons", "Springfield", 2001, 64, 9_900_000, 154_700, 0.0640, "Mar 2026"),
    ("Oak Hollow Flats", "Springfield", 1995, 40, 6_250_000, 156_250, 0.0665, "Jan 2026"),
    ("Parkview Terrace", "Westbrook", 2004, 72, 12_100_000, 168_050, 0.0620, "Nov 2025"),
    ("Linden Court", "Springfield", 1989, 36, 5_200_000, 144_450, 0.0690, "Sep 2025"),
    ("Cedar Point Residences", "Eastfield", 1999, 56, 8_700_000, 155_350, 0.0650, "Jul 2025"),
)
RENT_COMPS = (
    ("Riverside Commons", 2001, 1_195, 1_480, 1_910, 0.96),
    ("Oak Hollow Flats", 1995, 1_125, 1_410, 1_825, 0.95),
    ("Parkview Terrace", 2004, 1_260, 1_525, 1_980, 0.97),
    ("Linden Court", 1989, 1_095, 1_360, 1_760, 0.94),
    ("Cedar Point Residences", 1999, 1_175, 1_455, 1_880, 0.96),
)


def build(output_dir: Path) -> tuple[Path, Path, Path]:
    """Write the short packet, the Excel import, and the full-length memorandum."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "Maple Street Apartments - Offering Memorandum (mock).pdf"
    xlsx_path = output_dir / "maple-street-apartments-import.xlsx"
    _build_pdf(pdf_path)
    xlsx_path.write_bytes(underwriting_workbook_template().getvalue())
    from build_full_demo_packet import build_full_memorandum  # noqa: PLC0415  (shares this module's constants)

    full_path = build_full_memorandum(output_dir)
    return pdf_path, xlsx_path, full_path


# ---------------------------------------------------------------- figures

def _figures() -> dict[str, float]:
    in_place = sum(units * rent * 12 for _, units, _, rent, _ in RENT_ROLL)
    market = sum(units * rent * 12 for _, units, _, _, rent in RENT_ROLL)
    other = sum(amount for _, amount, _ in OTHER_INCOME)
    pgi = in_place + other
    vacancy = pgi * ASSUMPTIONS["vacancy"]
    egi = pgi - vacancy
    opex = sum(amount for _, amount, _ in EXPENSES)
    noi = egi - opex
    return {"in_place": in_place, "market": market, "other": other, "pgi": pgi, "vacancy": vacancy, "egi": egi, "opex": opex, "noi": noi, "cap": noi / PROPERTY["asking"]}


def money(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


# ---------------------------------------------------------------- document

def _build_pdf(path: Path) -> None:
    figures = _figures()
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=14, textColor=INK, spaceAfter=6)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=MUTED)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=20, leading=24, textColor=GREEN, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, leading=16, textColor=INK, spaceBefore=10, spaceAfter=6)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=4)
    mono = ParagraphStyle("mono", parent=styles["Code"], fontName="Courier", fontSize=8.6, leading=11, textColor=INK)
    center = ParagraphStyle("center", parent=body, alignment=TA_CENTER)

    def table(rows, widths, header=True, align_right_from=1, font_size=8.5):
        data = [[Paragraph(str(cell), small if index == 0 and header else ParagraphStyle("cell", parent=body, fontSize=font_size, leading=font_size + 3, spaceAfter=0)) if not isinstance(cell, Paragraph) else cell for cell in row] for index, row in enumerate(rows)]
        t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        style = [
            ("GRID", (0, 0), (-1, -1), 0.25, LINE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (align_right_from, 1 if header else 0), (-1, -1), "RIGHT"),
        ]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), GREEN), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
            data[0] = [Paragraph(f"<font color='white'><b>{cell}</b></font>", small) for cell in rows[0]]
            t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle(style))
        return t

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.75 * inch, 0.5 * inch, "Maple Street Apartments · Offering Memorandum · MOCK DOCUMENT FOR DEMONSTRATION — all figures are fictional")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.8 * inch, bottomMargin=0.8 * inch, title="Maple Street Apartments — Offering Memorandum (mock)", author="Deal Scope demo kit")
    story = []

    # ---- Cover
    story += [
        Spacer(1, 1.6 * inch),
        Paragraph("OFFERING MEMORANDUM", ParagraphStyle("kicker", parent=body, fontSize=11, textColor=GREEN, alignment=TA_CENTER, spaceAfter=14)),
        Paragraph(PROPERTY["name"], ParagraphStyle("title", parent=h1, fontSize=30, leading=36, alignment=TA_CENTER)),
        Paragraph(f"{PROPERTY['units']}-unit Class {PROPERTY['class']} garden-style community · {PROPERTY['address']}", center),
        Spacer(1, 0.4 * inch),
        Paragraph(f"Guidance price {money(PROPERTY['asking'])} · {pct(figures['cap'], 2)} in-place capitalization rate · {money(PROPERTY['asking'] / PROPERTY['units'])} per unit", center),
        Spacer(1, 2.2 * inch),
        Paragraph("Prepared by Northgate Capital Advisors (fictional) · October 2026", center),
        Paragraph("This document is a mock offering memorandum created for a product demonstration. The property, market, counterparties, and every figure are fictional.", ParagraphStyle("notice", parent=small, alignment=TA_CENTER, spaceBefore=12)),
        PageBreak(),
    ]

    # ---- Disclaimer
    story += [
        Paragraph("Confidentiality and disclaimer", h1),
        Paragraph(
            "This Offering Memorandum has been prepared to provide summary information to prospective purchasers and to establish a preliminary level of interest in the property described herein. It does not purport to be all-inclusive or to contain all of the information a prospective purchaser may require. All financial projections are provided for general reference and are based on assumptions relating to the general economy, competition, and other factors beyond the control of the owner and are therefore subject to material variation.",
            body,
        ),
        Paragraph(
            "Prospective purchasers should conduct their own independent investigation and rely solely on that investigation. Neither the owner nor the broker makes any representation or warranty as to the accuracy or completeness of the information contained herein. Historical operating figures are presented as reported by ownership and have not been audited.",
            body,
        ),
        Paragraph("Demonstration notice", h2),
        Paragraph(
            "This is a mock document generated for the Deal Scope product demonstration. Maple Street Apartments, Springfield, Northgate Capital Advisors, every comparable property, and every statistic are fictional. The packet exists so the demonstration can show a complete, realistic deal flowing from a broker package into an underwriting workspace. Appendix A contains the Deal Scope Data Sheet that the application reads directly; Appendix B lists the information the model requires.",
            body,
        ),
        PageBreak(),
    ]

    # ---- Executive summary
    offering_rows = [
        ["Offering summary", ""],
        ["Guidance price", money(PROPERTY["asking"])],
        ["Price per unit", money(PROPERTY["asking"] / PROPERTY["units"])],
        ["Price per rentable SF", f"${PROPERTY['asking'] / PROPERTY['sf']:,.2f}"],
        ["In-place NOI (trailing twelve months)", money(figures["noi"])],
        ["In-place capitalization rate", pct(figures["cap"], 2)],
        ["Units / rentable SF", f"{PROPERTY['units']} / {PROPERTY['sf']:,}"],
        ["Year built", str(PROPERTY["year_built"])],
        ["Occupancy (physical, at offering)", "95.8%"],
        ["Average in-place rent", money(figures["in_place"] / PROPERTY["units"] / 12) + " per month"],
        ["Average market rent", money(figures["market"] / PROPERTY["units"] / 12) + " per month"],
        ["Loss to lease", pct(1 - figures["in_place"] / figures["market"])],
    ]
    story += [
        Paragraph("Executive summary", h1),
        Paragraph(
            f"Northgate Capital Advisors is pleased to present {PROPERTY['name']}, a {PROPERTY['units']}-unit, {PROPERTY['stories']}-story garden-style community built in {PROPERTY['year_built']} on {PROPERTY['lot_acres']} acres in Springfield's Maple District. The property is 95.8% occupied with in-place rents approximately {pct(1 - figures['in_place'] / figures['market'])} below the submarket, offering a new owner immediate upside through a light interior program and disciplined management.",
            body,
        ),
        table(offering_rows, [3.4 * inch, 2.6 * inch]),
        Paragraph("Investment highlights", h2),
    ]
    for text in (
        "<b>Stable in-place cash flow.</b> Trailing-twelve-month NOI of " + money(figures["noi"]) + " on " + money(figures["pgi"]) + " of gross potential income, with physical occupancy above 95% in each of the last eight quarters.",
        "<b>Demonstrated rent upside.</b> Comparable renovated communities achieve rents " + pct(figures["market"] / figures["in_place"] - 1) + " above Maple Street's in-place roll; 14 units turned in the last year achieved market rents with a $6,200 average interior scope.",
        "<b>Attractive basis.</b> At guidance the price per unit sits below the trailing comparable-sale average of $155,800 and below estimated replacement cost of roughly $210,000 per unit.",
        "<b>Favourable debt market.</b> Agency and regional-bank quotes for comparable Class B assets are in the high-5% to low-6% range at 55% to 65% loan-to-value with 30-year amortization.",
        "<b>Supply-constrained submarket.</b> No new garden-style product has delivered within two miles since 2019, and the planning pipeline shows one 112-unit project not expected before 2028.",
    ):
        story.append(Paragraph(text, bullet, bulletText="•"))
    story.append(PageBreak())

    # ---- Property description
    story += [
        Paragraph("Property description", h1),
        table(
            [
                ["Attribute", "Detail"],
                ["Address", PROPERTY["address"]],
                ["Property type / class", f"{PROPERTY['type']} / Class {PROPERTY['class']}"],
                ["Year built / renovated", f"{PROPERTY['year_built']} / common areas 2019"],
                ["Buildings / stories", f"4 / {PROPERTY['stories']}"],
                ["Units / average unit size", f"{PROPERTY['units']} / {PROPERTY['sf'] // PROPERTY['units']:,} SF"],
                ["Rentable area / site", f"{PROPERTY['sf']:,} SF / {PROPERTY['lot_acres']} acres"],
                ["Parking", f"{PROPERTY['parking']} surface spaces (1.5 per unit), 48 reserved"],
                ["Construction", "Wood frame over slab, brick and fibre-cement exterior, pitched asphalt shingle roofs (2017)"],
                ["Mechanical", "Individual electric HVAC with heat pumps, individually metered electricity, master-metered water"],
                ["Amenities", "Leasing office, fitness room, laundry facility, dog run, outdoor grilling area"],
                ["Zoning", "RM-3 multifamily residential (conforming)"],
            ],
            [2.0 * inch, 4.0 * inch],
            align_right_from=2,
        ),
        Paragraph("Unit mix", h2),
        table(
            [["Unit type", "Units", "Avg SF", "In-place rent", "In-place rent / SF", "Market rent", "Market rent / SF"]]
            + [[name, str(units), f"{sf:,}", money(rent), f"${rent / sf:.2f}", money(market), f"${market / sf:.2f}"] for name, units, sf, rent, market in RENT_ROLL]
            + [["Total / weighted", str(PROPERTY["units"]), f"{PROPERTY['sf'] // PROPERTY['units']:,}", money(figures["in_place"] / PROPERTY["units"] / 12), f"${figures['in_place'] / 12 / PROPERTY['sf']:.2f}", money(figures["market"] / PROPERTY["units"] / 12), f"${figures['market'] / 12 / PROPERTY['sf']:.2f}"]],
            [1.3 * inch, 0.6 * inch, 0.7 * inch, 0.95 * inch, 1.05 * inch, 0.95 * inch, 1.05 * inch],
        ),
        Paragraph("Interiors feature laminate flooring in living areas, black appliance packages, and laminate countertops. Fourteen units (29%) have been upgraded with quartz counters, stainless appliances, and LED lighting and are achieving the market rents shown above.", body),
        PageBreak(),
    ]

    # ---- Location and market
    story += [
        Paragraph("Location and market overview", h1),
        Paragraph(
            "Springfield (metro population 412,000) is a regional health-care, logistics, and education hub. The Maple District sits two miles east of the central business district with direct access to Route 9, the Springfield Medical Center campus (6,400 jobs), and the Eastside logistics corridor. Average household income within a three-mile radius is $71,900 and renter households represent 54% of the three-mile population.",
            body,
        ),
        table(
            [
                ["Demographic (fictional)", "1 mile", "3 miles", "5 miles"],
                ["Population (2026)", "11,840", "68,200", "148,600"],
                ["Population growth (2020–2026)", "4.1%", "5.6%", "6.2%"],
                ["Households", "5,120", "27,900", "60,100"],
                ["Renter share", "61%", "54%", "47%"],
                ["Average household income", "$64,300", "$71,900", "$78,400"],
                ["Median age", "33.1", "35.4", "36.8"],
            ],
            [2.6 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch],
        ),
        Paragraph("Employment", h2),
        table(
            [
                ["Major employer (fictional)", "Sector", "Employees", "Distance"],
                ["Springfield Medical Center", "Health care", "6,400", "1.4 miles"],
                ["Riverbend University", "Education", "3,900", "3.2 miles"],
                ["Eastside Logistics Park", "Distribution", "2,750", "2.8 miles"],
                ["Harrow Precision Components", "Manufacturing", "1,420", "4.6 miles"],
                ["County of Springfield", "Government", "2,100", "2.1 miles"],
            ],
            [2.6 * inch, 1.3 * inch, 1.0 * inch, 1.0 * inch],
        ),
        Paragraph("Submarket fundamentals", h2),
        table(
            [
                ["Metric (fictional)", "2023", "2024", "2025", "2026 YTD"],
                ["Submarket occupancy", "94.9%", "95.4%", "95.9%", "96.1%"],
                ["Effective rent growth", "2.4%", "3.1%", "3.3%", "3.0%"],
                ["Units delivered", "0", "0", "0", "0"],
                ["Units under construction", "0", "0", "112", "112"],
                ["Class B average cap rate", "6.1%", "6.4%", "6.6%", "6.5%"],
            ],
            [2.2 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch],
        ),
        PageBreak(),
    ]

    # ---- Rent roll
    story += [
        Paragraph("Rent roll and income", h1),
        Paragraph("Summary rent roll as of 30 September 2026. Individual lease detail is available in the data room; the summary below is the basis for the trailing and pro forma income statements.", body),
        table(
            [["Unit type", "Units", "Avg SF", "Current rent / mo", "Market rent / mo", "Annual in-place", "Annual market", "Loss to lease"]]
            + [[name, str(units), f"{sf:,}", money(rent), money(market), money(units * rent * 12), money(units * market * 12), pct(1 - rent / market)] for name, units, sf, rent, market in RENT_ROLL]
            + [["Total", str(PROPERTY["units"]), "", money(figures["in_place"] / PROPERTY["units"] / 12), money(figures["market"] / PROPERTY["units"] / 12), money(figures["in_place"]), money(figures["market"]), pct(1 - figures["in_place"] / figures["market"])]],
            [1.15 * inch, 0.5 * inch, 0.6 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch, 0.75 * inch],
        ),
        Paragraph("Other income", h2),
        table([["Category", "Annual amount", "Basis"]] + [[name, money(amount), note] for name, amount, note in OTHER_INCOME] + [["Total other income", money(figures["other"]), ""]], [2.0 * inch, 1.3 * inch, 2.7 * inch], align_right_from=1),
        Paragraph("Leasing and occupancy history", h2),
        table(
            [
                ["Quarter", "Physical occupancy", "Average in-place rent", "Renewal rate", "Renewal trade-out"],
                ["Q4 2024", "95.8%", "$1,436", "58%", "2.9%"],
                ["Q1 2025", "95.8%", "$1,448", "61%", "3.1%"],
                ["Q2 2025", "97.9%", "$1,462", "55%", "3.4%"],
                ["Q3 2025", "95.8%", "$1,471", "60%", "3.2%"],
                ["Q4 2025", "95.8%", "$1,480", "63%", "2.8%"],
                ["Q1 2026", "97.9%", "$1,489", "59%", "3.0%"],
                ["Q2 2026", "95.8%", "$1,494", "57%", "3.1%"],
                ["Q3 2026", "95.8%", money(figures["in_place"] / PROPERTY["units"] / 12), "62%", "3.0%"],
            ],
            [1.0 * inch, 1.3 * inch, 1.5 * inch, 1.1 * inch, 1.1 * inch],
        ),
        PageBreak(),
    ]

    # ---- Financial summary
    pro_forma_pgi = figures["market"] + figures["other"] * 1.02
    pro_forma_vac = pro_forma_pgi * 0.05
    pro_forma_egi = pro_forma_pgi - pro_forma_vac
    pro_forma_opex = figures["opex"] * 1.025
    story += [
        Paragraph("Financial summary", h1),
        Paragraph("The trailing twelve months (T-12) reflect actual collections and expenses through September 2026 as reported by ownership. The broker pro forma applies market rents to all units with a 5% economic vacancy allowance and grows expenses 2.5%. Deal Scope underwrites from the in-place column; the pro forma is shown for reference only.", body),
        table(
            [
                ["Line item", "T-12 (in place)", "Per unit", "Broker pro forma", "Per unit"],
                ["Gross potential rent", money(figures["in_place"]), money(figures["in_place"] / 48), money(figures["market"]), money(figures["market"] / 48)],
                ["Other income", money(figures["other"]), money(figures["other"] / 48), money(figures["other"] * 1.02), money(figures["other"] * 1.02 / 48)],
                ["Gross potential income", money(figures["pgi"]), money(figures["pgi"] / 48), money(pro_forma_pgi), money(pro_forma_pgi / 48)],
                ["Vacancy and credit loss (5.0%)", f"({money(figures['vacancy'])})", f"({money(figures['vacancy'] / 48)})", f"({money(pro_forma_vac)})", f"({money(pro_forma_vac / 48)})"],
                ["Effective gross income", money(figures["egi"]), money(figures["egi"] / 48), money(pro_forma_egi), money(pro_forma_egi / 48)],
                ["Operating expenses", f"({money(figures['opex'])})", f"({money(figures['opex'] / 48)})", f"({money(pro_forma_opex)})", f"({money(pro_forma_opex / 48)})"],
                ["Net operating income", money(figures["noi"]), money(figures["noi"] / 48), money(pro_forma_egi - pro_forma_opex), money((pro_forma_egi - pro_forma_opex) / 48)],
                ["Expense ratio (OpEx / EGI)", pct(figures["opex"] / figures["egi"]), "", pct(pro_forma_opex / pro_forma_egi), ""],
                ["Capitalization rate at guidance", pct(figures["cap"], 2), "", pct((pro_forma_egi - pro_forma_opex) / PROPERTY["asking"], 2), ""],
            ],
            [2.2 * inch, 1.1 * inch, 0.8 * inch, 1.2 * inch, 0.8 * inch],
        ),
        Paragraph("Operating expense detail (T-12)", h2),
        table(
            [["Category", "Annual", "Per unit", "% of EGI", "Note"]]
            + [[name, money(amount), money(amount / 48), pct(amount / figures["egi"]), note] for name, amount, note in EXPENSES]
            + [["Total operating expenses", money(figures["opex"]), money(figures["opex"] / 48), pct(figures["opex"] / figures["egi"]), ""]],
            [1.7 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch, 1.9 * inch],
        ),
        Paragraph("Real estate taxes reflect the current assessment. Purchasers should underwrite a reassessment at the transaction price; at Springfield's 1.42% effective rate a sale at guidance would imply taxes of approximately $120,700.", small),
        PageBreak(),
    ]

    # ---- Capital plan
    story += [
        Paragraph("Capital improvements and value-add plan", h1),
        Paragraph("Ownership completed roof replacement (2017), common-area refresh and fitness room (2019), and an LED exterior lighting retrofit (2023). The remaining opportunity is an interior upgrade program across the 34 classic units.", body),
        table(
            [
                ["Program element", "Scope", "Units", "Cost per unit", "Total", "Rent premium"],
                ["Classic interior upgrade", "Quartz counters, stainless appliances, LED lighting, hardware", "34", "$6,200", "$210,800", "$55–$80 / month"],
                ["Washer-dryer connections", "In-unit connections where plumbing allows", "20", "$2,400", "$48,000", "$35 / month"],
                ["Smart locks and thermostats", "Keyless entry, programmable thermostats", "48", "$650", "$31,200", "$15 / month"],
                ["Deferred maintenance reserve", "Asphalt seal coat, drainage, exterior paint touch-up", "—", "—", "$85,000", "—"],
                ["Total identified capital", "", "", "", "$375,000", ""],
            ],
            [1.5 * inch, 1.9 * inch, 0.5 * inch, 0.75 * inch, 0.75 * inch, 0.9 * inch],
        ),
        Paragraph("The capital plan is presented as a buyer's opportunity and is not included in the trailing figures or in the Deal Scope Data Sheet, which captures the in-place operating position. Buyers who intend to execute the program should model it explicitly.", small),
        Paragraph("Financing overview", h2),
        Paragraph("Indicative terms gathered from two agency lenders and one regional bank in September 2026 for a stabilized Class B multifamily acquisition of this size. Terms are indicative only and subject to full underwriting.", body),
        table(
            [
                ["Term (indicative, fictional)", "Agency quote", "Regional bank quote"],
                ["Loan-to-value", "60% to 65%", "55% to 60%"],
                ["Interest rate", "5.85% to 6.10% fixed", "6.15% to 6.40% fixed"],
                ["Amortization", "30 years", "25 to 30 years"],
                ["Term", "7 or 10 years", "5 years"],
                ["Interest-only period", "Up to 2 years", "None"],
                ["Minimum DSCR", "1.25x", "1.25x to 1.30x"],
                ["Origination fee", "1.0%", "0.5%"],
            ],
            [2.4 * inch, 1.8 * inch, 1.8 * inch],
            align_right_from=3,
        ),
        PageBreak(),
    ]

    # ---- Comparables
    story += [
        Paragraph("Sale comparables", h1),
        Paragraph("Five Class B garden-style transactions within the Springfield metro over the trailing fifteen months. Cap rates are reported on trailing NOI at closing.", body),
        table(
            [["Property (fictional)", "Submarket", "Built", "Units", "Price", "Price / unit", "Cap rate", "Closed"]]
            + [[name, sub, str(built), str(units), money(price), money(ppu), pct(cap, 2), closed] for name, sub, built, units, price, ppu, cap, closed in SALE_COMPS]
            + [["Average", "", "", str(round(sum(c[3] for c in SALE_COMPS) / 5)), money(sum(c[4] for c in SALE_COMPS) / 5), money(sum(c[5] for c in SALE_COMPS) / 5), pct(sum(c[6] for c in SALE_COMPS) / 5, 2), ""]],
            [1.45 * inch, 0.8 * inch, 0.45 * inch, 0.45 * inch, 0.95 * inch, 0.8 * inch, 0.6 * inch, 0.7 * inch],
        ),
        Paragraph(f"Maple Street Apartments at guidance: {money(PROPERTY['asking'] / 48)} per unit and a {pct(figures['cap'], 2)} in-place cap rate, inside the comparable range on both measures.", body),
        Paragraph("Rent comparables", h2),
        table(
            [["Property (fictional)", "Built", "Studio", "1 bed", "2 bed", "Occupancy"]]
            + [[name, str(built), money(s), money(one), money(two), pct(occ)] for name, built, s, one, two, occ in RENT_COMPS]
            + [["Average", "", money(sum(c[2] for c in RENT_COMPS) / 5), money(sum(c[3] for c in RENT_COMPS) / 5), money(sum(c[4] for c in RENT_COMPS) / 5), pct(sum(c[5] for c in RENT_COMPS) / 5)]]
            + [["Maple Street (in place)", str(PROPERTY["year_built"]), money(RENT_ROLL[0][3]), money(RENT_ROLL[1][3]), money(RENT_ROLL[2][3]), "95.8%"]]
            + [["Maple Street (market)", "", money(RENT_ROLL[0][4]), money(RENT_ROLL[1][4]), money(RENT_ROLL[2][4]), ""]],
            [1.9 * inch, 0.6 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 0.9 * inch],
        ),
        Paragraph("Capital markets context", h2),
        table(
            [
                ["Indicator (fictional)", "Q3 2024", "Q1 2025", "Q3 2025", "Q1 2026", "Q3 2026"],
                ["10-year Treasury", "3.95%", "4.20%", "4.05%", "4.15%", "4.10%"],
                ["Agency multifamily coupon (60% LTV)", "5.70%", "6.05%", "5.95%", "6.00%", "5.95%"],
                ["Springfield Class B cap rate", "6.30%", "6.50%", "6.60%", "6.55%", "6.50%"],
                ["Spread: cap rate less Treasury", "2.35%", "2.30%", "2.55%", "2.40%", "2.40%"],
            ],
            [2.3 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch],
        ),
        PageBreak(),
    ]

    # ---- Risk factors
    story += [Paragraph("Risk factors", h1)]
    for text in (
        "<b>Property tax reassessment.</b> Taxes are likely to reset to the transaction price. The data sheet carries the trailing figure; buyers should sensitise expenses for a reassessment of roughly $2,700 per year above trailing.",
        "<b>Interest-rate exposure.</b> A 100 basis point increase in the note rate reduces Year 1 cash flow after debt service by roughly $45,000 at 60% leverage and compresses the supportable price materially.",
        "<b>Exit cap rate.</b> Each 25 basis points of exit cap expansion reduces the reversion value by roughly 3.7%. The Deal Scope sensitivity grids quantify this at the solved price.",
        "<b>Loss-to-lease realisation.</b> The pro forma assumes market rents on all units; achieving them requires completing the interior program and absorbing turnover vacancy.",
        "<b>Single-market concentration.</b> Performance depends on Springfield's health-care and logistics employers; a contraction at Springfield Medical Center would weigh on demand.",
        "<b>Insurance and utilities.</b> Insurance premiums rose 18% at the 2026 renewal across the region; master-metered water exposes ownership to utility inflation.",
    ):
        story.append(Paragraph(text, bullet, bulletText="•"))
    story += [
        Paragraph("Offering process", h2),
        Paragraph("Offers are requested by 14 November 2026 with proof of funds and a summary of financing. Tours are available Tuesdays and Thursdays by appointment. The data room contains the full rent roll, leases, T-12 general ledger, tax bills, insurance policies, service contracts, and the 2026 property condition report.", body),
        PageBreak(),
    ]

    # ---- Appendix A: data sheet (machine readable)
    sheet_lines = [
        "DEAL SCOPE DATA SHEET  (version 1)",
        "Plain-text appendix read directly by Deal Scope. Keep one Label: Value per line.",
        "",
        "Property name: Maple Street Apartments",
        "Address: 100 Maple Street, Springfield",
        "Property type: Multifamily",
        "Property class: B",
        f"Units: {PROPERTY['units']}",
        f"Rentable square feet: {PROPERTY['sf']:,}",
        f"Year built: {PROPERTY['year_built']}",
        "",
        f"Purchase price (asking or guide): {PROPERTY['asking']:,}",
        f"Closing costs: {pct(ASSUMPTIONS['closing_costs'])}",
        f"Hold period: {ASSUMPTIONS['hold']}",
        f"Exit cap rate: {pct(ASSUMPTIONS['exit_cap'], 2)}",
        f"Selling costs: {pct(ASSUMPTIONS['selling_costs'])}",
        "",
        "Current potential gross income: (roll up from rent roll and other income)",
        "Current operating expenses: (roll up from operating expenses)",
        f"Vacancy and credit loss: {pct(ASSUMPTIONS['vacancy'])}",
        f"Rent growth: {pct(ASSUMPTIONS['rent_growth'])}",
        f"Expense growth: {pct(ASSUMPTIONS['expense_growth'])}",
        "Rent growth schedule: n/a",
        "Year 1 convention: Current",
        "",
        f"Loan-to-value: {pct(ASSUMPTIONS['ltv'])}",
        f"Interest rate: {pct(ASSUMPTIONS['rate'], 2)}",
        f"Amortization: {ASSUMPTIONS['amort']}",
        "",
        f"Target levered IRR: {pct(ASSUMPTIONS['target_irr'])}",
        f"Minimum DSCR: {ASSUMPTIONS['min_dscr']:.2f}",
        "",
        "Version label: Broker OM base case",
        "Source or document reference: Northgate Capital Advisors offering memorandum, October 2026 (mock)",
        f"Effective date: {date(2026, 9, 30).isoformat()}",
        "Confidence: Medium",
        "",
        "RENT ROLL",
        "Unit type | Units | Average square feet | Current monthly rent | Market monthly rent",
    ]
    sheet_lines += [f"{name} | {units} | {sf} | {rent} | {market}" for name, units, sf, rent, market in RENT_ROLL]
    sheet_lines += ["", "OTHER INCOME", "Category | Annual amount | Note"]
    sheet_lines += [f"{name} | {amount} | {note}" for name, amount, note in OTHER_INCOME]
    sheet_lines += ["", "OPERATING EXPENSES", "Category | Annual amount | Note"]
    sheet_lines += [f"{name} | {amount} | {note}" for name, amount, note in EXPENSES]
    sheet_lines += ["", "END OF DATA SHEET"]
    story += [
        Paragraph("Appendix A — Deal Scope Data Sheet", h1),
        Paragraph(
            "This appendix restates the offering's underwriting inputs in the Deal Scope Data Sheet format so the packet can be imported directly. Labels match the Excel import template and are matched flexibly; percentages may be written as 5%, 5 or 0.05. Income and expense totals are left to roll up from the tables so the detail is preserved.",
            body,
        ),
        Preformatted("\n".join(sheet_lines), mono),
        PageBreak(),
    ]

    # ---- Appendix B: data requirements
    story += [
        Paragraph("Appendix B — What Deal Scope needs to underwrite a deal", h1),
        Paragraph("A complete underwriting needs the eleven required inputs below; everything else enriches the output. A packet that provides them all, in a data sheet or in the Excel template, builds the deal in one import.", body),
        table(
            [
                ["Input", "Required", "Why it matters", "In this packet"],
                ["Purchase price (asking or guide)", "Yes", "Seeds the solver and the going-in cap rate", "Executive summary"],
                ["Closing costs (%)", "Yes", "Funded with equity; part of total cost", "Data sheet"],
                ["Hold period (5–10 years)", "Yes", "Length of the pro forma and the sale year", "Data sheet"],
                ["Exit cap rate", "Yes", "Capitalizes forward NOI into the sale price", "Capital markets context"],
                ["Selling costs (%)", "Yes", "Deducted from the gross sale price", "Data sheet"],
                ["Current potential gross income", "Yes*", "Year 1 revenue before vacancy", "Rent roll + other income"],
                ["Current operating expenses", "Yes*", "Year 1 expenses", "Operating expense detail"],
                ["Vacancy and credit loss", "Yes", "Converts potential to effective income", "Financial summary"],
                ["Rent growth / expense growth", "Yes", "Drive NOI through the hold", "Submarket fundamentals"],
                ["Loan-to-value, interest rate, amortization", "Yes", "Debt service, DSCR and payoff", "Financing overview"],
                ["Target levered IRR, minimum DSCR", "Recommended", "The two constraints the solver prices to", "Data sheet"],
                ["Units, square feet, class, year built", "Optional", "Per-unit and per-SF metrics", "Property description"],
                ["Rent roll by unit type", "Optional", "Roll-up of income, loss-to-lease, exports", "Rent roll"],
                ["Other income and expense line items", "Optional", "Expense ratios, per-unit detail, exports", "Financial summary"],
                ["Version label, source, effective date, confidence", "Recommended", "Audit trail for the saved version", "Data sheet"],
            ],
            [2.0 * inch, 0.8 * inch, 2.0 * inch, 1.2 * inch],
            align_right_from=4,
        ),
        Paragraph("* Either the aggregate figure or the detail table that rolls up to it.", small),
        Paragraph("Packet size", h2),
        Paragraph("A typical broker offering memorandum runs 25 to 60 pages, most of it photography and market narrative. The information Deal Scope needs fits on the two pages of Appendix A. This demonstration packet is kept to roughly fifteen pages so it can be read in a meeting while still showing where each input comes from.", body),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    for written in build(target):
        print("wrote", written)
