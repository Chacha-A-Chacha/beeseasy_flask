"""
DPO Payment Gateway Service for BEEASY2025
Handles DPO API interactions for Tanzania mobile money and card payments

Supported Payment Methods:
- Mobile Money: M-Pesa (Vodacom), Tigo Pesa, Airtel Money
- Cards: Visa, Mastercard, Amex
"""

import logging
from typing import Dict, Optional

import requests
import xmltodict
from flask import current_app

logger = logging.getLogger("dpo_service")


class DPOService:
    """
    DPO Payment Gateway Service

    Handles all interactions with DPO API including:
    - Creating payment tokens (initiate payment)
    - Verifying payment status
    - Generating payment URLs
    - Canceling tokens

    Documentation: https://dpogroup.com/developer-resources/
    """

    def __init__(self):
        """Initialize DPO service with configuration from Flask app"""
        self.company_token: Optional[str] = None
        self.service_type: Optional[str] = None
        self.currency: str = "TZS"
        self.test_mode: bool = True
        self.base_url: str = ""
        self.api_url: str = ""
        self.redirect_url: Optional[str] = None
        self.back_url: Optional[str] = None
        self.token_lifetime: int = 5

    def init_app(self, app):
        """Initialize with Flask app context"""
        with app.app_context():
            self.company_token = current_app.config.get("DPO_COMPANY_TOKEN")
            self.service_type = current_app.config.get("DPO_SERVICE_TYPE")
            self.currency = current_app.config.get("DPO_CURRENCY", "TZS")
            self.test_mode = current_app.config.get("DPO_TEST_MODE", True)

            # Set API URLs based on test/production mode
            self.base_url = (
                current_app.config.get("DPO_API_URL_TEST")
                if self.test_mode
                else current_app.config.get("DPO_API_URL_LIVE")
            )
            self.api_url = f"{self.base_url}/API/v6/"

            # Callback URLs
            self.redirect_url = current_app.config.get("DPO_REDIRECT_URL")
            self.back_url = current_app.config.get("DPO_BACK_URL")
            self.token_lifetime = current_app.config.get(
                "DPO_PAYMENT_TOKEN_LIFETIME", 5
            )

            # Validate configuration
            if not self.company_token:
                logger.warning("DPO_COMPANY_TOKEN not configured")
            if not self.service_type:
                logger.warning("DPO_SERVICE_TYPE not configured")
            if not self.redirect_url:
                logger.warning("DPO_REDIRECT_URL not configured")

            logger.info(
                f"DPO Service initialized - Mode: {'TEST' if self.test_mode else 'LIVE'}, "
                f"Currency: {self.currency}"
            )

    def create_token(self, payment_data: Dict) -> Dict:
        """
        Create payment token with DPO

        Args:
            payment_data: Dictionary containing payment information
                Required fields:
                    - amount: float (total payment amount)
                    - company_ref: str (unique reference - use payment.payment_reference)
                    - customer_name: str (full name)
                    - customer_email: str
                    - customer_phone: str (e.g., +255712345678)
                    - service_description: str (e.g., "VIP Ticket - Event Name")

                Optional fields:
                    - currency: str (USD, TZS, etc. - defaults to config DPO_CURRENCY)
                    - service_date: str (event date)
                    - payment_type: str (mpesa, tigo, airtel, card)

        Returns:
            Dictionary with token information or error:
            {
                'success': bool,
                'trans_token': str,
                'trans_ref': str,
                'payment_url': str,
                'error': str (if failed),
                'full_response': dict (complete DPO response)
            }
        """
        try:
            # Validate configuration
            if not self.company_token or not self.service_type:
                return {
                    "success": False,
                    "error": "DPO service not properly configured. Missing CompanyToken or ServiceType.",
                }

            # Validate required payment data
            required_fields = [
                "amount",
                "company_ref",
                "customer_name",
                "customer_email",
                "customer_phone",
            ]
            for field in required_fields:
                if field not in payment_data or not payment_data[field]:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}",
                    }

            # Build XML request
            xml_request = self._build_create_token_xml(payment_data)

            # Log configuration (mask sensitive data)
            company_token_masked = (
                f"{self.company_token[:8]}...{self.company_token[-4:]}"
                if self.company_token and len(self.company_token) > 12
                else "NOT_SET"
            )
            logger.info(
                f"Creating DPO token for {payment_data['company_ref']} - "
                f"Amount: {self.currency} {payment_data['amount']}"
            )
            logger.info(
                f"DPO Config - URL: {self.api_url}, "
                f"Token: {company_token_masked}, "
                f"Service Type: {self.service_type}, "
                f"Test Mode: {self.test_mode}"
            )

            # Send request to DPO
            response = requests.post(
                self.api_url,
                data=xml_request,
                headers={"Content-Type": "application/xml"},
                timeout=30,
            )

            # Log response details before checking status
            logger.info(f"DPO API Response Status: {response.status_code}")
            logger.debug(f"DPO API Response Headers: {response.headers}")
            logger.debug(f"DPO API Response Body: {response.text}")

            # If we got a 403, try to parse the error from DPO
            if response.status_code == 403:
                try:
                    error_result = xmltodict.parse(response.content)
                    error_msg = error_result.get("API3G", {}).get(
                        "ResultExplanation", "Forbidden - Invalid credentials"
                    )
                    logger.error(f"DPO API 403 Error: {error_msg}")
                    return {
                        "success": False,
                        "error": f"DPO Authentication Failed: {error_msg}",
                    }
                except Exception:
                    logger.error(
                        "DPO API returned 403 Forbidden - Check your Company Token and Service Type"
                    )
                    return {
                        "success": False,
                        "error": "Invalid DPO credentials. Please check your Company Token and Service Type.",
                    }

            response.raise_for_status()

            # Parse XML response
            result = xmltodict.parse(response.content)
            api_response = result.get("API3G", {})

            # Check for success
            result_code = api_response.get("Result", "")

            if result_code == "000":
                # Success - payment token created
                trans_token = api_response.get("TransToken")
                trans_ref = api_response.get("TransRef")
                payment_url = self._create_payment_url(trans_token)

                logger.info(
                    f"DPO token created successfully: {trans_token} (Ref: {trans_ref})"
                )

                return {
                    "success": True,
                    "trans_token": trans_token,
                    "trans_ref": trans_ref,
                    "payment_url": payment_url,
                    "full_response": api_response,
                }
            else:
                # Token creation failed
                error_msg = api_response.get("ResultExplanation", "Unknown error")
                logger.error(
                    f"DPO token creation failed - Code: {result_code}, Error: {error_msg}"
                )

                return {
                    "success": False,
                    "error": error_msg,
                    "result_code": result_code,
                    "full_response": api_response,
                }

        except requests.Timeout:
            logger.error("DPO API request timeout")
            return {
                "success": False,
                "error": "Payment gateway timeout. Please try again.",
            }
        except requests.RequestException as e:
            logger.error(f"DPO API request failed: {str(e)}")
            return {
                "success": False,
                "error": f"Payment gateway connection error. Please try again later.",
            }
        except Exception as e:
            logger.error(f"DPO token creation error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": "Payment processing error. Please contact support.",
            }

    def verify_token(self, trans_token: str) -> Dict:
        """
        Verify payment status with DPO

        This should be called after user completes payment and is redirected back.
        ALWAYS verify before marking payment as complete.

        Args:
            trans_token: Transaction token from DPO

        Returns:
            Dictionary with payment verification result:
            {
                'success': bool,
                'status': str (Approved, Declined, Pending),
                'customer_name': str,
                'customer_phone': str,
                'payment_method': str (M-Pesa, Visa, etc.),
                'amount': float,
                'currency': str,
                'trans_ref': str,
                'error': str (if failed),
                'full_response': dict
            }
        """
        try:
            if not trans_token:
                return {"success": False, "error": "Transaction token is required"}

            # Build XML request
            xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <API3G>
                <CompanyToken>{self.company_token}</CompanyToken>
                <Request>verifyToken</Request>
                <TransactionToken>{trans_token}</TransactionToken>
            </API3G>"""

            logger.info(f"Verifying DPO token: {trans_token}")

            # Send request
            response = requests.post(
                self.api_url,
                data=xml_request,
                headers={"Content-Type": "application/xml"},
                timeout=30,
            )

            response.raise_for_status()

            # Parse response
            result = xmltodict.parse(response.content)
            api_response = result.get("API3G", {})

            result_code = api_response.get("Result", "")

            if result_code == "000":
                # Payment successful
                logger.info(f"Payment verified successfully: {trans_token}")

                return {
                    "success": True,
                    "status": "Approved",
                    "customer_name": api_response.get("CustomerName", ""),
                    "customer_phone": api_response.get("CustomerPhone", ""),
                    "payment_method": api_response.get("AccRef", ""),
                    "amount": float(api_response.get("TransactionAmount", 0)),
                    "currency": api_response.get("TransactionCurrency", self.currency),
                    "trans_ref": api_response.get("TransactionRef", ""),
                    "full_response": api_response,
                }
            else:
                # Payment failed or pending
                status_explanation = api_response.get("ResultExplanation", "Unknown")

                logger.warning(
                    f"Payment verification failed - Code: {result_code}, "
                    f"Reason: {status_explanation}"
                )

                return {
                    "success": False,
                    "status": "Declined",
                    "error": status_explanation,
                    "result_code": result_code,
                    "full_response": api_response,
                }

        except requests.Timeout:
            logger.error("DPO verification timeout")
            return {
                "success": False,
                "error": "Verification timeout. Please try again.",
            }
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": "Verification error. Please contact support.",
            }

    def cancel_token(self, trans_token: str) -> Dict:
        """
        Cancel a payment token

        Args:
            trans_token: Transaction token to cancel

        Returns:
            Dictionary with cancellation result:
            {
                'success': bool,
                'message': str,
                'full_response': dict
            }
        """
        try:
            xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <API3G>
                <CompanyToken>{self.company_token}</CompanyToken>
                <Request>cancelToken</Request>
                <TransactionToken>{trans_token}</TransactionToken>
            </API3G>"""

            logger.info(f"Canceling DPO token: {trans_token}")

            response = requests.post(
                self.api_url,
                data=xml_request,
                headers={"Content-Type": "application/xml"},
                timeout=30,
            )

            result = xmltodict.parse(response.content)
            api_response = result.get("API3G", {})

            success = api_response.get("Result") == "000"
            message = api_response.get("ResultExplanation", "")

            if success:
                logger.info(f"Token cancelled successfully: {trans_token}")
            else:
                logger.warning(f"Token cancellation failed: {message}")

            return {
                "success": success,
                "message": message,
                "full_response": api_response,
            }

        except Exception as e:
            logger.error(f"Token cancellation error: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _build_create_token_xml(self, payment_data: Dict) -> str:
        """
        Build XML request for createToken API

        Args:
            payment_data: Payment information dictionary

        Returns:
            XML string for DPO API request
        """
        from datetime import datetime

        # Extract customer name parts
        customer_name = payment_data.get("customer_name", "").strip()
        name_parts = customer_name.split(" ", 1)
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Format service date - DPO requires "YYYY/MM/DD HH:MM" format
        service_date = payment_data.get("service_date", "")

        # If no service date provided or invalid format, use current date + 30 days
        if not service_date or len(service_date.strip()) == 0:
            from datetime import datetime, timedelta

            service_date = (datetime.now() + timedelta(days=30)).strftime(
                "%Y/%m/%d 09:00"
            )
        else:
            # Check if date is already in correct format (YYYY/MM/DD HH:MM or YYYY-MM-DD HH:MM)
            if not any(char in service_date for char in [":", " "]):
                # If only date provided (no time), add default time 09:00
                service_date = f"{service_date} 09:00"

            # Ensure forward slashes are used (DPO accepts both / and -)
            # But let's standardize to forward slashes
            if "-" in service_date and "/" not in service_date:
                # Convert YYYY-MM-DD to YYYY/MM/DD
                date_part = (
                    service_date.split(" ")[0] if " " in service_date else service_date
                )
                time_part = (
                    service_date.split(" ")[1] if " " in service_date else "09:00"
                )
                date_part = date_part.replace("-", "/")
                service_date = f"{date_part} {time_part}"

        # Optional: Set default payment method for mobile money
        default_payment = ""
        payment_type = payment_data.get("payment_type", "").lower()

        # Pre-select payment method based on user choice
        if payment_type == "mpesa":
            default_payment = """
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>
            <DefaultPaymentMNO>Vodacom</DefaultPaymentMNO>"""
        elif payment_type == "mpesa_kenya":
            default_payment = """
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Kenya</DefaultPaymentCountry>
            <DefaultPaymentMNO>Safaricom</DefaultPaymentMNO>"""
        elif payment_type == "tigo":
            default_payment = """
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>
            <DefaultPaymentMNO>Tigo</DefaultPaymentMNO>"""
        elif payment_type == "airtel":
            default_payment = """
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>
            <DefaultPaymentMNO>Airtel</DefaultPaymentMNO>"""
        elif payment_type == "mtn":
            default_payment = """
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Uganda</DefaultPaymentCountry>
            <DefaultPaymentMNO>MTN</DefaultPaymentMNO>"""
        elif payment_type == "orange":
            default_payment = """
            <DefaultPayment>MO</DefaultPayment>
            <DefaultPaymentCountry>Senegal</DefaultPaymentCountry>
            <DefaultPaymentMNO>Orange</DefaultPaymentMNO>"""
        elif payment_type == "card":
            default_payment = """
            <DefaultPayment>CC</DefaultPayment>"""

        # Get currency from payment_data or use default from config
        currency = payment_data.get("currency", self.currency)

        # Build XML
        xml = f"""<?xml version="1.0" encoding="utf-8"?>
        <API3G>
            <CompanyToken>{self.company_token}</CompanyToken>
            <Request>createToken</Request>
            <Transaction>
                <PaymentAmount>{payment_data["amount"]}</PaymentAmount>
                <PaymentCurrency>{currency}</PaymentCurrency>
                <CompanyRef>{payment_data["company_ref"]}</CompanyRef>
                <RedirectURL>{self.redirect_url}</RedirectURL>
                <BackURL>{self.back_url}</BackURL>
                <CompanyRefUnique>1</CompanyRefUnique>
                <PTL>{self.token_lifetime}</PTL>
                <customerFirstName>{first_name}</customerFirstName>
                <customerLastName>{last_name}</customerLastName>
                <customerEmail>{payment_data.get("customer_email", "")}</customerEmail>
                <customerPhone>{payment_data.get("customer_phone", "")}</customerPhone>
                {default_payment}
            </Transaction>
            <Services>
                <Service>
                    <ServiceType>{self.service_type}</ServiceType>
                    <ServiceDescription>{payment_data.get("service_description", "Event Payment")}</ServiceDescription>
                    <ServiceDate>{service_date}</ServiceDate>
                </Service>
            </Services>
        </API3G>"""

        return xml

    def _create_payment_url(self, trans_token: str) -> str:
        """
        Generate DPO payment page URL

        Args:
            trans_token: Transaction token from DPO

        Returns:
            Full URL to DPO payment page
        """
        return f"{self.base_url}/payv3.php?ID={trans_token}"

    def is_configured(self) -> bool:
        """
        Check if DPO service is properly configured

        Returns:
            bool: True if all required credentials are set
        """
        return all(
            [self.company_token, self.service_type, self.redirect_url, self.back_url]
        )

    def get_supported_payment_methods(self) -> Dict[str, Dict]:
        """
        Get list of supported payment methods with descriptions

        Returns:
            Dictionary of payment methods with metadata
        """
        return {
            "mpesa": {
                "name": "M-Pesa (Vodacom)",
                "type": "mobile_money",
                "country": "Tanzania",
                "mno": "Vodacom",
                "description": "Pay with M-Pesa mobile money",
                "processing_time": "Instant",
            },
            "mpesa_kenya": {
                "name": "M-Pesa (Safaricom)",
                "type": "mobile_money",
                "country": "Kenya",
                "mno": "Safaricom",
                "description": "Pay with M-Pesa mobile money",
                "processing_time": "Instant",
            },
            "tigo": {
                "name": "Tigo Pesa",
                "type": "mobile_money",
                "country": "Tanzania",
                "mno": "Tigo",
                "description": "Pay with Tigo Pesa mobile money",
                "processing_time": "Instant",
            },
            "airtel": {
                "name": "Airtel Money",
                "type": "mobile_money",
                "country": "Multi",
                "mno": "Airtel",
                "description": "Pay with Airtel Money mobile money",
                "processing_time": "Instant",
            },
            "mtn": {
                "name": "MTN MoMo",
                "type": "mobile_money",
                "country": "Uganda",
                "mno": "MTN",
                "description": "Pay with MTN Mobile Money",
                "processing_time": "Instant",
            },
            "orange": {
                "name": "Orange Money",
                "type": "mobile_money",
                "country": "Multi",
                "mno": "Orange",
                "description": "Pay with Orange Money",
                "processing_time": "Instant",
            },
            "card": {
                "name": "Credit/Debit Card",
                "type": "card",
                "description": "Visa, Mastercard, American Express",
                "processing_time": "Instant",
            },
        }


# Singleton instance
dpo_service = DPOService()
