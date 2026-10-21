"""Downloadable underwriting workbook and investment-memo reports."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors


def excel_cash_flow(result, assumptions=None):
    book = Workbook(); summary = book.active; summary.title = "Summary"; cash = book.create_sheet("Cash Flow"); risks = book.create_sheet("Risk Flags")
    assumption_sheet = book.create_sheet("Assumptions") if assumptions is not None else None
    summary.append(["Underwriting Summary", "Value"])
    for row in [("Going-in cap rate", result.going_in_cap_rate), ("Debt yield", result.debt_yield if result.debt_yield is not None else "N/A — all-cash"), ("Levered IRR", result.returns.levered_irr), ("Equity Multiple", result.returns.equity_multiple), ("Minimum DSCR", result.returns.minimum_dscr if result.returns.minimum_dscr is not None else "N/A — all-cash"), ("Terminal NOI", result.terminal_noi), ("Net Sale Proceeds", result.disposition.net_sale_proceeds_to_equity)]: summary.append(row)
    cash.append(["Year", "NOI", "Debt Service", "Operating Equity Cash Flow", "Sale Proceeds", "Total Equity Cash Flow", "Cash-on-Cash", "YoY Total Cash Flow Change"])
    prior = None
    for operating, debt, operating_flow, flow, cash_on_cash in zip(result.operating_projection, result.debt_projection, result.annual_operating_cash_flows, result.annual_cash_flows, result.returns.cash_on_cash_by_year):
        sale_proceeds = flow - operating_flow
        cash.append([operating.year, operating.net_operating_income, debt.debt_service, operating_flow, sale_proceeds, flow, cash_on_cash, None if prior is None else (flow / prior - 1 if prior else None)]); prior = flow
    risks.append(["Code", "Severity", "Message", "Observed", "Threshold"])
    for flag in result.risk_flags:
        risks.append([flag.code, flag.severity, flag.message, flag.observed_value, flag.threshold])
    if assumption_sheet is not None:
        assumption_sheet.append(["Underwriting assumptions", "Value"])
        for row in _assumption_rows(assumptions): assumption_sheet.append(row)
    for sheet in (summary, cash, risks, *([assumption_sheet] if assumption_sheet is not None else [])):
        for cell in sheet[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="166534")
        sheet.freeze_panes = "A2"
        for column in sheet.columns: sheet.column_dimensions[column[0].column_letter].width = 24
    summary_formats = {2: "0.0%", 3: "0.0%", 4: "0.0%", 5: '0.00x', 6: '0.00x', 7: '$#,##0;($#,##0)', 8: '$#,##0;($#,##0)'}
    for row in summary.iter_rows(min_row=2, min_col=2): row[0].number_format = summary_formats[row[0].row]
    for row in cash.iter_rows(min_row=2, min_col=2, max_col=6):
        for cell in row: cell.number_format = '$#,##0;($#,##0)'
    for cell in cash['G'][1:]: cell.number_format = '0.0%'
    for cell in cash['H'][1:]: cell.number_format = '0.0%'
    for row in risks.iter_rows(min_row=2, min_col=4, max_col=5):
        for cell in row: cell.number_format = '0.00'
    output = BytesIO(); book.save(output); output.seek(0); return output


def investment_memo(result, assumptions=None):
    output = BytesIO(); doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42); styles = getSampleStyleSheet()
    styles["Heading2"].spaceBefore = 8; styles["Heading2"].spaceAfter = 4; styles["BodyText"].spaceBefore = 0; styles["BodyText"].spaceAfter = 0
    irr = float(result.returns.levered_irr); dscr = float(result.returns.minimum_dscr) if result.returns.minimum_dscr is not None else None
    opinion = "The modeled return is compelling" if irr >= .15 else "The modeled return is moderate" if irr >= .10 else "The modeled return is below a typical target threshold"
    risk = "No debt service is modeled, so DSCR and debt yield are not applicable." if dscr is None else ("Debt coverage is thin and warrants caution." if dscr < 1.20 else "Debt coverage is within a more resilient range.")
    story=[Paragraph("Investment Memo", styles["Title"]), Paragraph(f"{opinion}. {risk}", styles["BodyText"]), Spacer(1,12), Paragraph("Return summary", styles["Heading2"])]
    rows=[["Metric","Result"],["Going-in cap rate",f"{float(result.going_in_cap_rate):.1%}"],["Debt yield",f"{float(result.debt_yield):.1%}" if result.debt_yield is not None else "N/A — all-cash"],["Levered IRR",f"{irr:.1%}"],["Equity multiple",f"{float(result.returns.equity_multiple):.2f}x"],["Minimum DSCR",f"{dscr:.2f}x" if dscr is not None else "N/A — all-cash"],["Terminal NOI",f"${float(result.terminal_noi):,.0f}"],["Net sale proceeds",f"${float(result.disposition.net_sale_proceeds_to_equity):,.0f}"]]
    table=Table(rows, colWidths=[220,220]); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#166534")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.grey),("PADDING",(0,0),(-1,-1),4), ("FONTSIZE", (0, 0), (-1, -1), 9)])); story += [table, Spacer(1,8)]
    if assumptions is not None:
        assumption_rows = [["Assumption", "Value"]] + _assumption_rows(assumptions)
        assumption_table = Table(assumption_rows, colWidths=[220, 220])
        assumption_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#166534")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("PADDING", (0, 0), (-1, -1), 3), ("FONTSIZE", (0, 0), (-1, -1), 8.5)]))
        story += [Paragraph("Key assumptions", styles["Heading2"]), assumption_table, Spacer(1, 8)]
    story += [Paragraph("Risk review", styles["Heading2"])]
    if result.risk_flags:
        risk_rows=[["Severity", "Flag"]] + [[flag.severity.title(), flag.message] for flag in result.risk_flags]
        risk_table=Table(risk_rows, colWidths=[90,350]); risk_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#92400e")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.grey),("PADDING",(0,0),(-1,-1),4), ("FONTSIZE", (0, 0), (-1, -1), 9)])); story += [risk_table, Spacer(1,8)]
    else:
        story += [Paragraph("No rules-based risk flags were triggered by the modeled assumptions.", styles["BodyText"]), Spacer(1,12)]
    story += [Paragraph("Cash flow outlook", styles["Heading2"]), Paragraph("Annual cash flows and the modeled disposition drive the return outcome. Review exit-cap assumptions, rent growth, and interest-rate sensitivity before relying on the base case.", styles["BodyText"])]
    doc.build(story); output.seek(0); return output


def _assumption_rows(assumptions):
    operating = assumptions.operating
    schedule = operating.annual_rent_growth_rates
    schedule_display = ", ".join(f"{float(rate):.1%}" for rate in schedule) if schedule else "Not supplied (base rate used)"
    return [
        ["Purchase price", f"${float(assumptions.purchase_price):,.0f}"],
        ["Closing costs", f"{float(assumptions.closing_cost_rate):.1%}"],
        ["Loan-to-value", f"{float(assumptions.loan_to_value):.1%}"],
        ["Annual interest rate", f"{float(assumptions.annual_interest_rate):.1%}"],
        ["Amortization", f"{assumptions.amortization_years} years"],
        ["Exit cap rate", f"{float(assumptions.exit_cap_rate):.1%}"],
        ["Selling costs", f"{float(assumptions.selling_cost_rate):.1%}"],
        ["Current potential gross income", f"${float(operating.current_potential_gross_income):,.0f}"],
        ["Current operating expenses", f"${float(operating.current_operating_expenses):,.0f}"],
        ["Vacancy", f"{float(operating.vacancy_rate):.1%}"],
        ["Base rent growth", f"{float(operating.rent_growth_rate):.1%}"],
        ["Annual rent-growth schedule", schedule_display],
        ["Expense growth", f"{float(operating.expense_growth_rate):.1%}"],
        ["Hold period", f"{operating.hold_period_years} years"],
    ]
