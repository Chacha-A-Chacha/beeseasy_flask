"""
Model Utilities and Helper Functions for BEEASY2025 Registration System

Provides:
- Query helpers and filters
- Reporting utilities
- Data export functions
- Statistical analysis helpers
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, and_, or_, case, extract
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    Registration, AttendeeRegistration, ExhibitorRegistration,
    RegistrationStatus, AttendeeTicketType, ExhibitorPackage,
    ProfessionalCategory, IndustryCategory
)
from app.models import Payment, PaymentStatus, PaymentMethod


# ============================================
# QUERY HELPERS
# ============================================

class RegistrationQueries:
    """Helper class for common registration queries"""

    @staticmethod
    def get_by_reference(reference_number: str) -> Optional[Registration]:
        """Get registration by reference number"""
        return (Registration.query
                .filter_by(reference_number=reference_number, is_deleted=False)
                .first())

    @staticmethod
    def get_by_email(email: str, registration_type: str = None) -> Optional[Registration]:
        """Get registration by email, optionally filtered by type"""
        query = Registration.query.filter_by(
            email=email.lower(),
            is_deleted=False
        )

        if registration_type:
            query = query.filter_by(registration_type=registration_type)

        return query.first()

    @staticmethod
    def get_confirmed_registrations(
            registration_type: str = None,
            start_date: datetime = None,
            end_date: datetime = None
    ) -> List[Registration]:
        """Get all confirmed registrations with optional filters"""
        query = (Registration.query
                 .filter_by(status=RegistrationStatus.CONFIRMED, is_deleted=False)
                 .options(joinedload(Registration.payments)))

        if registration_type:
            query = query.filter_by(registration_type=registration_type)

        if start_date:
            query = query.filter(Registration.confirmed_at >= start_date)

        if end_date:
            query = query.filter(Registration.confirmed_at <= end_date)

        return query.order_by(Registration.confirmed_at.desc()).all()

    @staticmethod
    def get_pending_payments(days_overdue: int = 0) -> List[Registration]:
        """Get registrations with pending payments"""
        query = (Registration.query
        .join(Payment)
        .filter(
            Registration.is_deleted == False,
            Registration.status.in_([
                RegistrationStatus.PENDING,
                RegistrationStatus.PAYMENT_PENDING
            ]),
            Payment.payment_status.in_([
                PaymentStatus.PENDING,
                PaymentStatus.PROCESSING
            ])
        ))

        if days_overdue > 0:
            cutoff_date = datetime.utcnow() - timedelta(days=days_overdue)
            query = query.filter(Payment.payment_due_date < cutoff_date)

        return query.all()

    @staticmethod
    def search_registrations(
            search_term: str,
            registration_type: str = None,
            status: RegistrationStatus = None
    ) -> List[Registration]:
        """Search registrations by name, email, or reference number"""
        search_pattern = f"%{search_term.lower()}%"

        query = Registration.query.filter(
            Registration.is_deleted == False,
            or_(
                func.lower(Registration.first_name).like(search_pattern),
                func.lower(Registration.last_name).like(search_pattern),
                func.lower(Registration.email).like(search_pattern),
                func.lower(Registration.reference_number).like(search_pattern),
                func.lower(Registration.organization).like(search_pattern)
            )
        )

        if registration_type:
            query = query.filter_by(registration_type=registration_type)

        if status:
            query = query.filter_by(status=status)

        return query.limit(50).all()


class AttendeeQueries:
    """Helper class for attendee-specific queries"""

    @staticmethod
    def get_by_ticket_type(ticket_type: AttendeeTicketType) -> List[AttendeeRegistration]:
        """Get all attendees by ticket type"""
        return (AttendeeRegistration.query
                .filter_by(ticket_type=ticket_type, is_deleted=False)
                .options(joinedload(AttendeeRegistration.ticket_price))
                .all())

    @staticmethod
    def get_checked_in_attendees() -> List[AttendeeRegistration]:
        """Get all checked-in attendees"""
        return (AttendeeRegistration.query
                .filter_by(checked_in=True, is_deleted=False)
                .order_by(AttendeeRegistration.checked_in_at.desc())
                .all())

    @staticmethod
    def get_by_professional_category(
            category: ProfessionalCategory
    ) -> List[AttendeeRegistration]:
        """Get attendees by professional category"""
        return (AttendeeRegistration.query
                .filter_by(professional_category=category, is_deleted=False)
                .all())

    @staticmethod
    def get_dietary_requirements_summary() -> Dict[str, int]:
        """Get summary of dietary requirements"""
        results = (db.session.query(
            AttendeeRegistration.dietary_requirement,
            func.count(AttendeeRegistration.id)
        )
                   .filter(AttendeeRegistration.is_deleted == False)
                   .group_by(AttendeeRegistration.dietary_requirement)
                   .all())

        return {str(req.value): count for req, count in results if req}


class ExhibitorQueries:
    """Helper class for exhibitor-specific queries"""

    @staticmethod
    def get_by_package(package_type: ExhibitorPackage) -> List[ExhibitorRegistration]:
        """Get exhibitors by package type"""
        return (ExhibitorRegistration.query
                .filter_by(package_type=package_type, is_deleted=False)
                .options(joinedload(ExhibitorRegistration.package_price))
                .all())

    @staticmethod
    def get_booth_assignments() -> List[ExhibitorRegistration]:
        """Get all exhibitors with booth assignments"""
        return (ExhibitorRegistration.query
                .filter(
            ExhibitorRegistration.booth_assigned == True,
            ExhibitorRegistration.is_deleted == False
        )
                .order_by(ExhibitorRegistration.booth_number)
                .all())

    @staticmethod
    def get_pending_booth_assignments() -> List[ExhibitorRegistration]:
        """Get exhibitors awaiting booth assignment"""
        return (ExhibitorRegistration.query
                .filter(
            ExhibitorRegistration.booth_assigned == False,
            ExhibitorRegistration.status == RegistrationStatus.CONFIRMED,
            ExhibitorRegistration.is_deleted == False
        )
                .order_by(ExhibitorRegistration.confirmed_at)
                .all())

    @staticmethod
    def get_by_industry(industry: IndustryCategory) -> List[ExhibitorRegistration]:
        """Get exhibitors by industry category"""
        return (ExhibitorRegistration.query
                .filter_by(industry_category=industry, is_deleted=False)
                .all())


# ============================================
# REPORTING UTILITIES
# ============================================

class RegistrationReports:
    """Generate registration reports and statistics"""

    @staticmethod
    def get_registration_summary() -> Dict[str, Any]:
        """Get overall registration summary"""
        total = Registration.query.filter_by(is_deleted=False).count()

        attendees = AttendeeRegistration.query.filter_by(is_deleted=False).count()
        exhibitors = ExhibitorRegistration.query.filter_by(is_deleted=False).count()

        confirmed = Registration.query.filter_by(
            status=RegistrationStatus.CONFIRMED,
            is_deleted=False
        ).count()

        pending = Registration.query.filter_by(
            status=RegistrationStatus.PENDING,
            is_deleted=False
        ).count()

        return {
            'total_registrations': total,
            'attendees': attendees,
            'exhibitors': exhibitors,
            'confirmed': confirmed,
            'pending': pending,
            'confirmation_rate': (confirmed / total * 100) if total > 0 else 0
        }

    @staticmethod
    def get_ticket_distribution() -> Dict[str, int]:
        """Get distribution of ticket types"""
        results = (db.session.query(
            AttendeeRegistration.ticket_type,
            func.count(AttendeeRegistration.id)
        )
                   .filter(AttendeeRegistration.is_deleted == False)
                   .group_by(AttendeeRegistration.ticket_type)
                   .all())

        return {str(ticket_type.value): count for ticket_type, count in results}

    @staticmethod
    def get_package_distribution() -> Dict[str, int]:
        """Get distribution of exhibitor packages"""
        results = (db.session.query(
            ExhibitorRegistration.package_type,
            func.count(ExhibitorRegistration.id)
        )
                   .filter(ExhibitorRegistration.is_deleted == False)
                   .group_by(ExhibitorRegistration.package_type)
                   .all())

        return {str(package.value): count for package, count in results}

    @staticmethod
    def get_daily_registration_trend(days: int = 30) -> List[Dict[str, Any]]:
        """Get daily registration trend for past N days"""
        start_date = datetime.now() - timedelta(days=days)

        results = (db.session.query(
            func.date(Registration.created_at).label('date'),
            func.count(Registration.id).label('count'),
            Registration.registration_type
        )
                   .filter(
            Registration.created_at >= start_date,
            Registration.is_deleted == False
        )
                   .group_by(func.date(Registration.created_at), Registration.registration_type)
                   .order_by(func.date(Registration.created_at))
                   .all())

        trend_data = {}
        for result in results:
            date_str = result.date.isoformat()
            if date_str not in trend_data:
                trend_data[date_str] = {'date': date_str, 'attendees': 0, 'exhibitors': 0}

            if result.registration_type == 'attendee':
                trend_data[date_str]['attendees'] = result.count
            elif result.registration_type == 'exhibitor':
                trend_data[date_str]['exhibitors'] = result.count

        return list(trend_data.values())

    @staticmethod
    def get_geographic_distribution() -> Dict[str, int]:
        """Get distribution by country"""
        results = (db.session.query(
            Registration.country,
            func.count(Registration.id)
        )
                   .filter(
            Registration.country.isnot(None),
            Registration.is_deleted == False
        )
                   .group_by(Registration.country)
                   .order_by(func.count(Registration.id).desc())
                   .all())

        return {country: count for country, count in results if country}

    @staticmethod
    def get_revenue_summary() -> Dict[str, Any]:
        """Get revenue summary from payments"""
        # Total revenue
        total_revenue = (db.session.query(func.sum(Payment.total_amount))
                         .filter(Payment.payment_status == PaymentStatus.COMPLETED)
                         .scalar()) or Decimal('0.00')

        # Revenue by payment method
        payment_methods = (db.session.query(
            Payment.payment_method,
            func.sum(Payment.total_amount)
        )
                           .filter(Payment.payment_status == PaymentStatus.COMPLETED)
                           .group_by(Payment.payment_method)
                           .all())

        # Pending payments
        pending_revenue = (db.session.query(func.sum(Payment.total_amount))
                           .filter(Payment.payment_status.in_([
            PaymentStatus.PENDING,
            PaymentStatus.PROCESSING
        ]))
                           .scalar()) or Decimal('0.00')

        return {
            'total_revenue': float(total_revenue),
            'pending_revenue': float(pending_revenue),
            'by_payment_method': {
                str(method.value): float(amount)
                for method, amount in payment_methods
            }
        }


# ============================================
# DATA EXPORT UTILITIES
# ============================================

class DataExport:
    """Export registration data in various formats"""

    @staticmethod
    def export_registrations_to_dict(
            registration_type: str = None,
            include_pii: bool = True
    ) -> List[Dict[str, Any]]:
        """Export registrations as list of dictionaries"""
        query = Registration.query.filter_by(is_deleted=False)

        if registration_type:
            query = query.filter_by(registration_type=registration_type)

        registrations = query.all()
        return [reg.to_dict(include_pii=include_pii) for reg in registrations]

    @staticmethod
    def export_attendees_for_badges() -> List[Dict[str, str]]:
        """Export attendee data formatted for badge printing"""
        attendees = (AttendeeRegistration.query
                     .filter_by(is_deleted=False, status=RegistrationStatus.CONFIRMED)
                     .all())

        return [
            {
                'first_name': att.first_name,
                'last_name': att.last_name,
                'organization': att.organization or '',
                'ticket_type': att.ticket_type.value,
                'qr_code_data': att.qr_code_data or '',
                'reference_number': att.reference_number
            }
            for att in attendees
        ]

    @staticmethod
    def export_exhibitors_for_catalog() -> List[Dict[str, Any]]:
        """Export exhibitor data for event catalog"""
        exhibitors = (ExhibitorRegistration.query
                      .filter_by(is_deleted=False, status=RegistrationStatus.CONFIRMED)
                      .order_by(ExhibitorRegistration.company_legal_name)
                      .all())

        return [
            {
                'company_name': exh.company_legal_name,
                'booth_number': exh.booth_number or 'TBA',
                'description': exh.company_description,
                'website': exh.company_website,
                'logo_url': exh.company_logo_url,
                'industry': exh.industry_category.value,
                'contact_email': exh.company_email,
                'social_media': {
                    'facebook': exh.facebook_url,
                    'linkedin': exh.linkedin_url,
                    'twitter': exh.twitter_handle,
                    'instagram': exh.instagram_handle
                }
            }
            for exh in exhibitors
        ]

    @staticmethod
    def export_attendee_list_for_exhibitors(
            include_contact_info: bool = False
    ) -> List[Dict[str, Any]]:
        """Export attendee list for exhibitor networking"""
        attendees = (AttendeeRegistration.query
                     .filter_by(
            is_deleted=False,
            status=RegistrationStatus.CONFIRMED,
            consent_networking=True
        )
                     .all())

        data = []
        for att in attendees:
            entry = {
                'name': f"{att.first_name} {att.last_name}",
                'organization': att.organization or '',
                'job_title': att.job_title or '',
                'professional_category': att.professional_category.value if att.professional_category else '',
                'interests': att.session_interests or []
            }

            if include_contact_info and att.consent_data_sharing:
                entry['email'] = att.email
                entry['linkedin'] = att.linkedin_url

            data.append(entry)

        return data


# ============================================
# VALIDATION UTILITIES
# ============================================

class ValidationHelpers:
    """Validation helper functions"""

    @staticmethod
    def check_email_availability(
            email: str,
            registration_type: str,
            exclude_id: int = None
    ) -> Tuple[bool, str]:
        """
        Check if email is available for registration

        Returns:
            Tuple of (is_available, message)
        """
        query = Registration.query.filter(
            func.lower(Registration.email) == email.lower(),
            Registration.registration_type == registration_type,
            Registration.is_deleted == False
        )

        if exclude_id:
            query = query.filter(Registration.id != exclude_id)

        existing = query.first()

        if existing:
            return False, f"Email already registered as {registration_type}"

        return True, "Email is available"

    @staticmethod
    def validate_registration_can_be_confirmed(
            registration: Registration
    ) -> Tuple[bool, str]:
        """
        Check if registration can be confirmed

        Returns:
            Tuple of (can_confirm, message)
        """
        if registration.is_deleted:
            return False, "Registration is deleted"

        if registration.status == RegistrationStatus.CONFIRMED:
            return False, "Registration is already confirmed"

        if registration.status == RegistrationStatus.CANCELLED:
            return False, "Registration is cancelled"

        if not registration.is_fully_paid():
            balance = registration.get_balance_due()
            return False, f"Payment incomplete. Balance due: {balance}"

        return True, "Registration can be confirmed"

    @staticmethod
    def validate_booth_number_available(
            booth_number: str,
            exclude_exhibitor_id: int = None
    ) -> Tuple[bool, str]:
        """Check if booth number is available"""
        query = ExhibitorRegistration.query.filter_by(
            booth_number=booth_number,
            booth_assigned=True,
            is_deleted=False
        )

        if exclude_exhibitor_id:
            query = query.filter(ExhibitorRegistration.id != exclude_exhibitor_id)

        existing = query.first()

        if existing:
            return False, f"Booth {booth_number} already assigned to {existing.company_legal_name}"

        return True, f"Booth {booth_number} is available"


# ============================================
# STATISTICAL UTILITIES
# ============================================

class RegistrationStatistics:
    """Calculate registration statistics"""

    @staticmethod
    def get_conversion_rate() -> Dict[str, float]:
        """Calculate registration to confirmation conversion rate"""
        total = Registration.query.filter_by(is_deleted=False).count()
        confirmed = Registration.query.filter_by(
            status=RegistrationStatus.CONFIRMED,
            is_deleted=False
        ).count()

        return {
            'total_registrations': total,
            'confirmed_registrations': confirmed,
            'conversion_rate': (confirmed / total * 100) if total > 0 else 0
        }

    @staticmethod
    def get_average_registration_value() -> Dict[str, Decimal]:
        """Calculate average registration value"""
        # Attendees
        attendee_avg = (db.session.query(func.avg(Payment.total_amount))
                        .join(AttendeeRegistration,
                              Payment.registration_id == AttendeeRegistration.id)
                        .filter(Payment.payment_status == PaymentStatus.COMPLETED)
                        .scalar()) or Decimal('0.00')

        # Exhibitors
        exhibitor_avg = (db.session.query(func.avg(Payment.total_amount))
                         .join(ExhibitorRegistration,
                               Payment.registration_id == ExhibitorRegistration.id)
                         .filter(Payment.payment_status == PaymentStatus.COMPLETED)
                         .scalar()) or Decimal('0.00')

        return {
            'attendee_average': Decimal(str(attendee_avg)),
            'exhibitor_average': Decimal(str(exhibitor_avg))
        }

    @staticmethod
    def get_registration_velocity(days: int = 7) -> Dict[str, float]:
        """Calculate registration velocity (registrations per day)"""
        start_date = datetime.now() - timedelta(days=days)

        count = (Registration.query
                 .filter(
            Registration.created_at >= start_date,
            Registration.is_deleted == False
        )
                 .count())

        velocity = count / days if days > 0 else 0

        return {
            'period_days': days,
            'registrations': count,
            'velocity_per_day': round(velocity, 2)
        }

    @staticmethod
    def get_payment_success_rate() -> Dict[str, Any]:
        """Calculate payment success rate"""
        total_payments = Payment.query.count()
        successful_payments = Payment.query.filter_by(
            payment_status=PaymentStatus.COMPLETED
        ).count()
        failed_payments = Payment.query.filter_by(
            payment_status=PaymentStatus.FAILED
        ).count()

        return {
            'total_payments': total_payments,
            'successful_payments': successful_payments,
            'failed_payments': failed_payments,
            'success_rate': (successful_payments / total_payments * 100) if total_payments > 0 else 0,
            'failure_rate': (failed_payments / total_payments * 100) if total_payments > 0 else 0
        }


# ============================================
# BULK OPERATIONS
# ============================================

class BulkOperations:
    """Bulk operations on registrations"""

    @staticmethod
    def send_reminder_emails(email_type: str = 'payment_reminder') -> int:
        """
        Identify registrations needing reminder emails
        Returns count of registrations identified
        """
        if email_type == 'payment_reminder':
            # Find pending payments due soon
            cutoff_date = datetime.utcnow() + timedelta(days=3)

            registrations = (Registration.query
                             .join(Payment)
                             .filter(
                Registration.status == RegistrationStatus.PAYMENT_PENDING,
                Registration.is_deleted == False,
                Payment.payment_status == PaymentStatus.PENDING,
                Payment.payment_due_date <= cutoff_date,
                Payment.payment_reminder_sent == False
            )
                             .all())

            return len(registrations)

        return 0

    @staticmethod
    def expire_old_pending_registrations(days_old: int = 7) -> int:
        """
        Expire pending registrations older than specified days
        Returns count of expired registrations
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        registrations = (Registration.query
                         .filter(
            Registration.status == RegistrationStatus.PENDING,
            Registration.created_at < cutoff_date,
            Registration.is_deleted == False
        )
                         .all())

        count = 0
        for reg in registrations:
            reg.status = RegistrationStatus.EXPIRED
            count += 1

        db.session.commit()
        return count

    @staticmethod
    def update_registration_status_bulk(
            registration_ids: List[int],
            new_status: RegistrationStatus
    ) -> int:
        """
        Update status for multiple registrations
        Returns count of updated registrations
        """
        result = (db.session.query(Registration)
                  .filter(Registration.id.in_(registration_ids))
                  .update({'status': new_status}, synchronize_session='fetch'))

        db.session.commit()
        return result
