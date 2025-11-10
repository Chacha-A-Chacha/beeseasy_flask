"""
Database utilities for handling Neon's scale-to-zero feature.
"""

import time
from typing import Optional

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError


def wake_database(max_retries: int = 3, retry_delay: float = 2.0) -> bool:
    """
    Wake up the Neon database if it's scaled to zero.

    This function performs a simple query to ensure the database is awake
    and ready to handle requests. It includes retry logic to handle the
    initial connection delay when the database is waking up.

    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay in seconds between retry attempts

    Returns:
        bool: True if database is awake and responsive, False otherwise
    """
    from app.extensions import db

    for attempt in range(max_retries):
        try:
            # Simple query to wake up the database
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                connection.commit()

            if attempt > 0:
                current_app.logger.info(
                    f"✅ Database awakened successfully after {attempt + 1} attempt(s)"
                )
            return True

        except (OperationalError, DBAPIError) as e:
            error_msg = str(e)

            # Check if it's a connection/SSL error (database waking up)
            if (
                "SSL connection has been closed" in error_msg
                or "connection" in error_msg.lower()
                or "timeout" in error_msg.lower()
            ):
                if attempt < max_retries - 1:
                    current_app.logger.warning(
                        f"⏳ Database appears to be asleep. Attempt {attempt + 1}/{max_retries}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    current_app.logger.error(
                        f"❌ Failed to wake database after {max_retries} attempts: {error_msg}"
                    )
                    return False
            else:
                # Different error, don't retry
                current_app.logger.error(f"❌ Database error: {error_msg}")
                return False

        except Exception as e:
            current_app.logger.error(f"❌ Unexpected error waking database: {str(e)}")
            return False

    return False


def ensure_database_connection() -> bool:
    """
    Ensure database connection is active and healthy.

    This function should be called before critical database operations
    to prevent connection errors due to scale-to-zero.

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    from app.extensions import db

    try:
        # Try a quick connection test
        db.session.execute(text("SELECT 1"))
        return True
    except Exception:
        # If connection fails, try to wake the database
        return wake_database()


def get_database_status() -> dict:
    """
    Get the current database connection status.

    Returns:
        dict: Status information including connection state and latency
    """
    from app.extensions import db

    status = {"connected": False, "latency_ms": None, "error": None}

    try:
        start_time = time.time()
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        end_time = time.time()

        status["connected"] = True
        status["latency_ms"] = round((end_time - start_time) * 1000, 2)

    except Exception as e:
        status["error"] = str(e)

    return status
