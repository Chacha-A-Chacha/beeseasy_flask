#!/usr/bin/env python3
"""
DPO Credentials Test Script
Tests your DPO Company Token and Service Type directly

SECURITY WARNING:
================
This script uses environment variables to load DPO credentials.
NEVER hardcode credentials directly in this file!

SETUP:
======
1. Create a .env file in the project root (it's gitignored)
2. Add these variables:
   DPO_COMPANY_TOKEN=your_company_token_here
   DPO_SERVICE_TYPE=your_service_type_here
3. Run this script: python test_dpo_credentials.py

The .env file is automatically excluded from git via .gitignore
"""

import os
from datetime import datetime

import requests
import xmltodict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Your DPO Credentials - LOADED FROM ENVIRONMENT VARIABLES
# DO NOT HARDCODE CREDENTIALS HERE!
COMPANY_TOKEN = os.getenv("DPO_COMPANY_TOKEN")
SERVICE_TYPE = os.getenv("DPO_SERVICE_TYPE")

# Validate credentials are loaded
if not COMPANY_TOKEN or not SERVICE_TYPE:
    print("ERROR: DPO credentials not found in environment variables!")
    print("\nPlease create a .env file with:")
    print("  DPO_COMPANY_TOKEN=your_token_here")
    print("  DPO_SERVICE_TYPE=your_service_type_here")
    exit(1)

# DPO API Configuration
API_URL = "https://secure.3gdirectpay.com/API/v6/"
CURRENCY = "TZS"


def test_create_token():
    """Test creating a payment token with DPO"""

    print("=" * 60)
    print("DPO CREDENTIALS TEST")
    print("=" * 60)
    print(f"Company Token: {COMPANY_TOKEN}")
    print(f"Service Type: {SERVICE_TYPE}")
    print(f"API URL: {API_URL}")
    print(f"Currency: {CURRENCY}")
    print("=" * 60)
    print()

    # Build test payment XML
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<API3G>
    <CompanyToken>{COMPANY_TOKEN}</CompanyToken>
    <Request>createToken</Request>
    <Transaction>
        <PaymentAmount>1000.00</PaymentAmount>
        <PaymentCurrency>{CURRENCY}</PaymentCurrency>
        <CompanyRef>TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}</CompanyRef>
        <RedirectURL>http://localhost:5000/payments/dpo/callback</RedirectURL>
        <BackURL>http://localhost:5000/payments/dpo/cancel</BackURL>
        <CompanyRefUnique>1</CompanyRefUnique>
        <PTL>5</PTL>
        <customerFirstName>Test</customerFirstName>
        <customerLastName>User</customerLastName>
        <customerEmail>test@example.com</customerEmail>
        <customerPhone>+255712345678</customerPhone>
    </Transaction>
    <Services>
        <Service>
            <ServiceType>{SERVICE_TYPE}</ServiceType>
            <ServiceDescription>Test Payment</ServiceDescription>
            <ServiceDate>{datetime.now().strftime("%Y/%m/%d %H:%M")}</ServiceDate>
        </Service>
    </Services>
</API3G>"""

    print("Sending request to DPO...")
    print()

    try:
        # Send request with proper headers to avoid CloudFront blocking
        headers = {
            "Content-Type": "application/xml",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        response = requests.post(
            API_URL,
            data=xml_request,
            headers=headers,
            timeout=30,
        )

        print(f"Response Status Code: {response.status_code}")
        print()

        # Show raw response first
        print("Raw Response Content:")
        print("-" * 60)
        print(response.text[:1000])  # First 1000 characters
        print("-" * 60)
        print()

        # Try to parse response
        try:
            result = xmltodict.parse(response.content)
            api_response = result.get("API3G", {})

            print("Parsed DPO Response:")
            print("-" * 60)
            for key, value in api_response.items():
                print(f"{key}: {value}")
            print("-" * 60)
            print()
        except Exception as parse_error:
            print(f"⚠️  Could not parse XML response: {parse_error}")
            print(
                "The response is likely HTML (not XML), which means DPO rejected the request"
            )
            print()
            api_response = {}

        # Check result if we got valid XML
        if api_response:
            result_code = api_response.get("Result", "")
            result_explanation = api_response.get("ResultExplanation", "")
        else:
            result_code = ""
            result_explanation = "No valid XML response received"

        if result_code == "000":
            print("✅ SUCCESS! Token created successfully")
            print()
            trans_token = api_response.get("TransToken")
            trans_ref = api_response.get("TransRef")
            payment_url = f"https://secure.3gdirectpay.com/payv3.php?ID={trans_token}"

            print(f"Transaction Token: {trans_token}")
            print(f"Transaction Ref: {trans_ref}")
            print(f"Payment URL: {payment_url}")
            print()
            print("Your DPO credentials are working correctly! ✅")
        elif result_code:
            print(f"❌ FAILED - Code: {result_code}")
            print(f"Error: {result_explanation}")
            print()
            print("Common issues:")
            print("- Company Token is incorrect or inactive")
            print("- Service Type doesn't match your Company Token")
            print("- Account not properly configured with DPO")
            print("- IP restrictions on your DPO account")
        else:
            print("❌ No valid response from DPO")
            print()
            print("Possible issues:")
            print("- DPO API endpoint might be blocking your request")
            print("- Company Token format is incorrect")
            print("- You may need to contact DPO support to activate your account")
            print("- Check if your IP address needs to be whitelisted")

    except requests.RequestException as e:
        print(f"❌ REQUEST FAILED: {str(e)}")
        print()
        print("This could be a network issue or DPO server problem")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()

    print()
    print("=" * 60)


if __name__ == "__main__":
    test_create_token()
