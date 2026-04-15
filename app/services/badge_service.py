"""
Enhanced Badge Generation Service for Pollination Africa 2026
Generates PDF badges with embedded QR codes for:
- Attendees (yellow banner)
- Media Pass (red banner)
- Exhibitors (green banner)
- Exhibitor Team Members (green banner with team designation)
"""

import logging
import secrets
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import qrcode
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A6
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from svglib.svglib import svg2rlg

from app.extensions import db
from app.models import (
    AttendeeRegistration,
    ExhibitorRegistration,
    ProfessionalCategory,
    Registration,
    RegistrationStatus,
)

logger = logging.getLogger(__name__)


class BadgeService:
    """Service for generating event badges with QR codes"""

    # Badge dimensions (A6 = 105mm x 148mm portrait)
    BADGE_SIZE = A6
    STORAGE_BASE = "storage/badges"

    # Content width: A6 105mm - 10mm left - 10mm right margins
    CONTENT_WIDTH = 85 * mm

    # Brand colors
    COLOR_PRIMARY_DARK   = colors.HexColor("#142601")
    COLOR_PRIMARY_MEDIUM = colors.HexColor("#25400a")
    COLOR_ACCENT_YELLOW  = colors.HexColor("#f2c12e")
    COLOR_ACCENT_ORANGE  = colors.HexColor("#bf7e04")
    COLOR_ACCENT_BROWN   = colors.HexColor("#8c5c03")
    COLOR_MEDIA          = colors.HexColor("#DC2626")

    # ============================================
    # MAIN BADGE GENERATION
    # ============================================

    @classmethod
    def generate_badge(
        cls, registration_id: int, force_regenerate: bool = False
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate badge for a registration (attendee, media, or exhibitor).

        Returns:
            Tuple of (success, message, badge_url)
        """
        try:
            registration = Registration.query.get(registration_id)
            if not registration:
                return False, "Registration not found", None

            if registration.qr_code_image_url and not force_regenerate:
                return True, "Badge already exists", registration.qr_code_image_url

            if not registration.qr_code_data:
                registration.qr_code_data = (
                    f"POLLINATION2026-{registration.id}-{registration.reference_number}"
                )
                db.session.commit()

            qr_buffer = cls._generate_qr_code(registration.qr_code_data)

            if isinstance(registration, AttendeeRegistration):
                if (
                    registration.professional_category
                    == ProfessionalCategory.MEDIA_JOURNALIST
                ):
                    success, filename = cls._create_media_pass(registration, qr_buffer)
                    badge_type = "media"
                else:
                    success, filename = cls._create_attendee_badge(registration, qr_buffer)
                    badge_type = "attendee"
            elif isinstance(registration, ExhibitorRegistration):
                success, filename = cls._create_exhibitor_badge(registration, qr_buffer)
                badge_type = "exhibitor"
            else:
                return False, "Unknown registration type", None

            if not success:
                return False, f"Failed to create badge: {filename}", None

            year = datetime.now().year
            badge_url = f"/{cls.STORAGE_BASE}/{year}/{badge_type}/{filename}"
            registration.qr_code_image_url = badge_url
            db.session.commit()

            logger.info(
                f"Badge generated: {registration.reference_number} (Type: {badge_type})"
            )
            return True, "Badge generated successfully", badge_url

        except Exception as e:
            logger.error(f"Error generating badge: {str(e)}", exc_info=True)
            db.session.rollback()
            return False, f"Failed to generate badge: {str(e)}", None

    @classmethod
    def generate_team_badge(
        cls,
        exhibitor_id: int,
        member_name: str,
        member_role: str = "Team Member",
        member_number: int = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate additional badge for exhibitor team member.

        Returns:
            Tuple of (success, message, badge_url)
        """
        try:
            exhibitor = ExhibitorRegistration.query.get(exhibitor_id)
            if not exhibitor:
                return False, "Exhibitor registration not found", None

            team_id = secrets.token_hex(4).upper()
            qr_data = f"POLLINATION2026-{exhibitor_id}-TEAM-{team_id}"
            qr_buffer = cls._generate_qr_code(qr_data)

            success, filename = cls._create_team_member_badge(
                exhibitor=exhibitor,
                member_name=member_name,
                member_role=member_role,
                member_number=member_number,
                qr_buffer=qr_buffer,
                qr_data=qr_data,
            )

            if not success:
                return False, f"Failed to create team badge: {filename}", None

            year = datetime.now().year
            badge_url = f"/{cls.STORAGE_BASE}/{year}/exhibitor/{filename}"
            logger.info(
                f"Team badge generated for exhibitor {exhibitor.reference_number}: {member_name}"
            )
            return True, "Team badge generated successfully", badge_url

        except Exception as e:
            logger.error(f"Error generating team badge: {str(e)}", exc_info=True)
            return False, f"Failed to generate team badge: {str(e)}", None

    # ============================================
    # QR CODE GENERATION
    # ============================================

    @classmethod
    def _generate_qr_code(cls, data: str, size: int = 300) -> BytesIO:
        """Generate QR code image as a PNG in a BytesIO buffer."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    # ============================================
    # SHARED DESIGN HELPERS
    # ============================================

    @classmethod
    def _get_logo_element(cls, size_mm: float = 20):
        """
        Load the circular Pollination Africa logo SVG scaled to size_mm.
        Returns a ReportLab Drawing or None if unavailable.
        """
        try:
            logo_path = (
                Path(current_app.root_path) / "static" / "images" / "logo.svg"
            )
            if logo_path.exists():
                drawing = svg2rlg(str(logo_path))
                target = size_mm * mm
                scale = target / drawing.width
                drawing.width = target
                drawing.height = target
                drawing.scale(scale, scale)
                return drawing
        except Exception as e:
            logger.warning(f"Could not load badge logo: {e}")
        return None

    @classmethod
    def _build_header_band(cls, styles) -> Table:
        """
        Dark-green header band: circular logo (14mm) on the left,
        event name and date/location in white on the right.
        Measured height: ~19mm (logo 14mm + 2.5mm padding top/bottom).
        """
        logo = cls._get_logo_element(size_mm=14)

        s_name = ParagraphStyle(
            "HdrName",
            parent=styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            leading=11,
        )
        s_detail = ParagraphStyle(
            "HdrDetail",
            parent=styles["Normal"],
            fontSize=7,
            textColor=colors.HexColor("#c8e6c9"),
            leading=9,
            spaceBefore=1 * mm,
        )

        text_cell = [
            Paragraph("POLLINATION AFRICA", s_name),
            Paragraph("SUMMIT 2026", s_name),
            Paragraph("Arusha, Tanzania  •  June 3–5", s_detail),
        ]

        if logo:
            cell_data = [[logo, text_cell]]
            col_widths = [18 * mm, 67 * mm]
        else:
            cell_data = [[text_cell]]
            col_widths = [cls.CONTENT_WIDTH]

        table = Table(cell_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), cls.COLOR_PRIMARY_DARK),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (0, 0), (0, -1),  "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("LEFTPADDING",   (0, 0), (0, -1),  2 * mm),
            ("LEFTPADDING",   (1, 0), (1, -1),  3 * mm),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 2 * mm),
        ]))
        return table

    @classmethod
    def _build_type_banner(
        cls, label: str, banner_color, sub_label: str = None
    ) -> Table:
        """
        Colored type banner (ATTENDEE / MEDIA PASS / EXHIBITOR) spanning
        full content width. Optional sub_label shown below in smaller italic.
        """
        styles = getSampleStyleSheet()

        # font=11pt, leading=13 → 2-line para = 2×13pt=26pt=9.2mm + 2.5mm pad×2 = ~14mm
        if sub_label:
            markup = (
                f'<b>{label}</b>'
                f'<br/><font size="7"><i>{sub_label}</i></font>'
            )
        else:
            markup = f'<b>{label}</b>'

        s_banner = ParagraphStyle(
            "BannerText",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.white,
            alignment=TA_CENTER,
            leading=13,
        )

        table = Table(
            [[Paragraph(markup, s_banner)]],
            colWidths=[cls.CONTENT_WIDTH],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), banner_color),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ]))
        return table

    @classmethod
    def _build_name_block(
        cls,
        elements: list,
        styles,
        name: str,
        org: str = None,
        title: str = None,
        name_size: int = 20,
    ) -> None:
        """Append name / org / title paragraphs to elements list."""
        # name leading = name_size+3 → single line height = leading pt
        # org 9pt leading 11 + 0.5mm after; title 8pt leading 10
        s_name = ParagraphStyle(
            "BadgeName",
            parent=styles["Normal"],
            fontSize=name_size,
            fontName="Helvetica-Bold",
            textColor=cls.COLOR_PRIMARY_DARK,
            alignment=TA_CENTER,
            leading=name_size + 3,
            spaceAfter=1.5 * mm,
        )
        s_org = ParagraphStyle(
            "BadgeOrg",
            parent=styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=cls.COLOR_ACCENT_ORANGE,
            alignment=TA_CENTER,
            leading=11,
            spaceAfter=0.5 * mm,
        )
        s_title = ParagraphStyle(
            "BadgeTitle",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#555555"),
            alignment=TA_CENTER,
            leading=10,
        )

        elements.append(Paragraph(name.upper(), s_name))
        if org:
            elements.append(Paragraph(org, s_org))
        if title:
            elements.append(Paragraph(title, s_title))

    @classmethod
    def _build_qr_section(
        cls,
        elements: list,
        styles,
        qr_buffer: BytesIO,
        reference: str,
        qr_size_mm: float = 45,
    ) -> None:
        """Append a centered QR code image and reference number to elements."""
        qr_img = Image(qr_buffer, width=qr_size_mm * mm, height=qr_size_mm * mm)

        qr_table = Table([[qr_img]], colWidths=[cls.CONTENT_WIDTH])
        qr_table.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))
        elements.append(qr_table)
        elements.append(Spacer(1, 2 * mm))

        s_ref = ParagraphStyle(
            "RefStyle",
            parent=styles["Normal"],
            fontSize=7,
            textColor=colors.HexColor("#888888"),
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(reference, s_ref))

    @classmethod
    def _build_footer(cls, elements: list, styles) -> None:
        """
        Thin divider + 'Powered by' + CC logo.
        Measured total: ~8mm (spacer 1.5mm + HR 0.7mm + text 2mm + logo ~4mm).
        """
        elements.append(Spacer(1, 1.5 * mm))
        elements.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor("#cccccc"),
            spaceBefore=0,
            spaceAfter=0.5 * mm,
        ))

        s_powered = ParagraphStyle(
            "PoweredBy",
            parent=styles["Normal"],
            fontSize=5,
            textColor=colors.HexColor("#aaaaaa"),
            alignment=TA_CENTER,
            spaceAfter=0.5 * mm,
        )
        elements.append(Paragraph("Powered by", s_powered))

        try:
            logo_path = (
                Path(current_app.root_path)
                / "static" / "external" / "CC_logo_full.svg"
            )
            if logo_path.exists():
                drawing = svg2rlg(str(logo_path))
                target_w = 18 * mm
                scale = target_w / drawing.width
                drawing.width = target_w
                drawing.height = drawing.height * scale
                drawing.scale(scale, scale)

                logo_table = Table([[drawing]], colWidths=[cls.CONTENT_WIDTH])
                logo_table.setStyle(TableStyle([
                    ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING",    (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                elements.append(logo_table)
                return
        except Exception as e:
            logger.warning(f"Could not load CC logo for badge footer: {e}")

        # Fallback to text
        s_cc = ParagraphStyle(
            "CCText",
            parent=styles["Normal"],
            fontSize=5,
            textColor=colors.HexColor("#3db54a"),
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )
        elements.append(Paragraph("Chacha Technologies", s_cc))

    # ============================================
    # STORAGE PATH MANAGEMENT
    # ============================================

    @classmethod
    def _get_storage_path(cls, badge_type: str, year: str = None) -> Path:
        if year is None:
            year = datetime.now().year
        storage_path = (
            Path(current_app.root_path) / cls.STORAGE_BASE / str(year) / badge_type
        )
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    # ============================================
    # BADGE CREATION - ATTENDEE
    # ============================================

    @classmethod
    def _create_attendee_badge(
        cls, attendee: AttendeeRegistration, qr_buffer: BytesIO
    ) -> Tuple[bool, str]:
        try:
            storage_path = cls._get_storage_path("attendee")
            filename = f"{attendee.reference_number}.pdf"
            full_path = storage_path / filename

            doc = SimpleDocTemplate(
                str(full_path), pagesize=cls.BADGE_SIZE,
                rightMargin=10*mm, leftMargin=10*mm,
                topMargin=10*mm, bottomMargin=10*mm,
            )
            elements = []
            styles = getSampleStyleSheet()

            # Header band (~19mm)
            elements.append(cls._build_header_band(styles))
            elements.append(Spacer(1, 1.5 * mm))

            # Type banner (~14mm) — yellow, ticket type as sub-label
            ticket_label = attendee.ticket_type.value.replace("_", " ").title()
            elements.append(
                cls._build_type_banner(
                    "ATTENDEE", cls.COLOR_ACCENT_YELLOW, sub_label=ticket_label
                )
            )
            elements.append(Spacer(1, 3 * mm))

            # Name / org / title (~16mm)
            cls._build_name_block(
                elements, styles,
                name=f"{attendee.first_name} {attendee.last_name}",
                org=attendee.organization,
                title=attendee.job_title,
                name_size=16,
            )
            elements.append(Spacer(1, 3 * mm))

            # QR code + reference (38mm)
            cls._build_qr_section(
                elements, styles, qr_buffer, attendee.reference_number, qr_size_mm=38
            )

            # Footer
            cls._build_footer(elements, styles)

            doc.build(elements)
            return True, filename

        except Exception as e:
            logger.error(f"Error creating attendee badge: {e}", exc_info=True)
            return False, str(e)

    # ============================================
    # BADGE CREATION - MEDIA PASS
    # ============================================

    @classmethod
    def _create_media_pass(
        cls, attendee: AttendeeRegistration, qr_buffer: BytesIO
    ) -> Tuple[bool, str]:
        try:
            storage_path = cls._get_storage_path("media")
            filename = f"{attendee.reference_number}.pdf"
            full_path = storage_path / filename

            doc = SimpleDocTemplate(
                str(full_path), pagesize=cls.BADGE_SIZE,
                rightMargin=10*mm, leftMargin=10*mm,
                topMargin=10*mm, bottomMargin=10*mm,
            )
            elements = []
            styles = getSampleStyleSheet()

            # Header band (~19mm)
            elements.append(cls._build_header_band(styles))
            elements.append(Spacer(1, 1.5 * mm))

            # Type banner (~14mm) — red, media outlet as sub-label
            sub = attendee.organization or "Press"
            elements.append(
                cls._build_type_banner("MEDIA PASS", cls.COLOR_MEDIA, sub_label=sub)
            )
            elements.append(Spacer(1, 3 * mm))

            # Name / org / title (~16mm)
            cls._build_name_block(
                elements, styles,
                name=f"{attendee.first_name} {attendee.last_name}",
                org=attendee.organization,
                title=attendee.job_title,
                name_size=16,
            )
            elements.append(Spacer(1, 3 * mm))

            # QR code + reference (38mm)
            cls._build_qr_section(
                elements, styles, qr_buffer, attendee.reference_number, qr_size_mm=38
            )

            # Footer
            cls._build_footer(elements, styles)

            doc.build(elements)
            return True, filename

        except Exception as e:
            logger.error(f"Error creating media pass: {e}", exc_info=True)
            return False, str(e)

    # ============================================
    # BADGE CREATION - EXHIBITOR
    # ============================================

    @classmethod
    def _create_exhibitor_badge(
        cls, exhibitor: ExhibitorRegistration, qr_buffer: BytesIO
    ) -> Tuple[bool, str]:
        try:
            storage_path = cls._get_storage_path("exhibitor")
            filename = f"{exhibitor.reference_number}.pdf"
            full_path = storage_path / filename

            doc = SimpleDocTemplate(
                str(full_path), pagesize=cls.BADGE_SIZE,
                rightMargin=10*mm, leftMargin=10*mm,
                topMargin=10*mm, bottomMargin=10*mm,
            )
            elements = []
            styles = getSampleStyleSheet()

            # Header band (~19mm)
            elements.append(cls._build_header_band(styles))
            elements.append(Spacer(1, 1.5 * mm))

            # Type banner (~14mm) — dark green, booth number as sub-label
            sub = f"Booth {exhibitor.booth_number}" if exhibitor.booth_number else "Exhibitor"
            elements.append(
                cls._build_type_banner(
                    "EXHIBITOR", cls.COLOR_PRIMARY_MEDIUM, sub_label=sub
                )
            )
            elements.append(Spacer(1, 3 * mm))

            # Name / company / title (~16mm)
            cls._build_name_block(
                elements, styles,
                name=f"{exhibitor.first_name} {exhibitor.last_name}",
                org=exhibitor.company_legal_name,
                title=exhibitor.job_title,
                name_size=15,
            )
            elements.append(Spacer(1, 3 * mm))

            # QR code + reference (36mm)
            cls._build_qr_section(
                elements, styles, qr_buffer, exhibitor.reference_number, qr_size_mm=36
            )

            # Footer
            cls._build_footer(elements, styles)

            doc.build(elements)
            return True, filename

        except Exception as e:
            logger.error(f"Error creating exhibitor badge: {e}", exc_info=True)
            return False, str(e)

    # ============================================
    # BADGE CREATION - TEAM MEMBER
    # ============================================

    @classmethod
    def _create_team_member_badge(
        cls,
        exhibitor: ExhibitorRegistration,
        member_name: str,
        member_role: str,
        member_number: Optional[int],
        qr_buffer: BytesIO,
        qr_data: str,
    ) -> Tuple[bool, str]:
        try:
            storage_path = cls._get_storage_path("exhibitor")
            team_id = qr_data.split("-")[-1]
            filename = f"{exhibitor.reference_number}-team-{team_id}.pdf"
            full_path = storage_path / filename

            doc = SimpleDocTemplate(
                str(full_path), pagesize=cls.BADGE_SIZE,
                rightMargin=10*mm, leftMargin=10*mm,
                topMargin=10*mm, bottomMargin=10*mm,
            )
            elements = []
            styles = getSampleStyleSheet()

            # Header band (~19mm)
            elements.append(cls._build_header_band(styles))
            elements.append(Spacer(1, 1.5 * mm))

            # Type banner (~14mm) — dark green, booth / badge number as sub-label
            sub_parts = []
            if exhibitor.booth_number:
                sub_parts.append(f"Booth {exhibitor.booth_number}")
            if member_number and exhibitor.exhibitor_badges_needed:
                sub_parts.append(
                    f"Badge {member_number} of {exhibitor.exhibitor_badges_needed}"
                )
            sub = "  |  ".join(sub_parts) if sub_parts else "Team Member"
            elements.append(
                cls._build_type_banner(
                    "EXHIBITOR", cls.COLOR_PRIMARY_MEDIUM, sub_label=sub
                )
            )
            elements.append(Spacer(1, 3 * mm))

            # Name / company / role (~16mm)
            cls._build_name_block(
                elements, styles,
                name=member_name,
                org=exhibitor.company_legal_name,
                title=member_role,
                name_size=15,
            )
            elements.append(Spacer(1, 3 * mm))

            # QR code + reference (36mm)
            cls._build_qr_section(
                elements, styles, qr_buffer,
                f"{exhibitor.reference_number} — TEAM",
                qr_size_mm=36,
            )

            # Footer
            cls._build_footer(elements, styles)

            doc.build(elements)
            return True, filename

        except Exception as e:
            logger.error(f"Error creating team member badge: {e}", exc_info=True)
            return False, str(e)

    # ============================================
    # QR CODE VERIFICATION & CHECK-IN
    # ============================================

    @classmethod
    def verify_qr_code(cls, qr_data: str) -> Tuple[bool, str, Optional[Registration]]:
        """
        Verify and decode QR code data for check-in.

        Returns:
            Tuple of (valid, message, registration)
        """
        try:
            # Expected format: POLLINATION2026-{id}-{reference_number}
            # Team format:     POLLINATION2026-{exhibitor_id}-TEAM-{unique_id}
            # Legacy support:  BEEASY2025-...
            if not (
                qr_data.startswith("POLLINATION2026-")
                or qr_data.startswith("BEEASY2025-")
            ):
                return False, "Invalid QR code format", None

            parts = qr_data.split("-")
            if len(parts) < 3:
                return False, "Invalid QR code format", None

            # Team badge
            if len(parts) >= 4 and parts[2] == "TEAM":
                exhibitor_id = parts[1]
                registration = Registration.query.filter_by(
                    id=int(exhibitor_id), is_deleted=False
                ).first()
                if not registration:
                    return False, "Exhibitor registration not found", None
                return (
                    True,
                    f"Valid team badge for {registration.computed_full_name}",
                    registration,
                )

            # Regular badge
            reference_number = "-".join(parts[2:])
            registration = Registration.query.filter_by(
                reference_number=reference_number, is_deleted=False
            ).first()

            if not registration:
                return False, "Registration not found", None

            if registration.qr_code_data != qr_data:
                return False, "QR code mismatch", None

            if registration.status != RegistrationStatus.CONFIRMED:
                return (
                    False,
                    f"Registration not confirmed (Status: {registration.status.value})",
                    registration,
                )

            if not registration.is_fully_paid():
                return False, "Payment incomplete", registration

            return True, "Valid registration", registration

        except Exception as e:
            logger.error(f"Error verifying QR code: {str(e)}", exc_info=True)
            return False, f"Verification error: {str(e)}", None

    @classmethod
    def check_in_attendee(
        cls, qr_data: str, checked_in_by: str
    ) -> Tuple[bool, str, Optional[Registration]]:
        """
        Check in attendee/exhibitor using QR code for today.

        Returns:
            Tuple of (success, message, registration)
        """
        from datetime import date

        valid, message, registration = cls.verify_qr_code(qr_data)
        if not valid:
            return False, message, registration

        today = date.today()

        if isinstance(registration, AttendeeRegistration):
            if registration.is_checked_in_for_day(today):
                todays_checkin = next(
                    (c for c in registration.daily_checkins if c.event_date == today),
                    None,
                )
                checkin_time = (
                    todays_checkin.checked_in_at.strftime("%H:%M")
                    if todays_checkin
                    else "earlier"
                )
                return (
                    False,
                    f"Already checked in today at {checkin_time}",
                    registration,
                )

            registration.check_in_for_day(
                event_date=today,
                checked_in_by=checked_in_by,
                check_in_method="qr_code",
            )
            db.session.commit()
            logger.info(
                f"Attendee checked in: {registration.reference_number} for {today}"
            )
            return True, f"Welcome, {registration.first_name}!", registration

        elif isinstance(registration, ExhibitorRegistration):
            if not registration.is_checked_in_for_day(today):
                registration.check_in_for_day(
                    event_date=today,
                    checked_in_by=checked_in_by,
                    check_in_method="qr_code",
                )
                db.session.commit()
                logger.info(
                    f"Exhibitor checked in: {registration.reference_number} for {today}"
                )
            return (
                True,
                f"Welcome, {registration.first_name} from {registration.company_legal_name}",
                registration,
            )

        return True, "Check-in successful", registration
