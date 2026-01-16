#!/usr/bin/env python3
"""
DPO Payment Methods Test Script
Tests all supported payment methods and their XML generation
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.dpo_service import DPOService
from decimal import Decimal


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_payment_methods():
    """Test that all payment methods are properly configured"""
    print_section("TESTING: Get Supported Payment Methods")

    dpo_service = DPOService()
    methods = dpo_service.get_supported_payment_methods()

    print(f"\nTotal payment methods configured: {len(methods)}")
    print("\nPayment Methods:")
    print("-" * 70)

    for method_id, method_data in methods.items():
        print(f"\n✓ {method_id.upper()}")
        print(f"  Name: {method_data['name']}")
        print(f"  Type: {method_data['type']}")
        if 'country' in method_data:
            print(f"  Country: {method_data['country']}")
        if 'mno' in method_data:
            print(f"  MNO: {method_data['mno']}")
        print(f"  Description: {method_data['description']}")
        print(f"  Processing: {method_data['processing_time']}")

    # Verify expected methods exist
    expected_methods = [
        'mpesa',           # M-Pesa Vodacom (Tanzania)
        'mpesa_kenya',     # M-Pesa Safaricom (Kenya)
        'tigo',            # Tigo Pesa (Tanzania)
        'airtel',          # Airtel Money (Multi-country)
        'mtn',             # MTN MoMo (Uganda, Rwanda)
        'orange',          # Orange Money (Multi-country)
        'card',            # Credit/Debit Cards
    ]

    print("\n" + "-" * 70)
    print("Validation:")
    missing = []
    for method in expected_methods:
        if method in methods:
            print(f"  ✅ {method} - Found")
        else:
            print(f"  ❌ {method} - Missing")
            missing.append(method)

    if missing:
        print(f"\n⚠️  Warning: {len(missing)} method(s) missing: {', '.join(missing)}")
        return False
    else:
        print("\n✅ All expected payment methods are configured!")
        return True


def test_xml_generation():
    """Test XML generation for each payment type"""
    print_section("TESTING: XML Generation for Payment Types")

    dpo_service = DPOService()

    # Test data
    base_payment_data = {
        "amount": 50000.00,
        "currency": "TZS",
        "company_ref": "TEST-REF-2024",
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "customer_phone": "+255712345678",
        "service_description": "Event Registration - Attendee",
        "service_date": "2024/12/31 09:00",
    }

    payment_types = [
        ('card', 'Credit/Debit Card'),
        ('mpesa', 'M-Pesa Vodacom (Tanzania)'),
        ('mpesa_kenya', 'M-Pesa Safaricom (Kenya)'),
        ('tigo', 'Tigo Pesa (Tanzania)'),
        ('airtel', 'Airtel Money'),
        ('mtn', 'MTN MoMo'),
        ('orange', 'Orange Money'),
    ]

    all_passed = True

    for payment_type, description in payment_types:
        print(f"\n{'-' * 70}")
        print(f"Testing: {description} (payment_type='{payment_type}')")
        print(f"{'-' * 70}")

        payment_data = {**base_payment_data, "payment_type": payment_type}

        try:
            xml = dpo_service._build_create_token_xml(payment_data)

            # Check for key elements
            checks = []

            # Basic checks for all payment types
            if '<PaymentAmount>50000.0</PaymentAmount>' in xml:
                checks.append(('Amount', True))
            else:
                checks.append(('Amount', False))

            if '<PaymentCurrency>TZS</PaymentCurrency>' in xml:
                checks.append(('Currency', True))
            else:
                checks.append(('Currency', False))

            if '<CompanyRef>TEST-REF-2024</CompanyRef>' in xml:
                checks.append(('Company Ref', True))
            else:
                checks.append(('Company Ref', False))

            # Payment type specific checks
            if payment_type == 'card':
                if '<DefaultPayment>CC</DefaultPayment>' in xml:
                    checks.append(('Card Payment Type', True))
                else:
                    checks.append(('Card Payment Type', False))

            elif payment_type == 'mpesa':
                if '<DefaultPayment>MO</DefaultPayment>' in xml:
                    checks.append(('Mobile Money Type', True))
                else:
                    checks.append(('Mobile Money Type', False))

                if '<DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>' in xml:
                    checks.append(('Country: Tanzania', True))
                else:
                    checks.append(('Country: Tanzania', False))

                if '<DefaultPaymentMNO>Vodacom</DefaultPaymentMNO>' in xml:
                    checks.append(('MNO: Vodacom', True))
                else:
                    checks.append(('MNO: Vodacom', False))

            elif payment_type == 'mpesa_kenya':
                if '<DefaultPayment>MO</DefaultPayment>' in xml:
                    checks.append(('Mobile Money Type', True))
                else:
                    checks.append(('Mobile Money Type', False))

                if '<DefaultPaymentCountry>Kenya</DefaultPaymentCountry>' in xml:
                    checks.append(('Country: Kenya', True))
                else:
                    checks.append(('Country: Kenya', False))

                if '<DefaultPaymentMNO>Safaricom</DefaultPaymentMNO>' in xml:
                    checks.append(('MNO: Safaricom', True))
                else:
                    checks.append(('MNO: Safaricom', False))

            elif payment_type == 'tigo':
                if '<DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>' in xml:
                    checks.append(('Country: Tanzania', True))
                else:
                    checks.append(('Country: Tanzania', False))

                if '<DefaultPaymentMNO>Tigo</DefaultPaymentMNO>' in xml:
                    checks.append(('MNO: Tigo', True))
                else:
                    checks.append(('MNO: Tigo', False))

            elif payment_type == 'airtel':
                if '<DefaultPaymentCountry>Tanzania</DefaultPaymentCountry>' in xml:
                    checks.append(('Country: Tanzania', True))
                else:
                    checks.append(('Country: Tanzania', False))

                if '<DefaultPaymentMNO>Airtel</DefaultPaymentMNO>' in xml:
                    checks.append(('MNO: Airtel', True))
                else:
                    checks.append(('MNO: Airtel', False))

            elif payment_type == 'mtn':
                if '<DefaultPaymentCountry>Uganda</DefaultPaymentCountry>' in xml:
                    checks.append(('Country: Uganda', True))
                else:
                    checks.append(('Country: Uganda', False))

                if '<DefaultPaymentMNO>MTN</DefaultPaymentMNO>' in xml:
                    checks.append(('MNO: MTN', True))
                else:
                    checks.append(('MNO: MTN', False))

            elif payment_type == 'orange':
                if '<DefaultPaymentCountry>Senegal</DefaultPaymentCountry>' in xml:
                    checks.append(('Country: Senegal', True))
                else:
                    checks.append(('Country: Senegal', False))

                if '<DefaultPaymentMNO>Orange</DefaultPaymentMNO>' in xml:
                    checks.append(('MNO: Orange', True))
                else:
                    checks.append(('MNO: Orange', False))

            # Print results
            print("\nValidation Checks:")
            all_checks_passed = True
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"  {status} {check_name}")
                if not passed:
                    all_checks_passed = False

            if all_checks_passed:
                print(f"\n✅ {description} XML generation passed all checks")
            else:
                print(f"\n❌ {description} XML generation failed some checks")
                all_passed = False
                print("\nGenerated XML (first 500 chars):")
                print(xml[:500])

        except Exception as e:
            print(f"\n❌ ERROR generating XML: {str(e)}")
            all_passed = False
            import traceback
            traceback.print_exc()

    return all_passed


def test_payment_type_mapping():
    """Test that payment types are correctly categorized"""
    print_section("TESTING: Payment Type Categorization")

    dpo_service = DPOService()
    methods = dpo_service.get_supported_payment_methods()

    mobile_money = []
    cards = []

    for method_id, method_data in methods.items():
        if method_data['type'] == 'mobile_money':
            mobile_money.append(method_id)
        elif method_data['type'] == 'card':
            cards.append(method_id)

    print(f"\nMobile Money Methods ({len(mobile_money)}):")
    for method in mobile_money:
        print(f"  • {method}")

    print(f"\nCard Methods ({len(cards)}):")
    for method in cards:
        print(f"  • {method}")

    # Verify expectations
    expected_mobile = {'mpesa', 'mpesa_kenya', 'tigo', 'airtel', 'mtn', 'orange'}
    expected_cards = {'card'}

    print("\nValidation:")
    mobile_ok = set(mobile_money) == expected_mobile
    cards_ok = set(cards) == expected_cards

    if mobile_ok:
        print("  ✅ Mobile money methods correct")
    else:
        print(f"  ❌ Mobile money methods mismatch")
        print(f"     Expected: {expected_mobile}")
        print(f"     Got: {set(mobile_money)}")

    if cards_ok:
        print("  ✅ Card methods correct")
    else:
        print(f"  ❌ Card methods mismatch")
        print(f"     Expected: {expected_cards}")
        print(f"     Got: {set(cards)}")

    return mobile_ok and cards_ok


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(" DPO PAYMENT METHODS TEST SUITE")
    print(" Testing all supported payment methods and XML generation")
    print("=" * 70)

    results = []

    # Test 1: Payment methods configuration
    results.append(('Payment Methods Configuration', test_payment_methods()))

    # Test 2: XML generation
    results.append(('XML Generation', test_xml_generation()))

    # Test 3: Payment type mapping
    results.append(('Payment Type Categorization', test_payment_type_mapping()))

    # Summary
    print_section("TEST SUMMARY")

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("All payment methods are correctly configured and working.")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("Please review the failures above and fix configuration.")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
