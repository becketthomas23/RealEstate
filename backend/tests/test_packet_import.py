from decimal import Decimal
from io import BytesIO
from pathlib import Path
import unittest

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate

from backend.packet_import import parse_deal_packet


D = Decimal
DEMO_PACKET = Path(__file__).resolve().parents[2] / "demo" / "Maple Street Apartments - Offering Memorandum (mock).pdf"
FULL_PACKET = DEMO_PACKET.with_name("Maple Street Apartments - Full Offering Memorandum (mock).pdf")


def _pdf(*blocks: str) -> bytes:
    output = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output, pagesize=letter)
    story = []
    for block in blocks:
        story.append(Preformatted(block, styles["Code"]) if "|" in block or ":" in block else Paragraph(block, styles["BodyText"]))
    doc.build(story)
    return output.getvalue()


class DealPacketImportTests(unittest.TestCase):
    @unittest.skipUnless(DEMO_PACKET.exists(), "demo packet not built")
    def test_reads_the_demo_offering_memorandum(self) -> None:
        imported = parse_deal_packet(DEMO_PACKET.read_bytes())

        underwriting = imported.underwriting
        self.assertEqual(underwriting.purchase_price, D("8500000"))
        self.assertEqual(underwriting.loan_to_value, D("0.6"))
        self.assertEqual(underwriting.exit_cap_rate, D("0.065"))
        self.assertEqual(underwriting.operating.hold_period_years, 5)
        # Income and expenses roll up from the data-sheet tables.
        self.assertEqual(underwriting.operating.current_potential_gross_income, D("909600"))
        self.assertEqual(underwriting.operating.current_operating_expenses, D("405400"))
        detail = imported.supporting_detail
        self.assertEqual(detail.property.name, "Maple Street Apartments")
        self.assertEqual(detail.property.units, 48)
        self.assertEqual(detail.property.rentable_square_feet, D("42000"))
        self.assertEqual(len(detail.rent_roll), 3)
        self.assertEqual(len(detail.other_income), 3)
        self.assertEqual(len(detail.operating_expenses), 10)
        self.assertEqual(imported.version["label"], "Broker OM base case")
        self.assertEqual(imported.version["effective_date"], "2026-09-30")
        self.assertEqual(imported.targets["target_levered_irr"], D("0.12"))
        self.assertEqual(imported.targets["minimum_dscr"], D("1.25"))
        self.assertIn("_packet", imported.sources)

    @unittest.skipUnless(DEMO_PACKET.exists() and FULL_PACKET.exists(), "demo packets not built")
    def test_full_length_memorandum_imports_identically(self) -> None:
        """The 58-page packet carries the same data sheet, so the version it produces matches the short one."""
        short = parse_deal_packet(DEMO_PACKET.read_bytes())
        full = parse_deal_packet(FULL_PACKET.read_bytes())

        self.assertEqual(full.underwriting, short.underwriting)
        self.assertEqual(full.supporting_detail.rent_roll, short.supporting_detail.rent_roll)
        self.assertEqual(full.supporting_detail.operating_expenses, short.supporting_detail.operating_expenses)
        self.assertEqual(full.targets, short.targets)
        self.assertEqual(full.version["label"], short.version["label"])
        self.assertIn("full offering memorandum", full.version["source"])
        self.assertIn("_packet", full.sources)

    def test_reads_a_hand_typed_data_sheet_with_aliases(self) -> None:
        packet = _pdf(
            "Some narrative about the asset.",
            "DEAL SCOPE DATA SHEET\nAsking price: $1,000,000\nClosing costs: 2%\nHold period: 5\nTerminal cap rate: 10%\nCost of sale: 0.02\nGPR: 200,000\nOpEx: 50,000\nVacancy: 10%\nRent growth: 0\nExpense growth: 0\nLTV: 60%\nNote rate: 0\nAmort: 5\nScenario: Downside\nEND OF DATA SHEET",
        )

        imported = parse_deal_packet(packet)

        self.assertEqual(imported.underwriting.purchase_price, D("1000000"))
        self.assertEqual(imported.underwriting.exit_cap_rate, D("0.1"))
        self.assertEqual(imported.underwriting.operating.vacancy_rate, D("0.1"))
        self.assertEqual(imported.underwriting.amortization_years, 5)
        self.assertEqual(imported.version["label"], "Downside")
        self.assertEqual(imported.supporting_detail.rent_roll, [])

    def test_explains_when_the_packet_has_no_data_sheet(self) -> None:
        with self.assertRaisesRegex(ValueError, "Data Sheet"):
            parse_deal_packet(_pdf("An offering memorandum with photographs and narrative only."))

    def test_rejects_a_file_that_is_not_a_pdf(self) -> None:
        with self.assertRaisesRegex(ValueError, "readable PDF"):
            parse_deal_packet(b"not a pdf")
