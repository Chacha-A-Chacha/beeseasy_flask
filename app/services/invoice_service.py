"""
Proforma Invoice PDF Generation Service for Pollination Africa 2026.

Generates professional proforma invoices using ReportLab,
following the same storage and generation patterns as BadgeService.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from svglib.svglib import svg2rlg

from app.extensions import db

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for generating proforma invoice PDFs"""

    PAGE_SIZE = A4
    STORAGE_BASE = "storage/invoices"

    # Brand colors
    COLOR_GREEN = colors.HexColor("#2c5f2d")
    COLOR_GOLD = colors.HexColor("#e8b030")
    COLOR_BROWN = colors.HexColor("#5c3a21")
    COLOR_DARK = colors.HexColor("#212529")
    COLOR_GRAY = colors.HexColor("#6c757d")
    COLOR_LIGHT_BG = colors.HexColor("#f8f9fa")
    COLOR_BORDER = colors.HexColor("#dee2e6")

    # ============================================
    # MAIN INVOICE GENERATION
    # ============================================

    @classmethod
    def generate_invoice(
        cls, payment_id: int, force_regenerate: bool = False
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate proforma invoice PDF for a payment.

        Returns:
            Tuple of (success, message, invoice_url)
        """
        from app.models import Payment, Registration

        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return False, "Payment not found", None

            registration = Registration.query.get(payment.registration_id)
            if not registration:
                return False, "Registration not found", None

            # Check if already generated
            if payment.invoice_url and payment.invoice_generated and not force_regenerate:
                return True, "Invoice already exists", payment.invoice_url

            # Build PDF
            storage_path = cls._get_storage_path()
            filename = f"{payment.invoice_number or payment.payment_reference}.pdf"
            full_path = storage_path / filename

            cls._build_pdf(str(full_path), registration, payment)

            # Update payment record
            invoice_url = f"/{cls.STORAGE_BASE}/{datetime.now().year}/{filename}"
            payment.invoice_url = invoice_url
            payment.invoice_generated = True
            db.session.commit()

            logger.info(f"Invoice generated: {payment.invoice_number} for {registration.reference_number}")
            return True, "Invoice generated successfully", invoice_url

        except Exception as e:
            logger.error(f"Error generating invoice: {str(e)}", exc_info=True)
            db.session.rollback()
            return False, f"Failed to generate invoice: {str(e)}", None

    # ============================================
    # STORAGE
    # ============================================

    @classmethod
    def _get_storage_path(cls) -> Path:
        year = datetime.now().year
        storage_path = Path(current_app.root_path) / cls.STORAGE_BASE / str(year)
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    # ============================================
    # PDF BUILDER
    # ============================================

    @classmethod
    def _build_pdf(cls, filepath: str, registration, payment) -> None:
        """Build the complete proforma invoice PDF."""
        doc = SimpleDocTemplate(
            filepath,
            pagesize=cls.PAGE_SIZE,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )

        styles = getSampleStyleSheet()
        elements = []

        # -- Styles --
        s_org_name = ParagraphStyle(
            "InvOrgName", parent=styles["Heading1"],
            fontSize=16, fontName="Helvetica-Bold",
            textColor=cls.COLOR_GREEN, alignment=TA_LEFT,
            spaceAfter=1 * mm, leading=18,
        )
        s_contact = ParagraphStyle(
            "InvContact", parent=styles["Normal"],
            fontSize=8, textColor=cls.COLOR_GRAY, alignment=TA_LEFT,
            spaceAfter=0, leading=11,
        )
        s_heading = ParagraphStyle(
            "InvHeading", parent=styles["Heading2"],
            fontSize=14, fontName="Helvetica-Bold",
            textColor=cls.COLOR_GREEN, spaceAfter=4 * mm,
            spaceBefore=2 * mm, alignment=TA_CENTER,
        )
        s_section = ParagraphStyle(
            "InvSection", parent=styles["Heading3"],
            fontSize=11, fontName="Helvetica-Bold",
            textColor=cls.COLOR_GREEN, spaceAfter=3 * mm,
        )
        s_normal = ParagraphStyle(
            "InvNormal", parent=styles["Normal"],
            fontSize=9, textColor=cls.COLOR_DARK, leading=13,
        )
        s_label = ParagraphStyle(
            "InvLabel", parent=styles["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=cls.COLOR_GRAY,
        )
        s_value = ParagraphStyle(
            "InvValue", parent=styles["Normal"],
            fontSize=9, textColor=cls.COLOR_DARK,
        )
        config = current_app.config

        # ========== HEADER: Logo + name/theme left, contact right ==========
        logo_element = cls._get_logo_element()

        s_org_title = ParagraphStyle(
            "InvOrgTitle", parent=styles["Normal"],
            fontSize=11, fontName="Helvetica-Bold",
            textColor=cls.COLOR_GREEN, leading=13,
            spaceAfter=1 * mm,
        )
        s_theme = ParagraphStyle(
            "InvTheme", parent=styles["Normal"],
            fontSize=7, textColor=cls.COLOR_BROWN, leading=9,
            fontName="Helvetica-Oblique",
        )
        s_contact_r = ParagraphStyle(
            "InvContactR", parent=styles["Normal"],
            fontSize=8, textColor=cls.COLOR_GRAY, alignment=TA_RIGHT,
            leading=11,
        )

        event_theme = config.get(
            "EVENT_THEME",
            "Advancing Pollinators for Biodiversity, Climate Resilience, and Food Security in Africa",
        )

        # Build left block: logo + name + theme stacked
        name_and_theme = Paragraph(
            f"<b>POLLINATION AFRICA</b><br/>"
            f"<b>SUMMIT 2026</b><br/>"
            f"<i><font size=7 color='#{cls.COLOR_BROWN.hexval()[2:]}'>{event_theme}</font></i>",
            s_org_title,
        )

        contact_block = Paragraph(
            f"P.O. Box 11547 Arusha, Tanzania<br/>"
            f"Email: {config.get('CONTACT_EMAIL', 'info@pollination.africa')}<br/>"
            f"Tel: {config.get('SUPPORT_PHONE', '+255 767 727 619')}<br/>"
            f"{config.get('WEBSITE_URL', 'www.pollination.africa')}",
            s_contact_r,
        )

        if logo_element:
            left_table = Table(
                [[logo_element, name_and_theme]],
                colWidths=[22 * mm, 68 * mm],
            )
            left_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]))

            header_table = Table(
                [[left_table, contact_block]],
                colWidths=[95 * mm, 75 * mm],
            )
            header_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(header_table)
        else:
            elements.append(Paragraph("POLLINATION AFRICA SUMMIT 2026", s_org_title))
            elements.append(Paragraph(event_theme, s_theme))
            elements.append(contact_block)

        # Gold divider line — tight spacing
        elements.append(HRFlowable(
            width="100%", thickness=2, color=cls.COLOR_GOLD,
            spaceAfter=5 * mm, spaceBefore=3 * mm,
        ))

        # PROFORMA INVOICE heading
        elements.append(Paragraph("PROFORMA INVOICE", s_heading))
        elements.append(Spacer(1, 3 * mm))

        # ========== ISSUED BY / ISSUED TO ==========
        issued_by_data = [
            [Paragraph("<b>Issued by:</b>", s_label), Paragraph("<b>Invoice Issued To:</b>", s_label)],
            [
                Paragraph(
                    f"{config.get('EVENT_NAME', 'Pollination Africa Summit 2026')}<br/>"
                    f"P.O Box 11547, Arusha, Tanzania<br/>"
                    f"Email: {config.get('CONTACT_EMAIL', 'info@pollination.africa')}<br/>"
                    f"Phone: {config.get('SUPPORT_PHONE', '+255 767 727 619')}",
                    s_normal,
                ),
                Paragraph(cls._get_invoice_to_text(registration), s_normal),
            ],
        ]

        issued_table = Table(issued_by_data, colWidths=[85 * mm, 85 * mm])
        issued_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(issued_table)
        elements.append(Spacer(1, 4 * mm))

        # ========== INVOICE META ==========
        invoice_number = payment.invoice_number or payment.payment_reference
        date_of_issue = datetime.now().strftime("%d %B %Y")

        meta_data = [
            [Paragraph("Invoice Number:", s_label), Paragraph(f"PAS/PI/2026/{invoice_number}", s_value)],
            [Paragraph("Date of Issue:", s_label), Paragraph(date_of_issue, s_value)],
            [Paragraph("Event:", s_label), Paragraph(config.get("EVENT_NAME", "Pollination Africa Summit 2026"), s_value)],
            [Paragraph("Event Date:", s_label), Paragraph(config.get("EVENT_DATE", "June 2026"), s_value)],
            [Paragraph("Location:", s_label), Paragraph(config.get("EVENT_LOCATION", "Arusha, Tanzania"), s_value)],
        ]

        meta_table = Table(meta_data, colWidths=[40 * mm, 130 * mm])
        meta_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (-1, -2), 0.5, cls.COLOR_BORDER),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 6 * mm))

        # ========== LINE ITEMS TABLE ==========
        item_description = cls._get_item_description(registration)
        currency = payment.currency or "USD"
        amount = float(payment.total_amount)

        header_style = ParagraphStyle(
            "ItemHeader", parent=styles["Normal"],
            fontSize=9, fontName="Helvetica-Bold", textColor=colors.white,
        )
        item_style = ParagraphStyle(
            "ItemCell", parent=styles["Normal"],
            fontSize=9, textColor=cls.COLOR_DARK,
        )
        amount_style = ParagraphStyle(
            "AmountCell", parent=styles["Normal"],
            fontSize=9, textColor=cls.COLOR_DARK, alignment=TA_RIGHT,
        )
        total_label_style = ParagraphStyle(
            "TotalLabel", parent=styles["Normal"],
            fontSize=11, fontName="Helvetica-Bold", textColor=cls.COLOR_GREEN,
        )
        total_amount_style = ParagraphStyle(
            "TotalAmount", parent=styles["Normal"],
            fontSize=11, fontName="Helvetica-Bold",
            textColor=cls.COLOR_GREEN, alignment=TA_RIGHT,
        )

        items_data = [
            [
                Paragraph("Item", header_style),
                Paragraph("Description", header_style),
                Paragraph(f"Amount ({currency})", header_style),
            ],
            [
                Paragraph("1", item_style),
                Paragraph(item_description, item_style),
                Paragraph(f"{amount:,.2f}", amount_style),
            ],
            [
                Paragraph("", item_style),
                Paragraph("<b>Total Amount Due</b>", total_label_style),
                Paragraph(f"<b>{currency} {amount:,.2f}</b>", total_amount_style),
            ],
        ]

        items_table = Table(items_data, colWidths=[15 * mm, 115 * mm, 40 * mm])
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.COLOR_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, 0), 1, cls.COLOR_GREEN),
            ("LINEBELOW", (0, 1), (-1, 1), 0.5, cls.COLOR_BORDER),
            ("BACKGROUND", (0, 2), (-1, 2), cls.COLOR_LIGHT_BG),
            ("LINEABOVE", (0, 2), (-1, 2), 1, cls.COLOR_GREEN),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 8 * mm))

        # ========== PAYMENT INFORMATION (two-column) ==========
        elements.append(Paragraph("Payment Information", s_section))

        s_bank_label = ParagraphStyle(
            "BankLabel", parent=styles["Normal"],
            fontSize=8, fontName="Helvetica-Bold",
            textColor=cls.COLOR_GRAY, leading=11,
        )
        s_bank_value = ParagraphStyle(
            "BankValue", parent=styles["Normal"],
            fontSize=9, textColor=cls.COLOR_DARK, leading=12,
            spaceBefore=1,
        )

        def _bank_cell(label, value):
            return Paragraph(
                f"<font size=8 color='#6c757d'><b>{label}</b></font><br/>{value}",
                s_bank_value,
            )

        col1 = [
            _bank_cell("Bank Name", config.get("BANK_NAME", "CRDB Bank Plc")),
            _bank_cell("Account Name", config.get("BANK_ACCOUNT_NAME", "POLLINATION AFRICA SUMMIT")),
            _bank_cell("Account Number", config.get("BANK_ACCOUNT_NUMBER", "")),
            _bank_cell("Currency", "TZS"),
        ]

        col2 = [
            _bank_cell("SWIFT Code", config.get("BANK_SWIFT", "")),
            _bank_cell("Branch Code", config.get("BANK_BRANCH_CODE", "")),
            _bank_cell("Branch Name", config.get("BANK_BRANCH", "")),
            _bank_cell("Bank Address", config.get("BANK_ADDRESS", "")),
        ]

        # Filter out empty values
        col1 = [c for c in col1 if c]
        col2 = [c for c in col2 if c]

        # Pad shorter column
        max_rows = max(len(col1), len(col2))
        col1.extend([Paragraph("", s_bank_value)] * (max_rows - len(col1)))
        col2.extend([Paragraph("", s_bank_value)] * (max_rows - len(col2)))

        bank_rows = [[col1[i], col2[i]] for i in range(max_rows)]

        bank_table = Table(bank_rows, colWidths=[85 * mm, 85 * mm])
        bank_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, -1), cls.COLOR_LIGHT_BG),
            ("LINEBELOW", (0, 0), (-1, -2), 0.5, cls.COLOR_BORDER),
            # Vertical divider between columns
            ("LINEAFTER", (0, 0), (0, -1), 0.5, cls.COLOR_BORDER),
        ]))
        elements.append(bank_table)
        elements.append(Spacer(1, 8 * mm))

        # ========== NOTES ==========
        notes = [
            "Participation will be confirmed upon receipt of payment.",
            "Travel, visa, and accommodation costs are not included.",
            "Official receipt will be issued after payment confirmation.",
            "Equivalent amount in TZS will be calculated based on prevailing exchange rate." if currency == "USD" else None,
        ]

        for note in notes:
            if note:
                elements.append(Paragraph(f"\u2022  {note}", s_normal))
                elements.append(Spacer(1, 1.5 * mm))

        elements.append(Spacer(1, 6 * mm))

        # ========== FOOTER: metadata left, powered-by right ==========
        elements.append(HRFlowable(
            width="100%", thickness=0.5, color=cls.COLOR_BORDER,
            spaceAfter=3 * mm,
        ))

        s_footer_l = ParagraphStyle(
            "InvFooterL", parent=styles["Normal"],
            fontSize=7, textColor=cls.COLOR_GRAY, alignment=TA_LEFT,
            leading=10,
        )
        s_footer_r = ParagraphStyle(
            "InvFooterR", parent=styles["Normal"],
            fontSize=7, textColor=cls.COLOR_GRAY, alignment=TA_RIGHT,
            leading=10,
        )

        meta_block = Paragraph(
            f"P.O. Box 11547 &mdash; TIN: 200-552-075 &mdash; Arusha, Tanzania<br/>"
            f"{config.get('CONTACT_EMAIL', 'info@pollination.africa')} | {config.get('WEBSITE_URL', 'www.pollination.africa')}",
            s_footer_l,
        )

        # Build powered-by block
        try:
            logo_path = Path(current_app.root_path) / "static" / "external" / "CC_logo_full.svg"
            if logo_path.exists():
                drawing = svg2rlg(str(logo_path))
                scale_factor = (20 * mm) / drawing.width
                drawing.width = 20 * mm
                drawing.height = drawing.height * scale_factor
                drawing.scale(scale_factor, scale_factor)
                powered_block = Table(
                    [
                        [Paragraph("Powered by", s_footer_r)],
                        [drawing],
                    ],
                    colWidths=[75 * mm],
                )
                powered_block.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]))
            else:
                powered_block = Paragraph(
                    "Powered by <b>Chacha Technologies</b>",
                    s_footer_r,
                )
        except Exception:
            powered_block = Paragraph(
                "Powered by <b>Chacha Technologies</b>",
                s_footer_r,
            )

        footer_table = Table(
            [[meta_block, powered_block]],
            colWidths=[95 * mm, 75 * mm],
        )
        footer_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ]))
        elements.append(footer_table)

        # Build the PDF
        doc.build(elements)

    # ============================================
    # HELPERS
    # ============================================

    @classmethod
    def _get_logo_element(cls):
        """Load the Pollination Africa logo SVG for the header."""
        try:
            logo_path = Path(current_app.root_path) / "static" / "images" / "logo.svg"
            if logo_path.exists():
                drawing = svg2rlg(str(logo_path))
                # Circular badge — scale to 18mm
                target_size = 18 * mm
                scale_factor = target_size / drawing.width
                drawing.width = target_size
                drawing.height = target_size
                drawing.scale(scale_factor, scale_factor)
                return drawing
        except Exception as e:
            logger.warning(f"Could not load logo: {str(e)}")
        return None

    @classmethod
    def _get_invoice_to_text(cls, registration) -> str:
        """Build the 'Invoice Issued To' block text."""
        lines = [f"{registration.first_name} {registration.last_name}"]

        if hasattr(registration, "organization") and registration.organization:
            lines.append(registration.organization)
        if hasattr(registration, "company_legal_name") and registration.company_legal_name:
            lines.append(registration.company_legal_name)

        lines.append(registration.email)

        phone = ""
        if registration.phone_country_code and registration.phone_number:
            phone = f"{registration.phone_country_code} {registration.phone_number}"
        elif registration.phone_number:
            phone = registration.phone_number
        if phone:
            lines.append(f"Phone: {phone}")

        if hasattr(registration, "country") and registration.country:
            lines.append(registration.country)

        return "<br/>".join(lines)

    @classmethod
    def _get_item_description(cls, registration) -> str:
        """Build the line item description."""
        reg_type = registration.registration_type

        if reg_type == "attendee":
            ticket_type = registration.ticket_type.value.replace("_", " ").title()
            desc = f"{ticket_type} Registration Fee"
            if hasattr(registration, "group_size") and registration.group_size and registration.group_size > 1:
                desc += f" (Group of {registration.group_size})"
        elif reg_type == "exhibitor":
            package_type = registration.package_type.value.replace("_", " ").title()
            desc = f"{package_type} Exhibition Package"
        else:
            desc = "Registration Fee"

        return desc

