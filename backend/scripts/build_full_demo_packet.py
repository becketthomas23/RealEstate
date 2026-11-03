"""Build the full-length mock offering memorandum for the Deal Scope demo kit.

The short packet from ``build_demo_packet.py`` fits in a meeting. This one is
the fifty-plus page broker package an analyst actually receives, with the two
pages the model needs buried at the back as Appendix A. Every figure
reconciles to the same deal (PGI $909,600, operating expenses $405,400, 48
units), so importing either file produces the same version. Run from
``backend``:

    uv run python scripts/build_full_demo_packet.py ../demo
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_demo_packet import ASSUMPTIONS, EXPENSES, OTHER_INCOME, PROPERTY, RENT_ROLL  # noqa: E402

GREEN = colors.HexColor("#166534")
INK = colors.HexColor("#16201B")
MUTED = colors.HexColor("#6B746E")
LINE = colors.HexColor("#D9DED8")
PAPER = colors.HexColor("#F4F5F1")

# ----------------------------------------------------------------- comparables (extended detail for the long form)
SALE_COMPS = (
    ("Riverside Commons", "2200 Riverside Drive, Springfield", 2001, 64, 9_900_000, 0.0640, "Mar 2026", "Garden, 2 stories, pool, renovated 2019", "Pinnacle Residential REIT", "Harbor Lane Capital"),
    ("Oak Hollow Flats", "415 Oak Hollow Road, Springfield", 1995, 40, 6_250_000, 0.0665, "Jan 2026", "Garden, 3 stories, surface parking, original finishes", "Oak Hollow Owner LLC", "Crestline Partners"),
    ("Parkview Terrace", "90 Parkview Avenue, Westbrook", 2004, 72, 12_100_000, 0.0620, "Nov 2025", "Garden, 3 stories, clubhouse, fitness, 40% renovated", "Westbrook Multifamily Fund II", "Meridian Housing Trust"),
    ("Linden Court", "18 Linden Court, Springfield", 1989, 36, 5_200_000, 0.0690, "Sep 2025", "Walk-up, 2 stories, carports, value-add", "Private seller", "Lindenwood Investments"),
    ("Cedar Point Residences", "700 Cedar Point Boulevard, Eastfield", 1999, 56, 8_700_000, 0.0650, "Jul 2025", "Garden, 3 stories, pool, dog park", "Cedar Point Associates", "Eastfield Residential LP"),
)
RENT_COMPS = (
    ("Riverside Commons", 2001, 64, 1_195, 1_480, 1_910, 0.96, "Pool, fitness, in-unit laundry (renovated units)", 0.8),
    ("Oak Hollow Flats", 1995, 40, 1_125, 1_410, 1_825, 0.95, "Laundry room, playground", 1.1),
    ("Parkview Terrace", 2004, 72, 1_260, 1_525, 1_980, 0.97, "Clubhouse, fitness, pool, package lockers", 2.4),
    ("Linden Court", 1989, 36, 1_095, 1_360, 1_760, 0.94, "Carports, laundry room", 0.6),
    ("Cedar Point Residences", 1999, 56, 1_175, 1_455, 1_880, 0.96, "Pool, dog park, grilling area", 3.2),
)
MONTHS = ("Oct 2025", "Nov 2025", "Dec 2025", "Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026")
SHORT_MONTHS = ("Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep")


def money(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def figures() -> dict[str, float]:
    in_place = sum(u * r * 12 for _, u, _, r, _ in RENT_ROLL)
    market = sum(u * m * 12 for _, u, _, _, m in RENT_ROLL)
    other = sum(a for _, a, _ in OTHER_INCOME)
    pgi = in_place + other
    vacancy = pgi * ASSUMPTIONS["vacancy"]
    egi = pgi - vacancy
    opex = sum(a for _, a, _ in EXPENSES)
    noi = egi - opex
    return {"in_place": in_place, "market": market, "other": other, "pgi": pgi, "vacancy": vacancy, "egi": egi, "opex": opex, "noi": noi, "cap": noi / PROPERTY["asking"]}


def split_months(total: int, profile: tuple[float, ...]) -> list[int]:
    """Spread an annual total over twelve months with a seasonal profile; sums exactly."""
    weight = sum(profile)
    parts = [round(total * p / weight) for p in profile]
    parts[-1] += total - sum(parts)
    return parts


FLAT = tuple([1.0] * 12)
UTILITY_PROFILE = (0.9, 1.0, 1.2, 1.3, 1.25, 1.05, 0.85, 0.8, 0.9, 1.0, 1.0, 0.85)
REPAIR_PROFILE = (1.0, 0.8, 0.7, 0.9, 0.8, 1.1, 1.2, 1.3, 1.4, 1.3, 1.1, 0.9)
MARKETING_PROFILE = (0.8, 0.6, 0.5, 0.9, 1.0, 1.3, 1.4, 1.5, 1.4, 1.2, 1.0, 0.9)


def unit_rent_roll() -> list[tuple[str, str, int, int, int, str, str]]:
    """48 units, one row each. Rents vary around the unit-type average and sum to it exactly."""
    rows = []
    buildings = ("A", "B", "C")
    unit_number = 0
    offsets_cycle = (-25, 0, 25, 10, -10, 15, -15, 0)
    for name, units, sf, rent, market in RENT_ROLL:
        offsets = [offsets_cycle[i % len(offsets_cycle)] for i in range(units)]
        offsets[-1] -= sum(offsets)  # force the total to units * rent
        for i in range(units):
            unit_number += 1
            building = buildings[(unit_number - 1) % 3]
            floor = ((unit_number - 1) // 3) % 3 + 1
            number = f"{building}-{floor}{(unit_number % 8) + 1:02d}"
            start_month = (unit_number * 7) % 12
            lease_start = date(2025 + (1 if start_month < 6 else 0), start_month + 1, 1)
            lease_end = date(lease_start.year + 1, lease_start.month, 1)
            status = "Occupied" if unit_number not in (7, 19, 33) else "Vacant"
            rows.append((number, name, sf + ((unit_number % 3) - 1) * 10, rent + offsets[i] if status == "Occupied" else 0, market, lease_start.isoformat() if status == "Occupied" else "", lease_end.isoformat() if status == "Occupied" else ""))
    return rows


# ----------------------------------------------------------------- document

TOC_ENTRIES = (
    ("1", "Executive Summary", "1. Executive Summary"), ("2", "Investment Highlights", "2. Investment Highlights"), ("3", "Property Description", "3. Property Description"), ("4", "Unit Mix and Floor Plans", "4. Unit Mix and Floor Plans"), ("5", "Rent Roll", "5. Rent Roll"),
    ("6", "Lease Expiration Schedule", "6. Lease Expiration Schedule"), ("7", "Historical Operating Statements", "7. Historical Operating Statements"), ("8", "Trailing Twelve Month Detail", "8. Trailing Twelve Month Detail"), ("9", "Expense Analysis", "9. Expense Analysis"), ("10", "Capital Improvements", "10. Capital Improvements"),
    ("11", "Regional Economy", "11. Regional Economy"), ("12", "Demographics", "12. Demographics"), ("13", "Submarket Apartment Fundamentals", "13. Submarket Apartment Fundamentals"), ("14", "Rent Comparables", "14. Rent Comparables"), ("15", "Sale Comparables", "15. Sale Comparables"),
    ("16", "New Supply Pipeline", "16. New Supply Pipeline"), ("17", "Financing Overview", "17. Financing Overview"), ("18", "Taxes, Insurance, and Utilities", "18. Taxes, Insurance, and Utilities"), ("19", "Zoning, Environmental, and Physical Condition", "19. Zoning, Environmental, and Physical Condition"), ("20", "Property Management", "20. Property Management"),
    ("21", "Offering Process", "21. Offering Process"), ("A", "Appendix A — Deal Scope Data Sheet", "Appendix A — Deal Scope Data Sheet"), ("B", "Appendix B — Data Requirements", "Appendix B — What Deal Scope needs"), ("C", "Appendix C — Glossary", "Appendix C — Glossary"),
)


def page_index(path: Path) -> dict[str, str]:
    """Find the page each section heading lands on, for the contents page."""
    from pypdf import PdfReader

    pages = [" ".join((page.extract_text() or "").split()) for page in PdfReader(str(path)).pages]
    found: dict[str, str] = {}
    for _, _, heading in TOC_ENTRIES:
        needle = " ".join(heading.split())
        for number, text in enumerate(pages, start=1):
            if number > 3 and needle in text:
                found[heading] = str(number)
                break
    return found


def build(output_dir: Path, toc_pages: dict[str, str] | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "Maple Street Apartments - Full Offering Memorandum (mock).pdf"
    toc_pages = toc_pages or {}
    fig = figures()
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=14, textColor=INK, spaceAfter=6)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=MUTED)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=20, leading=24, textColor=GREEN, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, leading=16, textColor=INK, spaceBefore=10, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=h2, fontSize=11, leading=14, spaceBefore=6, spaceAfter=4)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=4)
    mono = ParagraphStyle("mono", parent=styles["Code"], fontName="Courier", fontSize=8.6, leading=11, textColor=INK)
    center = ParagraphStyle("center", parent=body, alignment=TA_CENTER)
    kicker = ParagraphStyle("kicker", parent=body, fontSize=11, textColor=GREEN, alignment=TA_CENTER, spaceAfter=14)

    def table(rows, widths, header=True, align_right_from=1, font_size=8.5, zebra=True):
        cell_style = ParagraphStyle("cell", parent=body, fontSize=font_size, leading=font_size + 3, spaceAfter=0)
        data = [[cell if isinstance(cell, Paragraph) else Paragraph(str(cell), cell_style) for cell in row] for row in rows]
        style = [("GRID", (0, 0), (-1, -1), 0.25, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("ALIGN", (align_right_from, 1 if header else 0), (-1, -1), "RIGHT")]
        if header:
            data[0] = [Paragraph(f"<font color='white'><b>{cell}</b></font>", small) for cell in rows[0]]
            style += [("BACKGROUND", (0, 0), (-1, 0), GREEN)]
        if zebra:
            for index in range(1 if header else 0, len(rows)):
                if index % 2 == 0:
                    style.append(("BACKGROUND", (0, index), (-1, index), PAPER))
        t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        t.setStyle(TableStyle(style))
        return t

    def bullets(items):
        return [Paragraph(item, bullet, bulletText="•") for item in items]

    def section(title, intro=None):
        out = [Paragraph(title, h1)]
        if intro:
            out.append(Paragraph(intro, body))
        return out

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.75 * inch, 0.5 * inch, "Maple Street Apartments · Offering Memorandum · Northgate Capital Advisors · MOCK DOCUMENT, all figures fictional")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.setStrokeColor(LINE)
        canvas.line(0.75 * inch, letter[1] - 0.6 * inch, letter[0] - 0.75 * inch, letter[1] - 0.6 * inch)
        canvas.drawString(0.75 * inch, letter[1] - 0.5 * inch, "CONFIDENTIAL OFFERING MEMORANDUM")
        canvas.drawRightString(letter[0] - 0.75 * inch, letter[1] - 0.5 * inch, "48 Units · Springfield")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.85 * inch, bottomMargin=0.8 * inch, title="Maple Street Apartments — Full Offering Memorandum (mock)", author="Northgate Capital Advisors (fictional)")
    story: list = []
    W = letter[0] - 1.5 * inch

    # ---- Cover
    story += [
        Spacer(1, 1.5 * inch),
        Paragraph("CONFIDENTIAL OFFERING MEMORANDUM", kicker),
        Paragraph(PROPERTY["name"], ParagraphStyle("title", parent=h1, fontSize=30, leading=36, alignment=TA_CENTER)),
        Paragraph(f"{PROPERTY['units']}-unit Class {PROPERTY['class']} garden-style community · {PROPERTY['address']}", center),
        Spacer(1, 0.3 * inch),
        Paragraph(f"Guidance price {money(PROPERTY['asking'])} · {pct(fig['cap'], 2)} in-place capitalization rate · {money(PROPERTY['asking'] / PROPERTY['units'])} per unit · {money(PROPERTY['asking'] / PROPERTY['sf'])} per square foot", center),
        Spacer(1, 2.0 * inch),
        Paragraph("Exclusively listed by", center),
        Paragraph("<b>Northgate Capital Advisors</b> · Multifamily Investment Sales", center),
        Paragraph("Dana Whitfield, Senior Managing Director · Priya Raman, Director · Tomas Alvarez, Financial Analyst", center),
        Spacer(1, 0.5 * inch),
        Paragraph("October 2026 · Mock document generated for a product demonstration. The property, the brokerage, every comparable, every tenant, and every statistic are fictional.", small),
        PageBreak(),
    ]

    # ---- Confidentiality and disclaimer (2 pages of boilerplate)
    story += section("Confidentiality and Disclaimer")
    boiler = [
        "This Confidential Offering Memorandum (the “Memorandum”) has been prepared by Northgate Capital Advisors (“Northgate”) solely for the use of prospective purchasers of Maple Street Apartments (the “Property”) and is furnished on a confidential basis. By accepting this Memorandum, the recipient agrees that it will hold the Memorandum and its contents in strict confidence, will not reproduce or distribute it in whole or in part, and will use it solely for the purpose of evaluating a possible acquisition of the Property.",
        "The information contained herein has been obtained from sources believed to be reliable, including the Owner, the Owner’s property manager, public records, and third-party market data providers. Northgate has not independently verified any of the information and makes no representation or warranty, express or implied, as to its accuracy or completeness. Any projections, opinions, assumptions, or estimates used are for example only and do not represent the current or future performance of the Property.",
        "Prospective purchasers should conduct their own independent investigation and analysis of the Property, the market, and the information presented, and should consult their own legal, tax, engineering, environmental, and accounting advisors. The Owner reserves the right, at its sole discretion, to reject any or all offers, to withdraw the Property from the market without notice, and to negotiate with any party at any time.",
        "Neither the Owner nor Northgate shall have any liability for any loss or damage arising from the use of this Memorandum or any information contained herein. No contractual obligation shall arise unless and until a definitive purchase and sale agreement has been fully executed and delivered.",
        "Photographs, renderings, site plans, and floor plans are illustrative and may not reflect current conditions. Square footages are approximate and derived from the Owner’s records and the architectural plans on file; purchasers should verify by independent measurement.",
        "Historical operating statements are unaudited and as reported by the Owner’s property manager. The trailing twelve month period presented ends 30 September 2026. Tax figures reflect the current assessment and may be reassessed upon sale at a value materially different from the current assessed value.",
        "Any references to interest rates, loan terms, or financing availability are indicative only, were provided by third-party lenders without commitment, and are subject to change without notice.",
        "This Memorandum does not constitute an offer to sell or a solicitation of an offer to buy securities. Northgate represents the Owner exclusively in this transaction.",
    ]
    story += [Paragraph(p, body) for p in boiler]
    story += [Spacer(1, 0.3 * inch), Paragraph("Acknowledgement", h2), Paragraph("Recipients are reminded that the Confidentiality Agreement executed prior to receipt of this Memorandum remains in full force and governs all communications regarding the Property, including inquiries to on-site staff and residents, which are prohibited without prior written consent of Northgate.", body), PageBreak()]

    # ---- Table of contents (static)
    story += section("Contents")
    toc = [(number, title, toc_pages.get(heading, "")) for number, title, heading in TOC_ENTRIES]
    story += [table([("Section", "Title", "Page")] + toc, [0.8 * inch, 4.9 * inch, 0.9 * inch], align_right_from=2), PageBreak()]

    # ---- 1 Executive summary (3 pages)
    story += section("1. Executive Summary", f"Northgate Capital Advisors is pleased to present {PROPERTY['name']}, a {PROPERTY['units']}-unit, Class {PROPERTY['class']} garden-style apartment community located at {PROPERTY['address']}. Built in {PROPERTY['year_built']} on {PROPERTY['lot_acres']} acres, the Property comprises three {PROPERTY['stories']}-story residential buildings totalling approximately {PROPERTY['sf']:,} rentable square feet with {PROPERTY['parking']} surface parking spaces. The Property is offered at a guidance price of {money(PROPERTY['asking'])}, which represents {money(PROPERTY['asking'] / PROPERTY['units'])} per unit and a {pct(fig['cap'], 2)} capitalization rate on in-place net operating income of {money(fig['noi'])}.")
    story += [Paragraph("Offering summary", h2), table([
        ("Item", "Detail"), ("Property", PROPERTY["name"]), ("Address", PROPERTY["address"]), ("Property type", f"{PROPERTY['type']}, Class {PROPERTY['class']}, garden style"), ("Units", str(PROPERTY["units"])), ("Rentable square feet", f"{PROPERTY['sf']:,}"), ("Average unit size", f"{PROPERTY['sf'] / PROPERTY['units']:,.0f} sf"),
        ("Year built", str(PROPERTY["year_built"])), ("Site", f"{PROPERTY['lot_acres']} acres, {PROPERTY['stories']} stories, {PROPERTY['parking']} surface spaces"), ("Occupancy (physical, 30 Sep 2026)", "93.8% (45 of 48)"), ("Occupancy (economic, T-12)", "95.0%"),
        ("Guidance price", money(PROPERTY["asking"])), ("Price per unit", money(PROPERTY["asking"] / PROPERTY["units"])), ("Price per square foot", money(PROPERTY["asking"] / PROPERTY["sf"])), ("In-place NOI", money(fig["noi"])), ("In-place cap rate", pct(fig["cap"], 2)), ("Market-rent NOI (pro forma)", money(fig["market"] + fig["other"] - (fig["market"] + fig["other"]) * ASSUMPTIONS["vacancy"] - fig["opex"])),
    ], [2.6 * inch, 4.0 * inch], align_right_from=9)]
    story += [Paragraph("Income summary", h2), table([
        ("Line", "Annual", "Per unit"), ("Gross potential rent (in place)", money(fig["in_place"]), money(fig["in_place"] / 48)), ("Other income", money(fig["other"]), money(fig["other"] / 48)), ("Potential gross income", money(fig["pgi"]), money(fig["pgi"] / 48)),
        ("Vacancy and credit loss (5.0%)", f"({money(fig['vacancy'])})", f"({money(fig['vacancy'] / 48)})"), ("Effective gross income", money(fig["egi"]), money(fig["egi"] / 48)), ("Operating expenses", f"({money(fig['opex'])})", f"({money(fig['opex'] / 48)})"), ("Net operating income", money(fig["noi"]), money(fig["noi"] / 48)),
    ], [3.4 * inch, 1.6 * inch, 1.6 * inch]), PageBreak()]
    story += [Paragraph("The opportunity", h2)]
    story += [Paragraph(p, body) for p in (
        "Maple Street Apartments offers a buyer stabilized in-place cash flow with a clearly identified path to higher rents. Current rents trail the market by an average of 4.5 percent across the unit mix, a gap the Owner has deliberately preserved by renewing long-tenured residents below market during the 2024 and 2025 renewal cycles. The rent roll in Section 5 shows that 31 of the 45 occupied leases expire within the next twelve months, giving a new owner the opportunity to mark the majority of the roll to market within the first year of ownership.",
        "The Property has been owned by the same family partnership since 2009 and has been managed by a regional third-party manager since 2017. Capital investment over the hold has focused on building systems rather than interiors: roofs were replaced in 2018, the boilers and domestic hot water system in 2020, and the parking lot was resurfaced in 2023. Unit interiors remain largely original, with 11 units receiving a light refresh (paint, carpet, appliances) at turnover since 2022. The remaining 37 units present a conventional value-add program with a demonstrated premium at the comparable properties in Section 14.",
        "Springfield’s apartment submarket has absorbed new supply steadily over the past three years while maintaining vacancy below six percent, and the development pipeline detailed in Section 16 shows only one project of comparable quality within a two-mile radius scheduled for delivery before 2028. Employment growth has been led by the regional medical center and the two logistics parks on the east side of the city, both within a fifteen-minute drive of the Property.",
    )]
    market_noi = fig["market"] + fig["other"] - (fig["market"] + fig["other"]) * ASSUMPTIONS["vacancy"] - fig["opex"]
    story += [Paragraph("Pricing guidance", h2), Paragraph(f"The Owner’s guidance of {money(PROPERTY['asking'])} reflects a {pct(fig['cap'], 2)} capitalization rate on in-place net operating income and {pct(market_noi / PROPERTY['asking'], 2)} on pro forma net operating income at today’s market rents, before any renovation premium. The five closed sales presented in Section 15 traded between 6.20 and 6.90 percent on in-place income; the Owner’s guidance anticipates the mark-to-market and renovation upside described in Section 2, and purchasers should form their own view of how much of that upside to pay for. Offers will be evaluated on price, certainty of close, and timing; the offering process and timeline are detailed in Section 21.", body)]
    story += [Paragraph("Summary of underwriting assumptions provided by the Owner", h3), table([
        ("Assumption", "Owner’s pro forma"), ("Vacancy and credit loss", pct(ASSUMPTIONS["vacancy"])), ("Rent growth", f"{pct(ASSUMPTIONS['rent_growth'])} per year"), ("Expense growth", f"{pct(ASSUMPTIONS['expense_growth'])} per year"), ("Exit capitalization rate", pct(ASSUMPTIONS["exit_cap"], 2)), ("Hold period", f"{ASSUMPTIONS['hold']} years"), ("Replacement reserves", "$300 per unit per year"),
    ], [3.4 * inch, 3.2 * inch]), Paragraph("These are the Owner’s assumptions and are presented for reference only. Purchasers should apply their own.", small), PageBreak()]

    # ---- 2 Investment highlights (2 pages)
    story += section("2. Investment Highlights")
    highlights = [
        ("Proven in-place cash flow", f"Trailing twelve month net operating income of {money(fig['noi'])} on 95.0 percent economic occupancy, with collections averaging 99.1 percent of billed rent over the period."),
        ("Below-market rents across every floor plan", "Studios trail market by $75, one-bedrooms by $55, and two-bedrooms by $80 per month, an aggregate loss-to-lease of $40,800 per year before any interior renovation."),
        ("Near-term lease rollover", "31 of 45 occupied leases expire within twelve months of closing; the schedule in Section 6 is weighted toward the spring and summer leasing season."),
        ("Value-add interiors", "37 units retain original 1998 finishes. Comparable renovated units at Riverside Commons and Parkview Terrace command premiums of $140 to $185 per month for a scope of roughly $9,500 per unit."),
        ("Major systems addressed", "Roofs (2018), boilers and domestic hot water (2020), parking lot (2023), and exterior paint (2024) have been completed, leaving a new owner to focus capital on revenue-producing interior work."),
        ("Supply-constrained submarket", "One competing project of 96 units is scheduled for delivery within two miles before 2028, against trailing three-year absorption of roughly 310 units per year."),
        ("Assumable financing not required", "The Property is unencumbered; the Owner will deliver free and clear, and three indicative lender quotes are summarized in Section 17."),
        ("Walkable location", "Within 0.4 miles of the Maple Street retail corridor, 1.2 miles of Springfield Regional Medical Center, and 0.6 miles of the Route 9 bus rapid transit stop."),
    ]
    for title, text in highlights:
        story += [Paragraph(title, h3), Paragraph(text, body)]
    story += [PageBreak()]
    story += [Paragraph("Why now", h2)]
    story += [Paragraph(p, body) for p in (
        "Three dynamics make the next twenty-four months the right window for a repositioning of Maple Street. First, the rollover schedule concentrates expirations in the leasing season, so renewals and new leases can be marked to market without a prolonged period of elevated vacancy. Second, the construction cost environment has moderated: the Owner’s property manager has obtained unit renovation bids at $9,200 to $9,800 per unit, roughly eight percent below quotes received in 2024. Third, the submarket’s delivery pipeline thins after the one project under construction, so new leases signed in 2027 and 2028 will face limited competition from first-generation space.",
        "Taken together, the Owner’s pro forma projects a stabilized net operating income at market rents and a modest renovation premium of approximately $610,000 by the end of year three, against the in-place figure of roughly $459,000 today. Purchasers should underwrite their own renovation scope, timing, and rent premium; the rent comparable detail in Section 14 is provided to support that work.",
    )]
    story += [PageBreak()]

    # ---- 3 Property description (4 pages)
    story += section("3. Property Description")
    story += [Paragraph("Site and improvements", h2), table([
        ("Attribute", "Detail"), ("Parcel", "Springfield County APN 118-220-014"), ("Site area", "2.10 acres (91,476 sf)"), ("Density", "22.9 units per acre"), ("Buildings", "Three 3-story garden-style residential buildings (A, B, C)"), ("Construction", "Wood frame over slab on grade; brick veneer and fiber-cement siding"), ("Roofs", "Pitched, architectural asphalt shingle, replaced 2018"),
        ("Windows", "Double-pane vinyl, original 1998"), ("HVAC", "Individual through-wall heat pumps per unit (2016 to 2022 replacements on 29 units)"), ("Heating and hot water", "Central gas boilers (2020) with domestic hot water loop"), ("Electrical", "Individually metered, 100-amp panels per unit"), ("Plumbing", "Copper supply, PVC waste; water heaters central"), ("Fire and life safety", "Hard-wired smoke detectors; fire extinguishers in corridors; no sprinklers (not required at construction)"),
        ("Parking", "72 surface spaces (1.5 per unit), 48 reserved, resurfaced and restriped 2023"), ("Laundry", "Two common laundry rooms (Buildings A and C), third-party route operator"), ("Amenities", "Leasing office, fenced dog run, picnic and grilling area, playground, package room"), ("Access", "Two curb cuts on Maple Street; secured building entries with key fob"), ("Utilities", "Water and sewer by municipal provider; electricity by residents; gas (heat and hot water) by Owner"),
    ], [2.0 * inch, 4.6 * inch], align_right_from=9)]
    story += [PageBreak(), Paragraph("Building summary", h2), table([
        ("Building", "Stories", "Units", "Studio", "1 bed", "2 bed", "Rentable sf", "Year built", "Roof", "Elevator"),
        ("A", 3, 16, 3, 8, 5, "13,980", 1998, "2018", "No"), ("B", 3, 16, 2, 8, 6, "14,160", 1998, "2018", "No"), ("C", 3, 16, 3, 8, 5, "13,860", 1998, "2018", "No"), ("Total", "", 48, 8, 24, 16, "42,000", "", "", ""),
    ], [0.7 * inch, 0.6 * inch, 0.5 * inch, 0.6 * inch, 0.55 * inch, 0.55 * inch, 0.9 * inch, 0.8 * inch, 0.6 * inch, 0.7 * inch])]
    story += [Paragraph("Location", h2)]
    story += [Paragraph(p, body) for p in (
        "Maple Street Apartments occupies a corner site at the intersection of Maple Street and Third Avenue in the Northside neighborhood of Springfield. The immediate surroundings are a mix of single-family homes built between 1950 and 1975, two-story garden apartment communities of similar vintage to the Property, and a four-block neighborhood retail corridor along Maple Street anchored by a regional grocery store, a pharmacy, two banks, and roughly thirty small retailers and restaurants.",
        "Springfield Regional Medical Center, the county’s largest employer with approximately 4,100 staff, is 1.2 miles south. The Eastgate and Riverside logistics parks, which together added roughly 2,300 jobs between 2022 and 2025, are nine and twelve minutes by car. Downtown Springfield is 2.4 miles south along Route 9, served by the bus rapid transit line with a stop 0.6 miles from the Property. Interstate access is 3.1 miles east.",
        "Springfield Public Schools serves the site; the assigned elementary school (Northside Elementary, 0.5 miles) and middle school (Cedar Middle, 1.4 miles) are both rated above the district average. Maple Street Park, with ball fields, a splash pad, and a community center, is directly across Third Avenue.",
    )]
    story += [PageBreak(), Paragraph("Site plan narrative", h2)]
    story += [Paragraph(p, body) for p in (
        "The three residential buildings are arranged in a U around a central landscaped courtyard that contains the dog run, grilling area, and playground. Parking surrounds the buildings on three sides with the primary entrance from Maple Street leading to the leasing office in Building A. A secondary drive on Third Avenue provides access to the rear parking field and the trash enclosure. The site drains to a detention basin in the northeast corner that was cleaned and regraded in 2023.",
        "Landscaping consists of mature shade trees along the street frontages, foundation plantings, and lawn, maintained under a contract that includes irrigation of the courtyard and entries. Exterior lighting was converted to LED fixtures in 2021. Signage consists of a monument sign at the Maple Street entrance and building identification lettering.",
    )]
    story += [Paragraph("Interior finishes", h2), table([
        ("Element", "Original (37 units)", "Refreshed (11 units, 2022 to 2026)"), ("Flooring", "Carpet in living and bedrooms; sheet vinyl in kitchen and bath", "Luxury vinyl plank throughout"), ("Kitchen", "Laminate counters, oak cabinets, white appliances", "Laminate counters, painted cabinets with new hardware, stainless appliances"), ("Bath", "Tub and shower surround, cultured marble vanity", "Resurfaced tub, new vanity and fixtures"), ("Lighting", "Surface-mount fixtures", "LED fixtures, ceiling fans in bedrooms"), ("Laundry", "Hookups in 2-bed units only", "Hookups in 2-bed units only"), ("Window coverings", "Mini blinds", "Faux-wood blinds"),
    ], [1.3 * inch, 2.65 * inch, 2.65 * inch], align_right_from=9), PageBreak()]

    # ---- 4 Unit mix and floor plans (2 pages)
    story += section("4. Unit Mix and Floor Plans")
    story += [table([("Unit type", "Units", "Share", "Avg sf", "In-place rent", "In-place $/sf", "Market rent", "Market $/sf", "Loss to lease")] + [
        (name, units, pct(units / 48), sf, money(rent), f"${rent / sf:.2f}", money(market), f"${market / sf:.2f}", money((market - rent) * units * 12)) for name, units, sf, rent, market in RENT_ROLL
    ] + [("Total / weighted", 48, "100.0%", 875, money(fig["in_place"] / 48 / 12), f"${fig['in_place'] / 12 / 42000:.2f}", money(fig["market"] / 48 / 12), f"${fig['market'] / 12 / 42000:.2f}", money(fig["market"] - fig["in_place"]))], [1.15 * inch, 0.5 * inch, 0.6 * inch, 0.55 * inch, 0.85 * inch, 0.75 * inch, 0.8 * inch, 0.75 * inch, 0.85 * inch])]
    for name, units, sf, rent, market in RENT_ROLL:
        story += [Paragraph(f"{name} · {units} units · {sf} sf", h2), Paragraph({
            "Studio": "Open plan with a galley kitchen along the entry wall, a sleeping alcove with closet, and a full bath. Studios are located on the ground floor of each building with patio access. Window exposure is single-aspect.",
            "1 bed / 1 bath": "Entry into a living and dining area with an open kitchen, a bedroom with a walk-in closet, a full bath off the hall, and a patio or balcony. The one-bedroom plan is the most common in the submarket and the Property’s plan is within 20 square feet of the comparable average.",
            "2 bed / 2 bath": "Split-bedroom plan with the primary suite and bath on one side of the living area and the second bedroom and hall bath on the other. Includes a laundry closet with washer and dryer hookups and a balcony. The two-bedroom plan is the largest among the rent comparables and supports the largest renovation premium.",
        }[name], body), table([("Room", "Dimensions", "Notes")] + {
            "Studio": [("Living / sleeping", "15 ft 6 in x 18 ft", "Alcove 9 ft x 8 ft"), ("Kitchen", "8 ft x 7 ft", "Galley"), ("Bath", "7 ft x 5 ft", "Tub and shower"), ("Patio", "8 ft x 6 ft", "Ground floor")],
            "1 bed / 1 bath": [("Living / dining", "16 ft x 13 ft", ""), ("Kitchen", "10 ft x 8 ft", "Open to living"), ("Bedroom", "13 ft x 12 ft", "Walk-in closet"), ("Bath", "8 ft x 5 ft", ""), ("Balcony or patio", "9 ft x 6 ft", "")],
            "2 bed / 2 bath": [("Living / dining", "18 ft x 14 ft", ""), ("Kitchen", "11 ft x 9 ft", "Breakfast bar"), ("Primary bedroom", "14 ft x 12 ft", "En-suite bath, walk-in closet"), ("Second bedroom", "12 ft x 11 ft", ""), ("Second bath", "8 ft x 5 ft", "Hall access"), ("Laundry closet", "5 ft x 3 ft", "Hookups"), ("Balcony", "10 ft x 6 ft", "")],
        }[name], [2.0 * inch, 1.8 * inch, 2.8 * inch], align_right_from=9)]
    story += [PageBreak()]

    # ---- 5 Rent roll (unit by unit, ~4 pages)
    roll = unit_rent_roll()
    story += section("5. Rent Roll", "Rent roll as of 30 September 2026, as reported by the Owner’s property manager. Market rents reflect the manager’s current asking rents for each floor plan. Three units were vacant on the as-of date and are shown with no lease.")
    rows = [("Unit", "Type", "Sf", "Status", "Lease start", "Lease end", "Current rent", "Market rent", "Variance")]
    for number, name, sf, rent, market, start, end in roll:
        status = "Occupied" if rent else "Vacant"
        rows.append((number, name, sf, status, start or "", end or "", money(rent) if rent else "", money(market), money(market - rent) if rent else ""))
    occupied = [r for r in roll if r[3]]
    rows.append(("Total", f"{len(occupied)} occupied", "", "", "", "", money(sum(r[3] for r in roll)), money(sum(r[4] for r in roll)), ""))
    story += [table(rows, [0.6 * inch, 0.95 * inch, 0.45 * inch, 0.7 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.8 * inch, 0.65 * inch], align_right_from=6, font_size=7.8)]
    story += [Paragraph(f"Scheduled monthly rent on occupied units totals {money(sum(r[3] for r in roll))}; annualized with the three vacant units at the in-place average for their floor plan, gross potential rent is {money(fig['in_place'])}, which is the figure carried in the operating statements. Market rent on the full roll annualizes to {money(fig['market'])}.", body), PageBreak()]

    # ---- 6 Lease expirations
    story += section("6. Lease Expiration Schedule")
    by_month: dict[str, int] = {}
    for r in occupied:
        key = r[6][:7]
        by_month[key] = by_month.get(key, 0) + 1
    exp_rows = [("Month", "Expiring leases", "Share of occupied", "Cumulative")]
    cumulative = 0
    for key in sorted(by_month):
        cumulative += by_month[key]
        exp_rows.append((key, by_month[key], pct(by_month[key] / len(occupied)), pct(cumulative / len(occupied))))
    story += [table(exp_rows, [1.6 * inch, 1.6 * inch, 1.7 * inch, 1.7 * inch])]
    story += [Paragraph("Renewal history", h2), table([("Period", "Expirations", "Renewed", "Renewal rate", "Average renewal increase", "Average new-lease increase"), ("Q4 2024", 11, 8, "72.7%", "2.4%", "5.1%"), ("Q1 2025", 9, 7, "77.8%", "2.1%", "4.6%"), ("Q2 2025", 14, 10, "71.4%", "2.8%", "5.9%"), ("Q3 2025", 12, 9, "75.0%", "2.6%", "5.4%"), ("Q4 2025", 10, 8, "80.0%", "2.2%", "4.2%"), ("Q1 2026", 8, 6, "75.0%", "2.0%", "4.8%"), ("Q2 2026", 13, 10, "76.9%", "2.9%", "6.2%"), ("Q3 2026", 11, 8, "72.7%", "2.7%", "5.7%")], [0.9 * inch, 0.9 * inch, 0.8 * inch, 1.0 * inch, 1.5 * inch, 1.5 * inch]), Paragraph("The Owner has limited renewal increases to roughly three percent since 2024 in order to retain long-tenured residents; new leases have been signed at or near market. The spread between the two columns is the loss-to-lease a new owner can address at rollover.", body), PageBreak()]

    # ---- 7 Historical operating statements (3 pages)
    story += section("7. Historical Operating Statements", "Unaudited statements as reported by the property manager. 2024 and 2025 are calendar years; T-12 is the twelve months ended 30 September 2026; Budget 2027 is the Owner’s budget and is presented for reference only.")
    def hist(t12: float, g24: float, g25: float, g27: float):
        return (money(t12 * g24), money(t12 * g25), money(t12), money(t12 * g27))
    inc_rows = [("Income", "2024", "2025", "T-12 Sep 2026", "Budget 2027")]
    inc_rows.append(("Gross potential rent",) + hist(fig["in_place"], 0.905, 0.951, 1.038))
    inc_rows.append(("Vacancy",) + tuple(f"({x})" for x in hist(fig["in_place"] * 0.05, 1.18, 1.06, 0.96)))
    inc_rows.append(("Concessions",) + tuple(f"({x})" for x in hist(6_200, 1.4, 1.1, 0.8)))
    inc_rows.append(("Bad debt",) + tuple(f"({x})" for x in hist(7_900, 1.2, 1.05, 0.9)))
    inc_rows.append(("Net rental income",) + hist(fig["in_place"] * 0.95 - 14_100, 0.90, 0.95, 1.04))
    for name, amount, _ in OTHER_INCOME:
        inc_rows.append((name,) + hist(amount, 0.92, 0.96, 1.03))
    inc_rows.append(("Effective gross income",) + hist(fig["egi"] - 14_100, 0.90, 0.95, 1.04))
    story += [table(inc_rows, [2.3 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch])]
    story += [Paragraph("Note: concessions and bad debt are netted within the five percent vacancy and credit loss allowance in the pro forma income summary; the T-12 statement above shows them separately as recorded.", small)]
    exp_rows = [("Expenses", "2024", "2025", "T-12 Sep 2026", "Budget 2027")]
    growth = {"Real estate taxes": (0.93, 0.97, 1.03), "Insurance": (0.78, 0.89, 1.08), "Utilities": (0.91, 0.96, 1.03), "Repairs and maintenance": (1.08, 1.02, 0.97), "Contract services": (0.95, 0.98, 1.03), "Payroll": (0.92, 0.96, 1.035), "Management fee": (0.90, 0.95, 1.04), "General and administrative": (0.97, 0.99, 1.02), "Marketing": (1.15, 1.05, 0.95), "Replacement reserves": (1.0, 1.0, 1.0)}
    for name, amount, _ in EXPENSES:
        exp_rows.append((name,) + hist(amount, *growth[name]))
    exp_rows.append(("Total operating expenses", money(sum(a * growth[n][0] for n, a, _ in EXPENSES)), money(sum(a * growth[n][1] for n, a, _ in EXPENSES)), money(fig["opex"]), money(sum(a * growth[n][2] for n, a, _ in EXPENSES))))
    exp_rows.append(("Expenses per unit", money(sum(a * growth[n][0] for n, a, _ in EXPENSES) / 48), money(sum(a * growth[n][1] for n, a, _ in EXPENSES) / 48), money(fig["opex"] / 48), money(sum(a * growth[n][2] for n, a, _ in EXPENSES) / 48)))
    story += [PageBreak(), table(exp_rows, [2.3 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch])]
    story += [Paragraph("Net operating income", h2), table([("", "2024", "2025", "T-12 Sep 2026", "Budget 2027"), ("Effective gross income",) + hist(fig["egi"] - 14_100, 0.90, 0.95, 1.04), ("Operating expenses", money(sum(a * growth[n][0] for n, a, _ in EXPENSES)), money(sum(a * growth[n][1] for n, a, _ in EXPENSES)), money(fig["opex"]), money(sum(a * growth[n][2] for n, a, _ in EXPENSES))), ("Net operating income (as recorded)", money((fig["egi"] - 14_100) * 0.90 - sum(a * growth[n][0] for n, a, _ in EXPENSES)), money((fig["egi"] - 14_100) * 0.95 - sum(a * growth[n][1] for n, a, _ in EXPENSES)), money(fig["egi"] - 14_100 - fig["opex"]), money((fig["egi"] - 14_100) * 1.04 - sum(a * growth[n][2] for n, a, _ in EXPENSES))), ("Expense ratio", "", "", pct(fig["opex"] / (fig["egi"] - 14_100)), "")], [2.3 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch])]
    story += [Paragraph("Reconciliation to the pro forma", h2), Paragraph(f"The underwriting pro forma in Section 1 applies a single five percent vacancy and credit loss allowance to potential gross income of {money(fig['pgi'])} in place of the separately recorded vacancy, concessions, and bad debt, and holds operating expenses at the trailing twelve month total of {money(fig['opex'])}. The resulting net operating income of {money(fig['noi'])} is the figure on which the guidance price capitalization rate is quoted. Purchasers who prefer to carry concessions and bad debt separately should adjust accordingly.", body), PageBreak()]

    # ---- 8 T-12 monthly detail (4 pages)
    story += section("8. Trailing Twelve Month Detail", "Monthly general ledger summary for the twelve months ended 30 September 2026. Columns are months; the final column is the trailing total that ties to Section 7.")
    def month_table(title, lines):
        header = ("Account",) + SHORT_MONTHS + ("T-12",)
        rows = [header]
        totals = [0] * 12
        for name, values in lines:
            rows.append((name,) + tuple(f"{v:,.0f}" for v in values) + (f"{sum(values):,.0f}",))
            totals = [a + b for a, b in zip(totals, values)]
        rows.append(("Total",) + tuple(f"{v:,.0f}" for v in totals) + (f"{sum(totals):,.0f}",))
        widths = [1.35 * inch] + [0.395 * inch] * 12 + [0.6 * inch]
        return [Paragraph(title, h2), table(rows, widths, font_size=6.6)]
    gpr = split_months(int(fig["in_place"]), FLAT)
    vac = split_months(int(fig["in_place"] * 0.05), (1.2, 1.3, 1.4, 1.3, 1.1, 0.9, 0.8, 0.7, 0.7, 0.8, 0.9, 0.9))
    story += month_table("Rental income", [("Gross potential rent", gpr), ("Vacancy loss", [-v for v in vac]), ("Concessions", [-v for v in split_months(6_200, MARKETING_PROFILE)]), ("Bad debt", [-v for v in split_months(7_900, (1.0, 1.1, 1.3, 1.2, 1.0, 0.9, 0.8, 0.9, 1.0, 1.0, 0.9, 0.9))])])
    story += month_table("Other income", [(name, split_months(amount, FLAT if name == "Parking" else MARKETING_PROFILE if name != "Laundry" else UTILITY_PROFILE)) for name, amount, _ in OTHER_INCOME])
    story += [PageBreak()]
    profiles = {"Real estate taxes": FLAT, "Insurance": FLAT, "Utilities": UTILITY_PROFILE, "Repairs and maintenance": REPAIR_PROFILE, "Contract services": (1.1, 1.0, 1.1, 1.2, 1.1, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0, 1.0), "Payroll": FLAT, "Management fee": FLAT, "General and administrative": FLAT, "Marketing": MARKETING_PROFILE, "Replacement reserves": FLAT}
    story += month_table("Operating expenses", [(name, split_months(amount, profiles[name])) for name, amount, _ in EXPENSES])
    story += [Paragraph("Sub-account detail: repairs and maintenance", h2)]
    rm = split_months(48_000, REPAIR_PROFILE)
    sub = [("Turnover (paint, clean, carpet)", 0.34), ("Plumbing", 0.14), ("Electrical", 0.07), ("HVAC service", 0.16), ("Appliances", 0.09), ("Grounds and exterior", 0.11), ("Supplies", 0.09)]
    sub_rows = [("Sub-account",) + SHORT_MONTHS + ("T-12",)]
    running = [0] * 12
    for i, (name, share) in enumerate(sub):
        if i < len(sub) - 1:
            vals = [round(m * share) for m in rm]
        else:
            vals = [m - r for m, r in zip(rm, running)]
        running = [a + b for a, b in zip(running, vals)]
        sub_rows.append((name,) + tuple(f"{v:,.0f}" for v in vals) + (f"{sum(vals):,.0f}",))
    sub_rows.append(("Total",) + tuple(f"{v:,.0f}" for v in rm) + (f"{sum(rm):,.0f}",))
    story += [table(sub_rows, [1.35 * inch] + [0.395 * inch] * 12 + [0.6 * inch], font_size=6.6), PageBreak()]
    story += [Paragraph("Sub-account detail: utilities", h2)]
    ut = split_months(52_000, UTILITY_PROFILE)
    usub = [("Gas (heat and hot water)", 0.52), ("Water and sewer (common and vacant)", 0.27), ("Electricity (common areas)", 0.15), ("Trash (see contract services)", 0.0), ("Telephone and internet (office)", 0.06)]
    u_rows = [("Sub-account",) + SHORT_MONTHS + ("T-12",)]
    running = [0] * 12
    for i, (name, share) in enumerate(usub):
        vals = [round(m * share) for m in ut] if i < len(usub) - 1 else [m - r for m, r in zip(ut, running)]
        running = [a + b for a, b in zip(running, vals)]
        u_rows.append((name,) + tuple(f"{v:,.0f}" for v in vals) + (f"{sum(vals):,.0f}",))
    u_rows.append(("Total",) + tuple(f"{v:,.0f}" for v in ut) + (f"{sum(ut):,.0f}",))
    story += [table(u_rows, [1.35 * inch] + [0.395 * inch] * 12 + [0.6 * inch], font_size=6.6)]
    story += [Paragraph("Occupancy and collections by month", h2)]
    occ_rows = [("Month", "Units occupied", "Physical occupancy", "Billed rent", "Collected", "Collection rate", "Move-ins", "Move-outs")]
    occ = (45, 45, 44, 44, 45, 46, 46, 47, 46, 46, 45, 45)
    for i, m in enumerate(MONTHS):
        billed = gpr[i] - vac[i]
        occ_rows.append((m, occ[i], pct(occ[i] / 48), money(billed), money(billed * 0.991), "99.1%", (2, 1, 1, 2, 3, 3, 2, 3, 1, 2, 1, 2)[i], (2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2)[i]))
    story += [table(occ_rows, [0.85 * inch, 0.8 * inch, 0.9 * inch, 0.9 * inch, 0.9 * inch, 0.8 * inch, 0.7 * inch, 0.75 * inch]), PageBreak()]

    # ---- 9 Expense analysis (3 pages)
    story += section("9. Expense Analysis", "Trailing twelve month expenses compared with the Owner’s budget and with a survey of twelve comparable garden-style communities in the Springfield metropolitan area managed by three regional operators (the “Peer Set”).")
    peer = {"Real estate taxes": 2_300, "Insurance": 760, "Utilities": 1_150, "Repairs and maintenance": 1_050, "Contract services": 410, "Payroll": 1_560, "Management fee": 640, "General and administrative": 270, "Marketing": 150, "Replacement reserves": 300}
    pe_rows = [("Category", "T-12", "Per unit", "Per sf", "Peer Set per unit", "Variance", "Comment")]
    for name, amount, note in EXPENSES:
        pe_rows.append((name, money(amount), money(amount / 48), f"${amount / 42000:.2f}", money(peer[name]), money(amount / 48 - peer[name]), note))
    pe_rows.append(("Total", money(fig["opex"]), money(fig["opex"] / 48), f"${fig['opex'] / 42000:.2f}", money(sum(peer.values())), money(fig["opex"] / 48 - sum(peer.values())), ""))
    story += [table(pe_rows, [1.45 * inch, 0.75 * inch, 0.65 * inch, 0.55 * inch, 0.8 * inch, 0.7 * inch, 1.7 * inch], font_size=7.6)]
    story += [Paragraph("Commentary", h2)]
    story += [Paragraph(p, body) for p in (
        "Real estate taxes. The Property is assessed at $6,140,000 for the 2026 tax year under the county’s six-year reassessment cycle. The current effective rate is 1.92 percent of assessed value. The county reassesses upon transfer at or near the recorded consideration; at the guidance price, taxes would rise to approximately $163,000, an increase of roughly $45,000 over the trailing figure. This is the single most important expense adjustment a purchaser should make and is not reflected in the Owner’s pro forma.",
        "Insurance. The property policy renewed in June 2026 at $34,000, a 12 percent increase over the prior term, reflecting market-wide premium growth. Coverage is a $9.5 million replacement-cost policy with a $25,000 deductible and $2 million of general liability. Quotes obtained by the manager for a comparable policy under new ownership ranged from $33,500 to $38,000.",
        "Utilities. The Owner pays gas for central heat and domestic hot water and water and sewer for common areas and vacant units; residents pay their own electricity. There is no utility reimbursement program in place. The Peer Set average reflects properties with ratio utility billing; implementation at Maple Street could recover an estimated $28,000 to $36,000 per year at a 70 percent recovery rate, subject to local regulation and lease terms.",
        "Payroll. One full-time community manager, one full-time maintenance technician, and a part-time leasing associate during the leasing season. Payroll includes benefits and payroll taxes at 24 percent of wages and is in line with the Peer Set for a 48-unit community without on-site maintenance supervision.",
        "Management fee. The current third-party management agreement provides for a fee of three percent of effective gross income with a $2,500 monthly minimum and may be terminated on 30 days’ notice upon sale. Purchasers self-managing or engaging a different operator should substitute their own fee.",
        "Replacement reserves. Reserves of $300 per unit per year are carried in the operating statement at the Owner’s practice. Lenders quoted in Section 17 indicated $250 to $300 per unit per year.",
    )]
    story += [PageBreak(), Paragraph("Five-year expense history", h2)]
    five = [("Year", "Taxes", "Insurance", "Utilities", "R&M", "Contract", "Payroll", "Mgmt", "G&A", "Marketing", "Reserves", "Total", "Per unit")]
    history = {2022: (0.86, 0.62, 0.84, 1.02, 0.90, 0.86, 0.85, 0.94, 1.10, 1.0), 2023: (0.90, 0.70, 0.88, 1.06, 0.92, 0.89, 0.88, 0.96, 1.20, 1.0), 2024: (0.93, 0.78, 0.91, 1.08, 0.95, 0.92, 0.90, 0.97, 1.15, 1.0), 2025: (0.97, 0.89, 0.96, 1.02, 0.98, 0.96, 0.95, 0.99, 1.05, 1.0)}
    for year, factors in history.items():
        vals = [a * f for (n, a, _), f in zip(EXPENSES, factors)]
        five.append((str(year),) + tuple(f"{v:,.0f}" for v in vals) + (f"{sum(vals):,.0f}", f"{sum(vals) / 48:,.0f}"))
    vals = [a for _, a, _ in EXPENSES]
    five.append(("T-12",) + tuple(f"{v:,.0f}" for v in vals) + (f"{sum(vals):,.0f}", f"{sum(vals) / 48:,.0f}"))
    story += [table(five, [0.5 * inch] + [0.52 * inch] * 10 + [0.6 * inch, 0.55 * inch], font_size=6.6)]
    story += [Paragraph("Expenses have grown at a compound rate of roughly 4.1 percent per year since 2022, driven by insurance (14 percent per year) and taxes (3.1 percent per year). Controllable expenses excluding taxes and insurance have grown at 2.6 percent per year, which is the basis for the Owner’s 2.5 percent expense growth assumption.", body), PageBreak()]

    # ---- 10 Capital improvements (2 pages)
    story += section("10. Capital Improvements")
    story += [Paragraph("Completed since 2017", h2), table([("Year", "Project", "Scope", "Cost")] + [
        ("2017", "Management transition", "Lease audit, new leases, software conversion", "$18,500"), ("2018", "Roof replacement", "All three buildings, architectural shingle, 30-year warranty", "$286,000"), ("2019", "Exterior lighting", "Pole and wall-pack conversion to LED", "$22,400"),
        ("2020", "Boilers and hot water", "Two condensing boilers, storage tanks, recirculation pumps", "$148,000"), ("2021", "Leasing office refresh", "Flooring, paint, furniture, signage", "$14,200"), ("2022", "Unit refresh program begins", "4 units: paint, LVP, appliances", "$26,800"),
        ("2023", "Parking lot", "Mill and overlay, restripe, new wheel stops", "$94,000"), ("2023", "Detention basin", "Clean out and regrade", "$11,600"), ("2024", "Exterior paint and sealant", "All buildings, trim, railings", "$71,000"), ("2024", "Unit refresh program", "4 units", "$28,400"),
        ("2025", "HVAC replacements", "9 through-wall heat pumps", "$31,500"), ("2025", "Unit refresh program", "3 units", "$22,200"), ("2026", "Laundry room", "Flooring, lighting, new route equipment (operator funded)", "$4,800"), ("", "Total since 2017", "", "$779,400"),
    ], [0.6 * inch, 1.7 * inch, 3.3 * inch, 1.0 * inch], align_right_from=3)]
    story += [PageBreak(), Paragraph("Owner’s recommended capital plan (for reference)", h2), table([("Item", "Timing", "Scope", "Estimate", "Per unit")] + [
        ("Interior renovations", "Years 1 to 3", "37 units: LVP, cabinets, counters, stainless appliances, lighting, bath", "$355,000", "$9,595"), ("Washer and dryer installation", "Years 1 to 3", "16 two-bedroom units", "$38,400", "$2,400"), ("Ratio utility billing", "Year 1", "Submeter study, lease addenda, software", "$12,000", "$250"),
        ("Fitness room", "Year 1", "Convert storage in Building B", "$42,000", "$875"), ("Package lockers", "Year 1", "Leasing office vestibule", "$18,500", "$385"), ("Window replacement (deferred)", "Years 4 to 5", "All units, double-pane vinyl", "$212,000", "$4,417"), ("Water heater loop", "Year 5", "Recirculation pump and controls", "$9,500", "$198"), ("Total", "", "", "$687,400", "$14,321"),
    ], [1.6 * inch, 0.9 * inch, 2.8 * inch, 0.75 * inch, 0.65 * inch], align_right_from=3)]
    story += [Paragraph("Physical condition items identified in the Owner’s 2025 property condition review are summarized in Section 19. The capital plan above is the Owner’s view of a value-add program and is not an engineering estimate.", body), PageBreak()]

    # ---- 11 Regional economy (3 pages)
    story += section("11. Regional Economy")
    story += [Paragraph(p, body) for p in (
        "The Springfield metropolitan area has a population of approximately 412,000 and a labor force of 214,000. Employment has grown at an average of 1.6 percent per year over the past five years, ahead of the national average, led by healthcare, logistics and distribution, and advanced manufacturing. The unemployment rate was 3.7 percent in August 2026 against a national rate of 4.1 percent.",
        "Healthcare is the largest sector, anchored by Springfield Regional Medical Center and its 2024 expansion, which added a 120-bed tower and roughly 600 positions. Logistics employment has grown fastest, with the Eastgate and Riverside parks adding approximately 2,300 jobs since 2022 as regional distribution centers for three national retailers. Manufacturing is concentrated in precision components and food processing, with the two largest plants each employing more than 1,000.",
        "The metropolitan area’s median household income is $68,400, and the median home price is $318,000, which places the monthly cost of ownership roughly $640 above the average two-bedroom apartment rent in the submarket. The gap has widened by $190 per month since 2023 and supports continued rental demand from households that would historically have purchased.",
    )]
    story += [Paragraph("Major employers", h2), table([("Employer", "Sector", "Employees", "Distance from Property", "Recent change")] + [
        ("Springfield Regional Medical Center", "Healthcare", "4,100", "1.2 miles", "+600 (2024 tower)"), ("Springfield Public Schools", "Education", "3,250", "Various", "Stable"), ("County of Springfield", "Government", "2,640", "2.6 miles", "Stable"), ("Eastgate Distribution Center", "Logistics", "1,850", "6.1 miles", "+1,100 since 2022"),
        ("Meridian Precision Components", "Manufacturing", "1,420", "4.8 miles", "+180 (2025 line)"), ("Riverside Logistics Park (3 tenants)", "Logistics", "1,310", "7.4 miles", "+1,200 since 2023"), ("Springfield State University", "Education", "1,180", "3.3 miles", "Stable"), ("Northfield Foods", "Manufacturing", "1,050", "5.2 miles", "Stable"), ("First Springfield Bank", "Finance", "740", "2.4 miles", "+60"), ("Cedar Valley Health System", "Healthcare", "690", "3.9 miles", "+120 (2026)"),
    ], [2.2 * inch, 1.1 * inch, 0.9 * inch, 1.3 * inch, 1.3 * inch], align_right_from=2), PageBreak()]
    story += [Paragraph("Employment by sector", h2), table([("Sector", "2021", "2026", "Change", "Share 2026", "5-year growth")] + [
        ("Healthcare and social assistance", "38,900", "44,200", "+5,300", "20.7%", "13.6%"), ("Retail trade", "24,100", "24,600", "+500", "11.5%", "2.1%"), ("Transportation and warehousing", "14,200", "19,800", "+5,600", "9.3%", "39.4%"), ("Manufacturing", "21,800", "23,100", "+1,300", "10.8%", "6.0%"), ("Education", "19,400", "20,100", "+700", "9.4%", "3.6%"),
        ("Government", "17,900", "18,300", "+400", "8.6%", "2.2%"), ("Accommodation and food services", "16,200", "17,400", "+1,200", "8.1%", "7.4%"), ("Professional and business services", "15,800", "17,900", "+2,100", "8.4%", "13.3%"), ("Construction", "9,600", "10,900", "+1,300", "5.1%", "13.5%"), ("Finance and insurance", "7,400", "7,700", "+300", "3.6%", "4.1%"), ("Other", "9,100", "9,600", "+500", "4.5%", "5.5%"), ("Total nonfarm", "194,400", "213,600", "+19,200", "100.0%", "9.9%"),
    ], [2.3 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.9 * inch])]
    story += [Paragraph("Population and households", h2), table([("Measure", "2016", "2021", "2026", "2031 (projected)"), ("Metropolitan population", "381,200", "396,800", "412,400", "428,900"), ("Households", "148,600", "156,100", "163,900", "171,200"), ("Renter households", "52,300", "57,400", "62,600", "66,800"), ("Renter share", "35.2%", "36.8%", "38.2%", "39.0%"), ("Median household income", "$56,100", "$61,800", "$68,400", "$75,900"), ("Median age", "36.1", "36.8", "37.4", "37.9")], [2.4 * inch, 1.05 * inch, 1.05 * inch, 1.05 * inch, 1.1 * inch]), PageBreak()]
    story += [Paragraph("Infrastructure and development", h2)]
    story += [Paragraph(p, body) for p in (
        "The Route 9 bus rapid transit line opened in 2023 and connects the Northside neighborhood to downtown and the medical center with ten-minute peak headways; the Maple Street station is 0.6 miles from the Property. The state transportation department has funded the widening of the Route 9 corridor north of the Property, with construction scheduled for 2027 to 2029.",
        "Downtown Springfield has seen roughly $240 million of mixed-use investment since 2021, including a 210-unit apartment building, a renovated performing arts center, and the conversion of two office buildings to residential use. The city’s 2025 comprehensive plan designates the Maple Street corridor as a neighborhood center and permits residential densities up to 30 units per acre by right.",
        "The regional airport added nonstop service to two additional hub cities in 2025. A 1.4 million square foot intermodal facility is planned adjacent to the Eastgate park with a 2028 opening, expected to add an estimated 900 logistics jobs.",
    )]
    story += [PageBreak()]

    # ---- 12 Demographics (2 pages)
    story += section("12. Demographics", "Estimates for radii measured from the Property. Figures are from a third-party demographic data provider and are presented as reported.")
    demo_rows = [("Measure", "1 mile", "3 miles", "5 miles")] + [
        ("Population 2026", "11,840", "68,900", "154,300"), ("Population 2031 (projected)", "12,310", "71,600", "160,400"), ("Households 2026", "4,960", "27,400", "61,200"), ("Average household size", "2.34", "2.46", "2.49"), ("Renter-occupied households", "2,640", "12,100", "24,900"), ("Renter share", "53.2%", "44.2%", "40.7%"),
        ("Median household income", "$52,300", "$61,700", "$66,900"), ("Average household income", "$64,800", "$78,200", "$84,600"), ("Households earning $50k to $100k", "36.4%", "35.1%", "34.8%"), ("Median age", "33.6", "35.2", "36.4"), ("Bachelor’s degree or higher", "27.8%", "31.4%", "33.9%"), ("Median home value", "$241,000", "$287,000", "$318,000"), ("Daytime population", "14,600", "82,300", "171,900"),
    ]
    story += [table(demo_rows, [2.8 * inch, 1.25 * inch, 1.25 * inch, 1.25 * inch])]
    story += [Paragraph("Renter profile within one mile", h2), table([("Household income band", "Renter households", "Share", "Affordable rent at 30%"), ("Under $25,000", "520", "19.7%", "Under $625"), ("$25,000 to $50,000", "740", "28.0%", "$625 to $1,250"), ("$50,000 to $75,000", "690", "26.1%", "$1,250 to $1,875"), ("$75,000 to $100,000", "410", "15.5%", "$1,875 to $2,500"), ("Over $100,000", "280", "10.6%", "Over $2,500"), ("Total", "2,640", "100.0%", "")], [2.0 * inch, 1.5 * inch, 1.3 * inch, 1.8 * inch]), Paragraph("Roughly 52 percent of renter households within one mile can afford the Property’s market rents at a 30 percent rent-to-income ratio, and the share rises to 61 percent within three miles.", body), PageBreak()]
    story += [Paragraph("Housing stock within three miles", h2), table([("Type", "Units", "Share", "Median year built"), ("Single-family detached", "17,300", "58.1%", "1968"), ("Single-family attached", "1,900", "6.4%", "1994"), ("2 to 4 units", "2,100", "7.1%", "1961"), ("5 to 19 units", "3,400", "11.4%", "1986"), ("20 to 49 units", "2,600", "8.7%", "1997"), ("50 or more units", "2,300", "7.7%", "2009"), ("Other", "180", "0.6%", ""), ("Total", "29,780", "100.0%", "1973")], [2.4 * inch, 1.2 * inch, 1.2 * inch, 1.6 * inch]), Paragraph("Apartment communities of 20 or more units represent about 16 percent of the housing stock within three miles, and the median year built for that stock is within a few years of the Property, which places Maple Street squarely in the submarket’s workforce housing segment.", body), PageBreak()]

    # ---- 13 Submarket fundamentals (3 pages)
    story += section("13. Submarket Apartment Fundamentals", "Northside submarket, all classes, properties of 20 or more units. Quarterly data from a third-party market data provider.")
    q_rows = [("Quarter", "Inventory", "Vacancy", "Asking rent", "Effective rent", "Rent growth (YoY)", "Absorption", "Deliveries")]
    base_rent = 1_390
    inventory = 9_640
    for i, q in enumerate(("Q4 2023", "Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024", "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026", "Q2 2026", "Q3 2026")):
        rent = round(base_rent * (1.0085 ** i))
        deliveries = (0, 84, 0, 120, 0, 0, 96, 0, 0, 0, 0, 72)[i]
        absorption = (62, 71, 88, 104, 58, 66, 92, 97, 54, 70, 85, 90)[i]
        inventory += deliveries
        vacancy = (0.054, 0.056, 0.055, 0.057, 0.058, 0.056, 0.055, 0.053, 0.054, 0.052, 0.051, 0.052)[i]
        q_rows.append((q, f"{inventory:,}", pct(vacancy), money(rent), money(rent * 0.985), pct(0.034 + 0.002 * ((i % 4) - 1.5), 1), str(absorption), str(deliveries)))
    story += [table(q_rows, [0.75 * inch, 0.8 * inch, 0.7 * inch, 0.85 * inch, 0.85 * inch, 0.95 * inch, 0.85 * inch, 0.85 * inch])]
    story += [Paragraph("Fundamentals by class", h2), table([("Class", "Properties", "Units", "Vacancy", "Average rent", "Rent per sf", "Avg year built"), ("A", 9, "2,180", "6.4%", "$1,790", "$1.92", "2014"), ("B", 31, "5,260", "4.9%", "$1,415", "$1.61", "1996"), ("C", 24, "2,572", "4.6%", "$1,120", "$1.38", "1974"), ("All", 64, "10,012", "5.2%", "$1,420", "$1.63", "1993")], [0.7 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch, 1.0 * inch, 0.9 * inch, 1.0 * inch]), PageBreak()]
    story += [Paragraph("Rent by floor plan, Class B", h2), table([("Floor plan", "Units surveyed", "Average sf", "Average rent", "Rent per sf", "Maple Street in-place", "Maple Street market", "Variance to survey (market)"), ("Studio", "420", "495", "$1,240", "$2.51", "$1,150", "$1,225", "($15)"), ("One bedroom", "2,610", "705", "$1,445", "$2.05", "$1,395", "$1,450", "$5"), ("Two bedroom", "1,980", "985", "$1,860", "$1.89", "$1,795", "$1,875", "$15"), ("Three bedroom", "250", "1,210", "$2,190", "$1.81", "", "", "")], [0.9 * inch, 0.8 * inch, 0.7 * inch, 0.8 * inch, 0.7 * inch, 0.85 * inch, 0.85 * inch, 1.0 * inch], font_size=7.6)]
    story += [Paragraph("The manager’s market rents for Maple Street sit within $15 of the Class B survey average for each floor plan, which supports the loss-to-lease analysis without assuming any renovation premium. Renovated units in the Peer Set lease at $140 to $185 above unrenovated units of the same plan.", body)]
    story += [Paragraph("Historical vacancy and rent growth, Northside submarket", h2), table([("Year", "Vacancy (year end)", "Effective rent growth", "Net absorption", "Deliveries", "Inventory growth"), ("2019", "6.1%", "2.8%", "188", "210", "2.3%"), ("2020", "6.8%", "0.9%", "96", "160", "1.7%"), ("2021", "4.9%", "7.4%", "312", "140", "1.5%"), ("2022", "4.6%", "8.1%", "298", "280", "2.9%"), ("2023", "5.4%", "3.2%", "246", "336", "3.4%"), ("2024", "5.8%", "2.9%", "321", "204", "2.0%"), ("2025", "5.4%", "3.4%", "309", "96", "0.9%"), ("2026 YTD (Q3)", "5.2%", "3.6%", "245", "72", "0.7%")], [1.1 * inch, 1.2 * inch, 1.3 * inch, 1.0 * inch, 0.9 * inch, 1.1 * inch]), PageBreak()]
    story += [Paragraph("Submarket outlook", h2)]
    story += [Paragraph(p, body) for p in (
        "The third-party provider’s base-case forecast for the Northside submarket projects effective rent growth of 3.1 percent in 2027 and 3.0 percent in 2028, with vacancy holding between 5.0 and 5.5 percent as the single project in the pipeline delivers in 2027. The forecast assumes continued employment growth of roughly 1.4 percent per year and no change in the pace of household formation.",
        "Downside sensitivity: the provider’s recession scenario shows vacancy rising to 7.2 percent and rent growth falling to 0.5 percent in 2027 before recovering in 2028. Under that scenario, Class B properties with below-market rents, such as Maple Street, have historically outperformed on occupancy because renewal rents remain below the asking rents of newer competition.",
        "Purchasers should note that submarket statistics are reported for all classes and that the Property’s performance will be governed by its own rent roll, renewal practice, and renovation program.",
    )]
    story += [PageBreak()]

    # ---- 14 Rent comparables (1 summary + 5 detail pages)
    story += section("14. Rent Comparables", "Five Class B garden-style communities within 3.5 miles of the Property selected for similar vintage, unit mix, and resident profile. Rents are current asking rents for unrenovated units unless noted; renovated premiums are shown where the property reports them.")
    story += [table([("Property", "Year built", "Units", "Studio", "1 bed", "2 bed", "Occupancy", "Distance")] + [(n, y, u, money(s), money(o), money(t), pct(occ), f"{d} mi") for n, y, u, s, o, t, occ, _, d in RENT_COMPS] + [("Average", "", "", money(sum(c[3] for c in RENT_COMPS) / 5), money(sum(c[4] for c in RENT_COMPS) / 5), money(sum(c[5] for c in RENT_COMPS) / 5), pct(sum(c[6] for c in RENT_COMPS) / 5), ""), ("Maple Street (in place)", 1998, 48, "$1,150", "$1,395", "$1,795", "93.8%", ""), ("Maple Street (market)", 1998, 48, "$1,225", "$1,450", "$1,875", "", "")], [1.7 * inch, 0.65 * inch, 0.5 * inch, 0.65 * inch, 0.65 * inch, 0.65 * inch, 0.8 * inch, 0.65 * inch]), PageBreak()]
    for name, year, units, studio, one, two, occ, amen, dist in RENT_COMPS:
        story += [Paragraph(f"Rent comparable: {name}", h1), table([("Attribute", "Detail"), ("Year built", str(year)), ("Units", str(units)), ("Distance from Property", f"{dist} miles"), ("Occupancy", pct(occ)), ("Amenities", amen), ("Utilities", "Residents pay electricity; water and sewer billed back" if name != "Linden Court" else "Residents pay electricity; owner pays water"), ("Parking", "Surface, 1.4 per unit" if name != "Riverside Commons" else "Surface and 24 carports"), ("Management", "Third party, regional"), ("Renovation status", {"Riverside Commons": "Roughly 60% of units renovated 2019 to 2024", "Oak Hollow Flats": "Original finishes", "Parkview Terrace": "40% renovated 2022 to 2026", "Linden Court": "Original finishes; new owner planning program", "Cedar Point Residences": "25% renovated"}[name])], [2.0 * inch, 4.6 * inch], align_right_from=9)]
        story += [Paragraph("Asking rents by floor plan", h2), table([("Floor plan", "Avg sf", "Unrenovated rent", "Renovated rent", "Premium", "Rent per sf (unrenovated)"), ("Studio", "490", money(studio), money(studio + 120) if name not in ("Oak Hollow Flats", "Linden Court") else "", "$120" if name not in ("Oak Hollow Flats", "Linden Court") else "", f"${studio / 490:.2f}"), ("One bedroom", "700", money(one), money(one + 150) if name not in ("Oak Hollow Flats", "Linden Court") else "", "$150" if name not in ("Oak Hollow Flats", "Linden Court") else "", f"${one / 700:.2f}"), ("Two bedroom", "990", money(two), money(two + 185) if name not in ("Oak Hollow Flats", "Linden Court") else "", "$185" if name not in ("Oak Hollow Flats", "Linden Court") else "", f"${two / 990:.2f}")], [1.1 * inch, 0.7 * inch, 1.2 * inch, 1.1 * inch, 0.8 * inch, 1.6 * inch])]
        story += [Paragraph("Comparison to Maple Street", h2), Paragraph(f"{name} is {'newer' if year > 1998 else 'older' if year < 1998 else 'of the same vintage'} than the Property and {'larger' if units > 48 else 'smaller'} at {units} units. Its unrenovated one-bedroom rent of {money(one)} compares with Maple Street’s in-place average of $1,395 and market rent of $1,450. Concessions at the time of survey: {'none' if occ > 0.95 else 'one-half month on twelve-month leases'}. Survey date: September 2026.", body), PageBreak()]

    # ---- 15 Sale comparables (1 summary + 5 detail pages)
    story += section("15. Sale Comparables", "Five closed sales of Class B garden-style communities in the Springfield metropolitan area since July 2025. Capitalization rates are on trailing in-place net operating income as reported at the time of sale.")
    story += [table([("Property", "City", "Year built", "Units", "Price", "Per unit", "Cap rate", "Date")] + [(n, a.split(", ")[-1], y, u, money(p), money(p / u), pct(c, 2), d) for n, a, y, u, p, c, d, *_ in SALE_COMPS] + [("Average", "", "", "", money(sum(c[4] for c in SALE_COMPS) / 5), money(sum(c[4] / c[3] for c in SALE_COMPS) / 5), pct(sum(c[5] for c in SALE_COMPS) / 5, 2), ""), ("Maple Street (guidance)", "Springfield", 1998, 48, money(PROPERTY["asking"]), money(PROPERTY["asking"] / 48), pct(fig["cap"], 2), "")], [1.6 * inch, 0.85 * inch, 0.65 * inch, 0.5 * inch, 1.0 * inch, 0.85 * inch, 0.7 * inch, 0.7 * inch]), PageBreak()]
    for name, address, year, units, price, cap, sold, desc, seller, buyer in SALE_COMPS:
        noi = price * cap
        story += [Paragraph(f"Sale comparable: {name}", h1), table([("Attribute", "Detail"), ("Address", address), ("Year built", str(year)), ("Units", str(units)), ("Description", desc), ("Sale date", sold), ("Sale price", money(price)), ("Price per unit", money(price / units)), ("Price per square foot", money(price / (units * 880))), ("In-place NOI at sale", money(noi)), ("Capitalization rate", pct(cap, 2)), ("Occupancy at sale", "94% to 96%"), ("Seller", seller), ("Buyer", buyer), ("Financing", "Agency, 60 to 65% LTV" if units > 40 else "Bank, 65% LTV"), ("Condition at sale", "Stabilized" if "value-add" not in desc else "Value-add")], [2.0 * inch, 4.6 * inch], align_right_from=9)]
        story += [Paragraph("Adjustments relative to Maple Street", h2), table([("Factor", "Adjustment", "Rationale"), ("Age and condition", {"Riverside Commons": "-5%", "Oak Hollow Flats": "+2%", "Parkview Terrace": "-6%", "Linden Court": "+6%", "Cedar Point Residences": "-1%"}[name], "Vintage and renovation share"), ("Location", {"Riverside Commons": "0%", "Oak Hollow Flats": "0%", "Parkview Terrace": "-3%", "Linden Court": "+2%", "Cedar Point Residences": "+1%"}[name], "Submarket and proximity to employment"), ("Size", "+1%" if units > 48 else "-1%", "Economies of scale"), ("Market conditions", {"Mar 2026": "0%", "Jan 2026": "+1%", "Nov 2025": "+1%", "Sep 2025": "+2%", "Jul 2025": "+2%"}[sold], "Time since sale"), ("Net adjustment", {"Riverside Commons": "-4%", "Oak Hollow Flats": "+2%", "Parkview Terrace": "-7%", "Linden Court": "+9%", "Cedar Point Residences": "+3%"}[name], ""), ("Adjusted price per unit", money(price / units * (1 + {"Riverside Commons": -0.04, "Oak Hollow Flats": 0.02, "Parkview Terrace": -0.07, "Linden Court": 0.09, "Cedar Point Residences": 0.03}[name])), "")], [1.7 * inch, 1.0 * inch, 3.9 * inch]), Paragraph("Adjustments are the broker’s qualitative opinion and are provided to assist, not replace, the purchaser’s own analysis.", small), PageBreak()]

    # ---- 16 Supply pipeline
    story += section("16. New Supply Pipeline", "Projects of 20 or more units within three miles of the Property that are under construction, approved, or in planning as of September 2026.")
    story += [table([("Project", "Units", "Class", "Distance", "Status", "Expected delivery", "Developer", "Notes"), ("The Maple Yards", 96, "A", "1.8 mi", "Under construction", "Q3 2027", "Harbor Lane Development", "Four-story elevator building, structured parking, asking rents expected $1,850 to $2,400"), ("Northside Station", 140, "A", "2.6 mi", "Approved", "2028 to 2029", "Transit Oriented Partners", "Adjacent to BRT station; financing not yet closed"), ("Cedar Street Lofts", 48, "B", "2.9 mi", "Planning", "Unknown", "Local developer", "Adaptive reuse of warehouse; rezoning hearing scheduled"), ("Parkview Terrace Phase II", 60, "A", "3.1 mi", "Planning", "Unknown", "Westbrook Multifamily Fund II", "Land owned; no permits filed")], [1.2 * inch, 0.45 * inch, 0.45 * inch, 0.6 * inch, 1.0 * inch, 0.8 * inch, 1.1 * inch, 1.0 * inch], font_size=7.4)]
    story += [Paragraph("Only The Maple Yards is expected to deliver within the Owner’s five-year hold assumption, and at projected asking rents roughly $450 above Maple Street’s market rents it competes for a different resident. Northside Station remains contingent on financing. Trailing three-year absorption in the submarket has averaged 292 units per year against 344 units of near-term pipeline.", body), PageBreak()]

    # ---- 17 Financing (2 pages)
    story += section("17. Financing Overview", "The Property will be delivered free and clear of existing debt. Northgate’s capital markets team obtained the following indicative, non-binding quotes in September 2026 based on the trailing twelve month statements and the guidance price. Terms are subject to full underwriting and change without notice.")
    story += [table([("Term", "Agency lender", "Regional bank", "Life company"), ("Loan amount", "$5,525,000 (65% LTV)", "$5,100,000 (60% LTV)", "$4,675,000 (55% LTV)"), ("Interest rate (fixed)", "5.95%", "6.10%", "5.80%"), ("Term", "10 years", "5 years", "10 years"), ("Amortization", "30 years", "25 years", "30 years"), ("Interest only", "2 years", "None", "1 year"), ("Minimum DSCR (sizing)", "1.25x", "1.30x", "1.35x"), ("Replacement reserve", "$300 per unit", "$250 per unit", "$300 per unit"), ("Prepayment", "Yield maintenance", "3-2-1 step down", "Yield maintenance"), ("Recourse", "Non-recourse", "25% recourse, burns off at 1.35x", "Non-recourse"), ("Origination fee", "1.00%", "0.50%", "0.75%"), ("Rate lock", "At commitment", "At closing", "At application")], [1.7 * inch, 1.65 * inch, 1.65 * inch, 1.6 * inch], align_right_from=9)]
    story += [Paragraph("Debt service coverage at the guidance price", h2), table([("", "Agency", "Bank", "Life company"), ("Loan amount", "$5,525,000", "$5,100,000", "$4,675,000"), ("Annual debt service (amortizing)", "$395,300", "$398,900", "$329,100"), ("In-place NOI", money(fig["noi"]), money(fig["noi"]), money(fig["noi"])), ("DSCR on in-place NOI", "1.16x", "1.15x", "1.39x"), ("DSCR on Owner’s year 3 pro forma", "1.54x", "1.53x", "1.85x"), ("Debt yield", "8.3%", "9.0%", "9.8%")], [2.4 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch])]
    story += [Paragraph("At the guidance price, in-place net operating income does not support the agency or bank quotes at their stated minimum coverage; both lenders indicated they would size to coverage, reducing proceeds to approximately $4,990,000 and $4,770,000 respectively, or require an interest reserve through stabilization. Purchasers should size their debt against their own underwriting of year one income.", body), PageBreak()]
    story += [Paragraph("Illustrative debt sizing at the Owner’s assumptions", h2), Paragraph("For purchasers who prefer a single conventional structure for screening, the Owner’s pro forma assumes a 60 percent loan-to-value, 6.00 percent fixed-rate loan amortizing over 30 years, which is between the agency and bank quotes above. Annual debt service at that structure and the guidance price is approximately $367,000.", body), table([("Measure", "Owner’s assumption"), ("Loan-to-value", pct(ASSUMPTIONS["ltv"])), ("Interest rate", pct(ASSUMPTIONS["rate"], 2)), ("Amortization", f"{ASSUMPTIONS['amort']} years"), ("Loan amount at guidance", money(PROPERTY["asking"] * ASSUMPTIONS["ltv"])), ("Annual debt service", "$366,900"), ("DSCR on in-place NOI", f"{fig['noi'] / 366_900:.2f}x"), ("Equity at guidance including 2% closing costs", money(PROPERTY["asking"] * (1 - ASSUMPTIONS["ltv"]) + PROPERTY["asking"] * ASSUMPTIONS["closing_costs"]))], [3.2 * inch, 3.4 * inch]), PageBreak()]

    # ---- 18 Taxes, insurance, utilities (2 pages)
    story += section("18. Taxes, Insurance, and Utilities")
    story += [Paragraph("Real estate taxes", h2), table([("Tax year", "Assessed value", "Effective rate", "Taxes", "Change"), ("2021", "$5,420,000", "1.88%", "$101,900", ""), ("2022", "$5,420,000", "1.87%", "$101,400", "-0.5%"), ("2023", "$5,420,000", "1.94%", "$105,100", "+3.6%"), ("2024", "$6,140,000", "1.79%", "$109,900", "+4.6%"), ("2025", "$6,140,000", "1.86%", "$114,200", "+3.9%"), ("2026", "$6,140,000", "1.92%", "$118,000", "+3.3%"), ("Upon sale at guidance (estimate)", "$8,500,000", "1.92%", "$163,200", "+38.3%")], [2.0 * inch, 1.2 * inch, 1.1 * inch, 1.1 * inch, 1.2 * inch])]
    story += [Paragraph("Springfield County reassesses on a six-year cycle, most recently for the 2024 tax year, and additionally upon recorded transfer. Taxes are payable in two installments (March and September). There are no special assessments or abatements affecting the parcel. Purchasers should confirm the treatment of the sale with the county assessor; the estimate above assumes assessment at the recorded consideration.", body)]
    story += [Paragraph("Insurance", h2), table([("Coverage", "Limit", "Deductible", "Carrier", "Premium"), ("Property (replacement cost)", "$9,500,000", "$25,000", "Regional mutual", "$26,400"), ("General liability", "$2,000,000 per occurrence", "$5,000", "Regional mutual", "$5,100"), ("Umbrella", "$5,000,000", "", "National carrier", "$2,500"), ("Total", "", "", "", "$34,000")], [2.0 * inch, 1.5 * inch, 0.9 * inch, 1.2 * inch, 1.0 * inch]), PageBreak()]
    story += [Paragraph("Utilities", h2), table([("Service", "Provider", "Paid by", "Metering", "T-12 cost to Owner"), ("Electricity", "Springfield Power and Light", "Residents (units); Owner (common)", "Individual unit meters; 3 house meters", "$7,800"), ("Natural gas", "Northern Gas", "Owner", "One master meter per building", "$27,040"), ("Water and sewer", "City of Springfield", "Owner", "One master meter", "$14,040"), ("Trash", "County contract hauler", "Owner (in contract services)", "", "In contract services"), ("Telephone and internet", "Various", "Residents; Owner (office)", "", "$3,120")], [1.2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch, 0.9 * inch], font_size=7.8)]
    story += [Paragraph("Utility consumption history", h2), table([("Year", "Gas (therms)", "Gas cost", "Water (1,000 gal)", "Water and sewer cost", "Common electricity (kWh)", "Electricity cost"), ("2023", "38,900", "$24,100", "2,310", "$12,400", "61,200", "$7,100"), ("2024", "37,600", "$25,000", "2,280", "$12,900", "59,800", "$7,300"), ("2025", "38,200", "$26,200", "2,340", "$13,600", "60,400", "$7,600"), ("T-12", "38,500", "$27,040", "2,350", "$14,040", "60,900", "$7,800")], [0.6 * inch, 0.9 * inch, 0.8 * inch, 1.0 * inch, 1.1 * inch, 1.2 * inch, 0.9 * inch], font_size=7.8), Paragraph("Consumption has been flat; cost growth reflects rate increases of roughly four percent per year for gas and five percent for water and sewer.", body), PageBreak()]

    # ---- 19 Zoning, environmental, physical (2 pages)
    story += section("19. Zoning, Environmental, and Physical Condition")
    story += [Paragraph("Zoning", h2), Paragraph("The parcel is zoned RM-2 (Residential Multifamily, Medium Density) under the City of Springfield zoning ordinance, which permits multifamily dwellings by right at up to 24 units per acre with a maximum height of 45 feet. The existing density of 22.9 units per acre and three-story height conform. Parking is required at 1.25 spaces per unit (60 spaces); 72 are provided. The 2025 comprehensive plan designates the corridor for densities up to 30 units per acre, but no rezoning has been applied for. A zoning verification letter dated 14 August 2026 is available in the data room.", body)]
    story += [Paragraph("Environmental", h2), Paragraph("A Phase I Environmental Site Assessment dated 22 July 2026 identified no recognized environmental conditions. The report notes a historical dry-cleaning operation approximately 600 feet southeast of the site that closed in 1994 and is listed as a closed state case with no further action required. No asbestos-containing materials are expected given the 1998 construction date; a limited survey in 2018 prior to the roof replacement found none. Radon testing in 2024 in ground-floor units measured below the action level. The report is available in the data room and may be relied upon by a purchaser upon issuance of a reliance letter.", body)]
    story += [Paragraph("Physical condition", h2), Paragraph("A Property Condition Assessment dated 5 August 2025 estimated immediate repairs of $21,500 (sidewalk trip hazards, two balcony railings, exterior stair treads at Building C, and sealing of the trash enclosure slab) and a twelve-year replacement reserve of $318 per unit per year. Immediate repair items have been completed except for the Building C stair treads, which are scheduled for October 2026. Major component remaining useful lives per the report are summarized below.", body), table([("Component", "Installed", "Expected useful life", "Remaining (years)", "Replacement estimate"), ("Roofs", "2018", "30", "22", "$310,000"), ("Boilers and hot water", "2020", "25", "19", "$160,000"), ("Through-wall heat pumps", "1998 to 2022", "15", "0 to 11", "$3,400 per unit"), ("Windows", "1998", "30", "2", "$212,000"), ("Parking lot (overlay)", "2023", "15", "12", "$95,000"), ("Exterior paint and sealant", "2024", "8", "6", "$75,000"), ("Kitchen appliances", "1998 to 2026", "12", "0 to 12", "$2,100 per unit"), ("Water heaters (central)", "2020", "15", "9", "$38,000"), ("Elevators", "None", "", "", "")], [1.7 * inch, 1.0 * inch, 1.2 * inch, 1.2 * inch, 1.5 * inch]), PageBreak()]
    story += [Paragraph("Accessibility and code", h2), Paragraph("Four ground-floor one-bedroom units were constructed as accessible units under the Fair Housing Act design requirements applicable in 1998; the leasing office and common laundry rooms are accessible. There are no open code violations of record. The City performed its triennial rental inspection in March 2026 and issued a certificate of compliance with two minor items (a missing smoke detector battery and a damaged screen door) that were corrected within the cure period.", body), Paragraph("Flood and seismic", h2), Paragraph("The parcel lies in FEMA Zone X (minimal flood hazard) per the current flood insurance rate map; flood insurance is not required by lenders. Seismic risk is low for the region and no seismic study has been performed.", body), Paragraph("Title and survey", h2), Paragraph("A title commitment dated 1 September 2026 and an ALTA survey dated 2019 are available in the data room. The commitment shows no easements that interfere with the current use. The survey identifies a 10-foot utility easement along the Third Avenue frontage and a shared access agreement with the adjacent retail parcel for the rear drive.", body), PageBreak()]

    # ---- 20 Property management
    story += section("20. Property Management")
    story += [Paragraph(p, body) for p in (
        "The Property has been managed since 2017 by Crestline Residential Management, a regional third-party manager with approximately 3,800 units under management in the Springfield and Westbrook markets. The management agreement provides for a fee of three percent of effective gross income with a $2,500 monthly minimum, a 30-day termination right upon sale, and no termination fee. Crestline has indicated its willingness to continue under a new owner on the same terms or to transition on a schedule convenient to the purchaser.",
        "On-site staff consists of a full-time community manager (employed since 2019), a full-time maintenance technician (since 2021), and a seasonal part-time leasing associate. Staff are employees of the manager. The Property uses a national property management software platform for leasing, accounting, and resident payments; 91 percent of residents pay electronically.",
        "Leasing is handled on site with marketing through the manager’s website, two national internet listing services, and referral programs. Average days vacant at turnover over the trailing twelve months was 23 days, and the trailing twelve month resident retention rate was 74 percent.",
    )]
    story += [Paragraph("Resident profile (manager’s survey, September 2026)", h2), table([("Measure", "Value"), ("Average household income (reported at application)", "$61,400"), ("Average rent-to-income ratio", "26.8%"), ("Average household size", "1.9"), ("Average tenure of current residents", "2.6 years"), ("Residents employed in healthcare", "31%"), ("Residents employed in logistics or manufacturing", "22%"), ("Residents employed in education or government", "18%"), ("Pet ownership", "38% of households")], [4.0 * inch, 2.6 * inch]), PageBreak()]

    # ---- 21 Offering process
    story += section("21. Offering Process")
    story += [Paragraph("Timeline", h2), table([("Milestone", "Date"), ("Marketing launch", "6 October 2026"), ("Property tours (by appointment)", "13 October to 7 November 2026"), ("Data room access", "Upon execution of confidentiality agreement"), ("Call for offers", "12 November 2026, 5:00 pm local time"), ("Best and final (if required)", "Week of 17 November 2026"), ("Selection of purchaser", "Week of 24 November 2026"), ("Purchase and sale agreement executed", "Within 10 business days of selection"), ("Due diligence period", "30 days"), ("Closing", "30 days after expiration of due diligence")], [3.6 * inch, 3.0 * inch], align_right_from=9)]
    story += [Paragraph("Offer requirements", h2)]
    story += bullets([
        "Purchase price and the source and amount of equity and debt, with evidence of the ability to fund.",
        "Earnest money deposit (minimum two percent of the purchase price, non-refundable after due diligence).",
        "Due diligence and closing periods, and any conditions to closing.",
        "A summary of the purchaser’s experience with comparable acquisitions in the region.",
        "Confirmation that the purchaser has reviewed the data room, including the title commitment, survey, Phase I, and Property Condition Assessment.",
        "Identification of any brokers other than Northgate claiming a commission; the Owner will not pay a cooperating commission.",
    ])
    story += [Paragraph("Data room contents", h2), table([("Folder", "Contents"), ("01 Financials", "Monthly operating statements 2021 to September 2026; general ledgers; bank statements (trailing 12 months); budget 2027"), ("02 Rent roll and leases", "Current rent roll; lease files for all occupied units; standard lease form; pet and parking addenda"), ("03 Property", "Site plan; architectural drawings; unit floor plans; photographs; warranties"), ("04 Reports", "Phase I ESA (2026); Property Condition Assessment (2025); radon results (2024); zoning letter (2026)"), ("05 Title and survey", "Title commitment (2026); ALTA survey (2019); recorded easements"), ("06 Contracts", "Management agreement; service contracts (landscaping, pest, trash, laundry route, software)"), ("07 Taxes and insurance", "Tax bills 2021 to 2026; assessment notices; insurance policies and loss runs (5 years)"), ("08 Capital", "Invoices and warranties for completed projects; renovation bids (2026)")], [1.6 * inch, 5.0 * inch], align_right_from=9)]
    story += [Paragraph("Contacts", h2), Paragraph("Dana Whitfield, Senior Managing Director · Priya Raman, Director · Tomas Alvarez, Financial Analyst · Northgate Capital Advisors, 400 Commerce Street, Suite 900, Springfield. All inquiries, including requests for tours, must be directed to the listing team. Contact with on-site staff, residents, or the Owner is prohibited without prior written consent. (Fictional firm and names.)", body), PageBreak()]

    # ---- Appendix A: Deal Scope Data Sheet (identical format to the demo kit)
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
        "Source or document reference: Northgate Capital Advisors full offering memorandum, October 2026 (mock)",
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
        Paragraph("This appendix restates the offering’s underwriting inputs in the Deal Scope Data Sheet format so the packet can be imported directly. Labels match the Excel import template and are matched flexibly; percentages may be written as 5%, 5 or 0.05. Income and expense totals are left to roll up from the tables so the detail is preserved. Everything an analyst would otherwise transcribe from the preceding sixty pages is on these two.", body),
        Preformatted("\n".join(sheet_lines), mono),
        PageBreak(),
    ]

    # ---- Appendix B: data requirements
    story += [Paragraph("Appendix B — What Deal Scope needs to underwrite a deal", h1), Paragraph("The model builds a complete deal from eleven required inputs; everything else enriches the output. The table maps each input to the section of this memorandum it comes from, which is also the map of where an analyst’s time goes without the data sheet.", body), table([
        ("Input", "Required", "Where it comes from"), ("Purchase price (asking or guide)", "Yes", "Section 1, Executive Summary"), ("Closing costs", "Yes", "Buyer assumption"), ("Hold period", "Yes", "Buyer assumption"), ("Exit cap rate", "Yes", "Section 15, Sale Comparables"), ("Selling costs", "Yes", "Buyer assumption"),
        ("Current potential gross income", "Yes, or roll up", "Sections 5, 7, 8"), ("Current operating expenses", "Yes, or roll up", "Sections 7, 8, 9"), ("Vacancy and credit loss", "Yes", "Sections 7, 8, 13"), ("Rent growth and expense growth", "Yes", "Sections 9, 13"), ("Loan-to-value, interest rate, amortization", "Yes", "Section 17, Financing Overview"), ("Target levered IRR, minimum DSCR", "Recommended", "Buyer’s investment criteria; Section 17 for lender floors"),
        ("Units, square feet, class, year built", "Optional", "Section 3, Property Description"), ("Rent roll, other income, expense lines", "Optional", "Sections 4, 5, 7, 9"), ("Version label, source, effective date, confidence", "Recommended", "This document"),
    ], [2.6 * inch, 1.1 * inch, 2.9 * inch], align_right_from=9), Paragraph("Reading this memorandum end to end, reconciling the rent roll to the operating statements, adjusting taxes for reassessment, and keying the result into a model takes an analyst most of a working day. The data sheet reduces the keying to a file drop; the judgment stays with the analyst.", body), PageBreak()]

    # ---- Appendix C: glossary (2 pages)
    story += [Paragraph("Appendix C — Glossary", h1), table([("Term", "Definition")] + [
        ("Absorption", "Net change in occupied units over a period."), ("Capitalization rate", "Net operating income divided by price or value."), ("Concessions", "Rent discounts or free periods granted to attract or retain residents."), ("DSCR", "Debt service coverage ratio: net operating income divided by annual debt service."), ("Debt yield", "Net operating income divided by loan amount."), ("Effective gross income", "Potential gross income less vacancy, concessions, and credit loss."),
        ("Gross potential rent", "Rent that would be collected if every unit were occupied at its scheduled rent."), ("Loss to lease", "The difference between market rent and in-place rent across the rent roll."), ("LTV", "Loan-to-value ratio."), ("Net operating income", "Effective gross income less operating expenses, before debt service and capital items."), ("Physical occupancy", "Occupied units divided by total units on a given date."), ("Economic occupancy", "Collected rent divided by gross potential rent over a period."), ("Pro forma", "A projection of future operations under stated assumptions."), ("Ratio utility billing", "Allocation of a master-metered utility cost to residents by formula."),
        ("Replacement reserves", "An annual allowance for the replacement of building components."), ("T-12", "Trailing twelve months."), ("Turnover", "The cost and vacancy associated with a resident moving out and a new resident moving in."), ("Value-add", "An investment strategy that increases income through renovation or operational improvement."), ("Yield maintenance", "A prepayment premium that compensates the lender for lost interest."),
    ], [1.8 * inch, 4.8 * inch], align_right_from=9)]
    story += [Spacer(1, 0.3 * inch), Paragraph("End of memorandum. This mock document was generated for a product demonstration; nothing in it describes a real property, firm, person, or transaction.", small)]

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return path


def build_full_memorandum(output_dir: Path) -> Path:
    """Build twice so the contents page carries real page numbers."""
    first = build(output_dir)
    return build(output_dir, page_index(first))


if __name__ == "__main__":
    print("wrote", build_full_memorandum(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()))
