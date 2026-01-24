"""
Newsletter Subscription Service
Handles email newsletter subscriptions with verification and unsubscribe
"""

import logging
import secrets
from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models.newsletter import NewsletterSubscription
from app.utils.enhanced_email import EnhancedEmailService, Priority

logger = logging.getLogger(__name__)


class NewsletterService:
    """Service for managing newsletter subscriptions"""

    @staticmethod
    def subscribe(email: str, source: str = "unknown") -> dict:
        """
        Subscribe an email to the newsletter

        Args:
            email: Email address to subscribe
            source: Source of subscription (overlay, registration_closed, footer, etc.)

        Returns:
            dict: {success: bool, message: str, subscription: NewsletterSubscription or None}
        """
        try:
            email = email.strip().lower()

            # Check if already subscribed
            existing = NewsletterSubscription.query.filter_by(email=email).first()

            if existing:
                if existing.is_active and not existing.is_deleted:
                    return {
                        "success": False,
                        "message": "This email is already subscribed to our newsletter.",
                        "subscription": existing,
                    }
                elif existing.is_deleted:
                    # Restore deleted subscription
                    existing.is_deleted = False
                    existing.deleted_at = None
                    existing.is_active = True
                    existing.subscribed_at = datetime.now()
                    existing.source = source
                    existing.verification_token = secrets.token_urlsafe(32)
                    db.session.commit()

                    # Send verification email
                    NewsletterService._send_verification_email(existing)

                    return {
                        "success": True,
                        "message": "Welcome back! Please check your email to verify your subscription.",
                        "subscription": existing,
                    }
                else:
                    # Reactivate inactive subscription
                    existing.resubscribe()
                    existing.source = source
                    existing.verification_token = secrets.token_urlsafe(32)
                    db.session.commit()

                    # Send verification email
                    NewsletterService._send_verification_email(existing)

                    return {
                        "success": True,
                        "message": "Your subscription has been reactivated! Please check your email to verify.",
                        "subscription": existing,
                    }

            # Create new subscription
            verification_token = secrets.token_urlsafe(32)
            subscription = NewsletterSubscription(
                email=email,
                source=source,
                is_active=True,
                is_verified=False,
                verification_token=verification_token,
                subscribed_at=datetime.now(),
            )

            db.session.add(subscription)
            db.session.commit()

            # Send verification email
            NewsletterService._send_verification_email(subscription)

            logger.info(f"New newsletter subscription: {email} from {source}")

            return {
                "success": True,
                "message": "Thank you! Please check your email to confirm your subscription.",
                "subscription": subscription,
            }

        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Newsletter subscription failed for {email}: {e}", exc_info=True
            )
            return {
                "success": False,
                "message": "Sorry, we couldn't process your subscription. Please try again later.",
                "subscription": None,
            }

    @staticmethod
    def verify(token: str) -> dict:
        """
        Verify email subscription via token

        Args:
            token: Verification token from email

        Returns:
            dict: {success: bool, message: str}
        """
        try:
            subscription = NewsletterSubscription.query.filter_by(
                verification_token=token, is_deleted=False
            ).first()

            if not subscription:
                return {
                    "success": False,
                    "message": "Invalid or expired verification link.",
                }

            if subscription.is_verified:
                return {
                    "success": True,
                    "message": "Your email is already verified. You're all set!",
                }

            # Verify the subscription
            subscription.verify()
            db.session.commit()

            logger.info(f"Newsletter subscription verified: {subscription.email}")

            return {
                "success": True,
                "message": "Thank you! Your email has been verified successfully.",
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Newsletter verification failed: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Verification failed. Please try again or contact support.",
            }

    @staticmethod
    def unsubscribe(email: str = None, token: str = None, reason: str = None) -> dict:
        """
        Unsubscribe from newsletter

        Args:
            email: Email address to unsubscribe
            token: Unsubscribe token (alternative to email)
            reason: Optional reason for unsubscribing

        Returns:
            dict: {success: bool, message: str}
        """
        try:
            subscription = None

            if token:
                subscription = NewsletterSubscription.query.filter_by(
                    verification_token=token, is_deleted=False
                ).first()
            elif email:
                email = email.strip().lower()
                subscription = NewsletterSubscription.query.filter_by(
                    email=email, is_deleted=False
                ).first()

            if not subscription:
                return {
                    "success": False,
                    "message": "Subscription not found.",
                }

            if not subscription.is_active:
                return {
                    "success": True,
                    "message": "You're already unsubscribed.",
                }

            # Unsubscribe
            subscription.unsubscribe(reason=reason)
            db.session.commit()

            logger.info(f"Newsletter unsubscribed: {subscription.email}")

            return {
                "success": True,
                "message": "You've been unsubscribed successfully. We're sorry to see you go!",
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Newsletter unsubscribe failed: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Unsubscribe failed. Please try again or contact support.",
            }

    @staticmethod
    def _send_verification_email(subscription: NewsletterSubscription):
        """
        Send verification email to subscriber

        Args:
            subscription: NewsletterSubscription instance
        """
        try:
            email_service = EnhancedEmailService(current_app)

            # Build verification URL
            verify_url = f"{current_app.config.get('WEBSITE_URL', 'https://pollination.africa')}/newsletter/verify/{subscription.verification_token}"
            unsubscribe_url = f"{current_app.config.get('WEBSITE_URL', 'https://pollination.africa')}/newsletter/unsubscribe/{subscription.verification_token}"

            # Email context
            context = {
                "email": subscription.email,
                "verify_url": verify_url,
                "unsubscribe_url": unsubscribe_url,
                "event_name": current_app.config.get(
                    "EVENT_NAME", "Pollination Africa Symposium 2026"
                ),
                "event_date": current_app.config.get("EVENT_DATE", "3-5 June 2026"),
                "event_location": current_app.config.get(
                    "EVENT_LOCATION",
                    "Arusha International Conference Centre, Arusha, Tanzania",
                ),
                "contact_email": current_app.config.get(
                    "CONTACT_EMAIL", "info@pollination.africa"
                ),
                "website_url": current_app.config.get(
                    "WEBSITE_URL", "https://pollination.africa"
                ),
            }

            # Send verification email
            email_service.send_notification(
                recipient=subscription.email,
                template="newsletter_verification",
                subject=f"Verify your subscription - {context['event_name']}",
                template_context=context,
                priority=Priority.NORMAL,
            )

            logger.info(f"Verification email sent to: {subscription.email}")

        except Exception as e:
            logger.error(
                f"Failed to send verification email to {subscription.email}: {e}",
                exc_info=True,
            )

    @staticmethod
    def get_active_subscribers(limit: int = None) -> list:
        """
        Get list of active subscribers

        Args:
            limit: Optional limit on results

        Returns:
            list: List of NewsletterSubscription instances
        """
        query = NewsletterSubscription.query.filter_by(
            is_active=True, is_deleted=False
        ).order_by(NewsletterSubscription.subscribed_at.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def get_stats() -> dict:
        """
        Get newsletter subscription statistics

        Returns:
            dict: Statistics about subscriptions
        """
        total = NewsletterSubscription.query.filter_by(is_deleted=False).count()
        active = NewsletterSubscription.query.filter_by(
            is_active=True, is_deleted=False
        ).count()
        verified = NewsletterSubscription.query.filter_by(
            is_active=True, is_verified=True, is_deleted=False
        ).count()
        unsubscribed = NewsletterSubscription.query.filter_by(
            is_active=False, is_deleted=False
        ).count()

        return {
            "total": total,
            "active": active,
            "verified": verified,
            "unsubscribed": unsubscribed,
            "unverified": active - verified,
        }
