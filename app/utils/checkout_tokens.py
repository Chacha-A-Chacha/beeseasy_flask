"""
Signed checkout tokens for secure payment links.

Generates HMAC-signed tokens over registration reference numbers
using the app's SECRET_KEY. Tokens have no time expiry — checkout
links remain valid until payment is completed.
"""

from itsdangerous import BadSignature, URLSafeSerializer
from flask import current_app


def _get_serializer():
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="checkout")


def generate_checkout_token(reference_number: str) -> str:
    """Sign a reference number into a URL-safe token."""
    return _get_serializer().dumps(reference_number)


def verify_checkout_token(token: str) -> str | None:
    """
    Verify a checkout token and return the reference number.
    Returns None if the token is invalid or tampered with.
    """
    try:
        return _get_serializer().loads(token)
    except BadSignature:
        return None
