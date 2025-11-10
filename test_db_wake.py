"""
Test script to verify database wake-up functionality.
Run this with: python test_db_wake.py
"""

import os

from app import create_app
from app.utils.database import (
    ensure_database_connection,
    get_database_status,
    wake_database,
)

# Create app instance
app = create_app()


def test_database_status():
    """Test getting database status."""
    print("\n" + "=" * 60)
    print("Testing Database Status Check")
    print("=" * 60)

    with app.app_context():
        status = get_database_status()
        print(f"\n📊 Database Status:")
        print(f"   Connected: {status['connected']}")
        print(
            f"   Latency: {status['latency_ms']}ms"
            if status["latency_ms"]
            else "   Latency: N/A"
        )
        print(f"   Error: {status['error']}" if status["error"] else "   Error: None")

        return status["connected"]


def test_wake_database():
    """Test waking up the database."""
    print("\n" + "=" * 60)
    print("Testing Database Wake-up")
    print("=" * 60)

    with app.app_context():
        print("\n⏳ Attempting to wake database...")
        success = wake_database()

        if success:
            print("✅ Database wake-up successful!")
        else:
            print("❌ Database wake-up failed!")

        return success


def test_ensure_connection():
    """Test ensuring database connection."""
    print("\n" + "=" * 60)
    print("Testing Connection Ensuring")
    print("=" * 60)

    with app.app_context():
        print("\n⏳ Ensuring database connection...")
        success = ensure_database_connection()

        if success:
            print("✅ Database connection ensured!")
        else:
            print("❌ Failed to ensure database connection!")

        return success


def test_query():
    """Test running a simple query."""
    print("\n" + "=" * 60)
    print("Testing Database Query")
    print("=" * 60)

    with app.app_context():
        from sqlalchemy import text

        from app.extensions import db

        try:
            print("\n⏳ Running test query...")
            result = db.session.execute(text("SELECT 1 as test")).fetchone()
            print(f"✅ Query successful! Result: {result[0]}")
            return True
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            return False


def main():
    """Run all tests."""
    print("\n")
    print("🔧 Neon Database Wake-up Test Suite")
    print("=" * 60)
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")

    # Run tests
    results = {
        "Status Check": test_database_status(),
        "Wake Database": test_wake_database(),
        "Ensure Connection": test_ensure_connection(),
        "Test Query": test_query(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(results.values())

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
