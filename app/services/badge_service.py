"""
Enhanced Badge Generation Service for BEEASY2025
Generates PDF badges with embedded QR codes for:
- Attendees (yellow banner)
- Media Pass (orange/red banner)
- Exhibitors (green banner)
- Exhibitor Team Members (green banner with team designation)
"""

import os
import logging
import secrets
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Tuple, Optional

import qrcode
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle

from flask import current_app
from app.models import Registration, AttendeeRegistration, ExhibitorRegistration, ProfessionalCategory
from app.extensions import db

logger = logging.getLogger(__name__)


class BadgeService:
    """Service for generating event badges with QR codes"""

    # Badge dimensions (A6 = 105mm x 148mm)
    BADGE_SIZE = A6  # Portrait orientation

    # Storage configuration
    STORAGE_BASE = 'storage/badges'

    # Badge colors - Brand consistent
    COLOR_PRIMARY = colors.HexColor('#F5C342')      # Yellow/Gold - Attendee
    COLOR_SECONDARY = colors.HexColor('#5C3A21')    # Brown - Text
    COLOR_ACCENT = colors.HexColor('#2C5F2D')       # Green - Exhibitor
    COLOR_MEDIA = colors.HexColor('#DC2626')        # Red - Media Pass

    # ============================================
    # MAIN BADGE GENERATION
    # ============================================

    @classmethod
    def generate_badge(cls, registration_id: int, force_regenerate: bool = False) -> Tuple[bool, str, Optional[str]]:
        """
        Generate badge for a registration (attendee, media, or exhibitor)

        Args:
            registration_id: Registration ID
            force_regenerate: Force regenerate even if exists

        Returns:
            Tuple of (success, message, badge_url)
        """
        try:
            # Get registration
            registration = Registration.query.get(registration_id)

            if not registration:
                return False, "Registration not found", None

            # Check if already generated and not forcing regenerate
            if registration.qr_code_image_url and not force_regenerate:
                return True, "Badge already exists", registration.qr_code_image_url

            # Generate QR code data if not exists
            if not registration.qr_code_data:
                registration.qr_code_data = f"BEEASY2025-{registration.id}-{registration.reference_number}"
                db.session.commit()

            # Generate QR code image
            qr_buffer = cls._generate_qr_code(registration.qr_code_data)

            # Determine badge type and create appropriate badge
            if isinstance(registration, AttendeeRegistration):
                # Check if media pass
                if registration.professional_category == ProfessionalCategory.MEDIA:
                    success, filename = cls._create_media_pass(registration, qr_buffer)
                    badge_type = 'media'
                else:
                    success, filename = cls._create_attendee_badge(registration, qr_buffer)
                    badge_type = 'attendee'
            elif isinstance(registration, ExhibitorRegistration):
                success, filename = cls._create_exhibitor_badge(registration, qr_buffer)
                badge_type = 'exhibitor'
            else:
                return False, "Unknown registration type", None

            if not success:
                return False, f"Failed to create badge: {filename}", None

            # Generate URL path
            year = datetime.now().year
            badge_url = f"/{cls.STORAGE_BASE}/{year}/{badge_type}/{filename}"

            # Update registration with badge URL
            registration.qr_code_image_url = badge_url
            db.session.commit()

            logger.info(f"Badge generated: {registration.reference_number} (Type: {badge_type})")

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
        member_number: int = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate additional badge for exhibitor team member
        Called by admin to create team badges after registration

        Args:
            exhibitor_id: Exhibitor registration ID
            member_name: Team member full name
            member_role: Team member job title/role
            member_number: Badge number (e.g., 2 for "Badge 2 of 5")

        Returns:
            Tuple of (success, message, badge_url)
        """
        try:
            # Get exhibitor registration
            exhibitor = ExhibitorRegistration.query.get(exhibitor_id)

            if not exhibitor:
                return False, "Exhibitor registration not found", None

            # Generate unique QR code for team member
            team_id = secrets.token_hex(4).upper()
            qr_data = f"BEEASY2025-{exhibitor_id}-TEAM-{team_id}"
            qr_buffer = cls._generate_qr_code(qr_data)

            # Create team member badge
            success, filename = cls._create_team_member_badge(
                exhibitor=exhibitor,
                member_name=member_name,
                member_role=member_role,
                member_number=member_number,
                qr_buffer=qr_buffer,
                qr_data=qr_data
            )

            if not success:
                return False, f"Failed to create team badge: {filename}", None

            # Generate URL path
            year = datetime.now().year
            badge_url = f"/{cls.STORAGE_BASE}/{year}/exhibitor/{filename}"

            logger.info(f"Team badge generated for exhibitor {exhibitor.reference_number}: {member_name}")

            return True, "Team badge generated successfully", badge_url

        except Exception as e:
            logger.error(f"Error generating team badge: {str(e)}", exc_info=True)
            return False, f"Failed to generate team badge: {str(e)}", None

    # ============================================
    # QR CODE GENERATION
    # ============================================

    @classmethod
    def _generate_qr_code(cls, data: str, size: int = 300) -> BytesIO:
        """
        Generate QR code image

        Args:
            data: Data to encode in QR code
            size: Size of QR code in pixels

        Returns:
            BytesIO object containing PNG image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Save to BytesIO
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        return img_buffer

    # ============================================
    # STORAGE PATH MANAGEMENT
    # ============================================

    @classmethod
    def _get_storage_path(cls, badge_type: str, year: str = None) -> Path:
        """
        Get storage path for badges

        Args:
            badge_type: 'attendee', 'media', or 'exhibitor'
            year: Year (defaults to current year)

        Returns:
            Path object for storage directory
        """
        if year is None:
            year = datetime.now().year

        storage_path = Path(current_app.root_path) / cls.STORAGE_BASE / str(year) / badge_type
        storage_path.mkdir(parents=True, exist_ok=True)

        return storage_path

    # ============================================
    # BADGE CREATION - ATTENDEE
    # ============================================

    @classmethod
    def _create_attendee_badge(cls, attendee: AttendeeRegistration, qr_buffer: BytesIO) -> Tuple[bool, str]:
        """
        Create PDF badge for attendee

        Args:
            attendee: AttendeeRegistration object
            qr_buffer: BytesIO containing QR code image

        Returns:
            Tuple of (success, filename)
        """
        try:
            # Determine storage path and filename
            storage_path = cls._get_storage_path('attendee')
            filename = f"{attendee.reference_number}.pdf"
            full_path = storage_path / filename

            # Create PDF
            doc = SimpleDocTemplate(
                str(full_path),
                pagesize=cls.BADGE_SIZE,
                rightMargin=10 * mm,
                leftMargin=10 * mm,
                topMargin=10 * mm,
                bottomMargin=10 * mm,
            )

            elements = []
            styles = getSampleStyleSheet()

            # Custom styles
            style_title = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=3 * mm,
                fontName='Helvetica-Bold'
            )

            style_name = ParagraphStyle(
                'CustomName',
                parent=styles['Heading2'],
                fontSize=20,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=2 * mm,
                fontName='Helvetica-Bold'
            )

            style_detail = ParagraphStyle(
                'CustomDetail',
                parent=styles['Normal'],
                fontSize=10,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=1 * mm,
            )

            style_type = ParagraphStyle(
                'CustomType',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.white,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Event title
            elements.append(Paragraph("BEEASY 2025", style_title))
            elements.append(Paragraph("Bee East Africa Symposium", style_detail))
            elements.append(Spacer(1, 3 * mm))

            # Attendee type badge
            type_table = Table(
                [[Paragraph("ATTENDEE", style_type)]],
                colWidths=[80 * mm]
            )
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_PRIMARY),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(type_table)
            elements.append(Spacer(1, 5 * mm))

            # Attendee name
            full_name = f"{attendee.first_name} {attendee.last_name}"
            elements.append(Paragraph(full_name.upper(), style_name))

            # Organization
            if attendee.organization:
                elements.append(Paragraph(attendee.organization, style_detail))

            # Job title
            if attendee.job_title:
                elements.append(Paragraph(attendee.job_title, style_detail))

            elements.append(Spacer(1, 3 * mm))

            # Ticket type
            ticket_type = attendee.ticket_type.value.replace('_', ' ').title()
            elements.append(Paragraph(f"<b>{ticket_type}</b>", style_detail))

            elements.append(Spacer(1, 5 * mm))

            # QR Code
            qr_img = Image(qr_buffer, width=50 * mm, height=50 * mm)
            elements.append(qr_img)

            elements.append(Spacer(1, 2 * mm))

            # Reference number
            ref_style = ParagraphStyle(
                'RefStyle',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
            elements.append(Paragraph(attendee.reference_number, ref_style))

            # Build PDF
            doc.build(elements)

            return True, filename

        except Exception as e:
            logger.error(f"Error creating attendee badge: {str(e)}", exc_info=True)
            return False, str(e)

    # ============================================
    # BADGE CREATION - MEDIA PASS
    # ============================================

    @classmethod
    def _create_media_pass(cls, attendee: AttendeeRegistration, qr_buffer: BytesIO) -> Tuple[bool, str]:
        """
        Create PDF badge for media/press attendee

        Args:
            attendee: AttendeeRegistration object
            qr_buffer: BytesIO containing QR code image

        Returns:
            Tuple of (success, filename)
        """
        try:
            # Determine storage path and filename
            storage_path = cls._get_storage_path('media')
            filename = f"{attendee.reference_number}.pdf"
            full_path = storage_path / filename

            # Create PDF
            doc = SimpleDocTemplate(
                str(full_path),
                pagesize=cls.BADGE_SIZE,
                rightMargin=10 * mm,
                leftMargin=10 * mm,
                topMargin=10 * mm,
                bottomMargin=10 * mm,
            )

            elements = []
            styles = getSampleStyleSheet()

            # Custom styles
            style_title = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=3 * mm,
                fontName='Helvetica-Bold'
            )

            style_name = ParagraphStyle(
                'CustomName',
                parent=styles['Heading2'],
                fontSize=20,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=2 * mm,
                fontName='Helvetica-Bold'
            )

            style_detail = ParagraphStyle(
                'CustomDetail',
                parent=styles['Normal'],
                fontSize=10,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=1 * mm,
            )

            style_type = ParagraphStyle(
                'CustomType',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.white,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Event title
            elements.append(Paragraph("BEEASY 2025", style_title))
            elements.append(Paragraph("Bee East Africa Symposium", style_detail))
            elements.append(Spacer(1, 3 * mm))

            # Media pass badge (RED banner)
            type_table = Table(
                [[Paragraph("MEDIA PASS", style_type)]],
                colWidths=[80 * mm]
            )
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_MEDIA),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(type_table)
            elements.append(Spacer(1, 5 * mm))

            # Media name
            full_name = f"{attendee.first_name} {attendee.last_name}"
            elements.append(Paragraph(full_name.upper(), style_name))

            # Media organization
            if attendee.organization:
                org_style = ParagraphStyle(
                    'OrgStyle',
                    parent=styles['Normal'],
                    fontSize=12,
                    textColor=cls.COLOR_MEDIA,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Bold',
                    spaceAfter=1 * mm,
                )
                elements.append(Paragraph(attendee.organization, org_style))

            # Job title
            if attendee.job_title:
                elements.append(Paragraph(attendee.job_title, style_detail))

            elements.append(Spacer(1, 5 * mm))

            # QR Code
            qr_img = Image(qr_buffer, width=50 * mm, height=50 * mm)
            elements.append(qr_img)

            elements.append(Spacer(1, 2 * mm))

            # Reference number
            ref_style = ParagraphStyle(
                'RefStyle',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
            elements.append(Paragraph(attendee.reference_number, ref_style))

            # Build PDF
            doc.build(elements)

            return True, filename

        except Exception as e:
            logger.error(f"Error creating media pass: {str(e)}", exc_info=True)
            return False, str(e)

    # ============================================
    # BADGE CREATION - EXHIBITOR
    # ============================================

    @classmethod
    def _create_exhibitor_badge(cls, exhibitor: ExhibitorRegistration, qr_buffer: BytesIO) -> Tuple[bool, str]:
        """
        Create PDF badge for exhibitor (main contact)

        Args:
            exhibitor: ExhibitorRegistration object
            qr_buffer: BytesIO containing QR code image

        Returns:
            Tuple of (success, filename)
        """
        try:
            # Determine storage path and filename
            storage_path = cls._get_storage_path('exhibitor')
            filename = f"{exhibitor.reference_number}.pdf"
            full_path = storage_path / filename

            # Create PDF
            doc = SimpleDocTemplate(
                str(full_path),
                pagesize=cls.BADGE_SIZE,
                rightMargin=10 * mm,
                leftMargin=10 * mm,
                topMargin=10 * mm,
                bottomMargin=10 * mm,
            )

            elements = []
            styles = getSampleStyleSheet()

            # Custom styles
            style_title = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=3 * mm,
                fontName='Helvetica-Bold'
            )

            style_name = ParagraphStyle(
                'CustomName',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=2 * mm,
                fontName='Helvetica-Bold'
            )

            style_detail = ParagraphStyle(
                'CustomDetail',
                parent=styles['Normal'],
                fontSize=9,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=1 * mm,
            )

            style_type = ParagraphStyle(
                'CustomType',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.white,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Event title
            elements.append(Paragraph("BEEASY 2025", style_title))
            elements.append(Paragraph("Bee East Africa Symposium", style_detail))
            elements.append(Spacer(1, 3 * mm))

            # Exhibitor type badge (GREEN banner)
            type_table = Table(
                [[Paragraph("EXHIBITOR", style_type)]],
                colWidths=[80 * mm]
            )
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_ACCENT),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(type_table)
            elements.append(Spacer(1, 4 * mm))

            # Contact person name
            full_name = f"{exhibitor.first_name} {exhibitor.last_name}"
            elements.append(Paragraph(full_name.upper(), style_name))

            # Job title
            if exhibitor.job_title:
                elements.append(Paragraph(exhibitor.job_title, style_detail))

            elements.append(Spacer(1, 2 * mm))

            # Company name (prominent)
            company_style = ParagraphStyle(
                'CompanyStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=cls.COLOR_PRIMARY,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=1 * mm,
            )
            elements.append(Paragraph(exhibitor.company_legal_name.upper(), company_style))

            # Booth number (if assigned)
            if exhibitor.booth_number:
                booth_style = ParagraphStyle(
                    'BoothStyle',
                    parent=styles['Normal'],
                    fontSize=11,
                    textColor=cls.COLOR_SECONDARY,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Bold',
                )
                elements.append(Paragraph(f"BOOTH: {exhibitor.booth_number}", booth_style))

            elements.append(Spacer(1, 4 * mm))

            # QR Code
            qr_img = Image(qr_buffer, width=45 * mm, height=45 * mm)
            elements.append(qr_img)

            elements.append(Spacer(1, 2 * mm))

            # Reference number
            ref_style = ParagraphStyle(
                'RefStyle',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
            elements.append(Paragraph(exhibitor.reference_number, ref_style))

            # Build PDF
            doc.build(elements)

            return True, filename

        except Exception as e:
            logger.error(f"Error creating exhibitor badge: {str(e)}", exc_info=True)
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
        qr_data: str
    ) -> Tuple[bool, str]:
        """
        Create PDF badge for exhibitor team member

        Args:
            exhibitor: ExhibitorRegistration object (parent)
            member_name: Team member full name
            member_role: Team member job title/role
            member_number: Badge number (optional)
            qr_buffer: BytesIO containing QR code image
            qr_data: QR code data string

        Returns:
            Tuple of (success, filename)
        """
        try:
            # Determine storage path and filename
            storage_path = cls._get_storage_path('exhibitor')
            team_id = qr_data.split('-')[-1]  # Extract unique ID
            filename = f"{exhibitor.reference_number}-team-{team_id}.pdf"
            full_path = storage_path / filename

            # Create PDF
            doc = SimpleDocTemplate(
                str(full_path),
                pagesize=cls.BADGE_SIZE,
                rightMargin=10 * mm,
                leftMargin=10 * mm,
                topMargin=10 * mm,
                bottomMargin=10 * mm,
            )

            elements = []
            styles = getSampleStyleSheet()

            # Custom styles (similar to exhibitor)
            style_title = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=3 * mm,
                fontName='Helvetica-Bold'
            )

            style_name = ParagraphStyle(
                'CustomName',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=2 * mm,
                fontName='Helvetica-Bold'
            )

            style_detail = ParagraphStyle(
                'CustomDetail',
                parent=styles['Normal'],
                fontSize=9,
                textColor=cls.COLOR_SECONDARY,
                alignment=TA_CENTER,
                spaceAfter=1 * mm,
            )

            style_type = ParagraphStyle(
                'CustomType',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.white,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Event title
            elements.append(Paragraph("BEEASY 2025", style_title))
            elements.append(Paragraph("Bee East Africa Symposium", style_detail))
            elements.append(Spacer(1, 3 * mm))

            # Exhibitor type badge (GREEN banner)
            type_table = Table(
                [[Paragraph("EXHIBITOR", style_type)]],
                colWidths=[80 * mm]
            )
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_ACCENT),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(type_table)
            elements.append(Spacer(1, 4 * mm))

            # Team member name
            elements.append(Paragraph(member_name.upper(), style_name))

            # Team member role
            if member_role:
                elements.append(Paragraph(member_role, style_detail))

            elements.append(Spacer(1, 2 * mm))

            # Company name (prominent)
            company_style = ParagraphStyle(
                'CompanyStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=cls.COLOR_PRIMARY,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=1 * mm,
            )
            elements.append(Paragraph(exhibitor.company_legal_name.upper(), company_style))

            # Booth number and badge number
            booth_info = []
            if exhibitor.booth_number:
                booth_info.append(f"BOOTH: {exhibitor.booth_number}")

            if member_number and exhibitor.exhibitor_badges_needed:
                booth_info.append(f"Badge {member_number} of {exhibitor.exhibitor_badges_needed}")

            if booth_info:
                booth_style = ParagraphStyle(
                    'BoothStyle',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=cls.COLOR_SECONDARY,
                    alignment=TA_CENTER,
                )
                elements.append(Paragraph(" | ".join(booth_info), booth_style))

            elements.append(Spacer(1, 4 * mm))

            # QR Code
            qr_img = Image(qr_buffer, width=45 * mm, height=45 * mm)
            elements.append(qr_img)

            elements.append(Spacer(1, 2 * mm))

            # Team badge identifier
            ref_style = ParagraphStyle(
                'RefStyle',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
            elements.append(Paragraph(f"{exhibitor.reference_number} - TEAM", ref_style))

            # Build PDF
            doc.build(elements)

            return True, filename

        except Exception as e:
            logger.error(f"Error creating team member badge: {str(e)}", exc_info=True)
            return False, str(e)

    # ============================================
    # QR CODE VERIFICATION & CHECK-IN
    # ============================================

    @classmethod
    def verify_qr_code(cls, qr_data: str) -> Tuple[bool, str, Optional[Registration]]:
        """
        Verify and decode QR code data for check-in

        Args:
            qr_data: Scanned QR code data

        Returns:
            Tuple of (valid, message, registration)
        """
        try:
            # Expected format: BEEASY2025-{id}-{reference_number}
            # Or for team: BEEASY2025-{exhibitor_id}-TEAM-{unique_id}
            if not qr_data.startswith('BEEASY2025-'):
                return False, "Invalid QR code format", None

            parts = qr_data.split('-')

            if len(parts) < 3:
                return False, "Invalid QR code format", None

            # Check if it's a team badge
            if len(parts) >= 4 and parts[2] == 'TEAM':
                exhibitor_id = parts[1]
                registration = Registration.query.filter_by(
                    id=int(exhibitor_id),
                    is_deleted=False
                ).first()

                if not registration:
                    return False, "Exhibitor registration not found", None

                # Team badges are valid for check-in
                return True, f"Valid team badge for {registration.computed_full_name}", registration

            # Regular badge - extract reference number
            reference_number = '-'.join(parts[2:])

            # Find registration
            registration = Registration.query.filter_by(
                reference_number=reference_number,
                is_deleted=False
            ).first()

            if not registration:
                return False, "Registration not found", None

            # Verify QR data matches
            if registration.qr_code_data != qr_data:
                return False, "QR code mismatch", None

            # Check registration status
            from app.models.registration_models import RegistrationStatus

            if registration.status != RegistrationStatus.CONFIRMED:
                return False, f"Registration not confirmed (Status: {registration.status.value})", registration

            # Check payment
            if not registration.is_fully_paid():
                return False, "Payment incomplete", registration

            return True, "Valid registration", registration

        except Exception as e:
            logger.error(f"Error verifying QR code: {str(e)}", exc_info=True)
            return False, f"Verification error: {str(e)}", None

    @classmethod
    def check_in_attendee(cls, qr_data: str, checked_in_by: str) -> Tuple[bool, str, Optional[Registration]]:
        """
        Check in attendee/exhibitor using QR code

        Args:
            qr_data: Scanned QR code data
            checked_in_by: User/staff who performed check-in

        Returns:
            Tuple of (success, message, registration)
        """
        # Verify QR code
        valid, message, registration = cls.verify_qr_code(qr_data)

        if not valid:
            return False, message, registration

        # Check if already checked in (attendees only)
        if isinstance(registration, AttendeeRegistration):
            if registration.checked_in:
                return False, f"Already checked in at {registration.checked_in_at.strftime('%H:%M')}", registration

            # Perform check-in
            registration.check_in(checked_in_by)
            db.session.commit()

            logger.info(f"Attendee checked in: {registration.reference_number}")

            return True, f"Welcome, {registration.first_name}!", registration

        elif isinstance(registration, ExhibitorRegistration):
            # Exhibitors - just confirm valid badge
            return True, f"Welcome, {registration.first_name} from {registration.company_legal_name}", registration

        return True, "Check-in successful", registration
