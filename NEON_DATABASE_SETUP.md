# Neon Database Scale-to-Zero Handling

## Overview

This application implements comprehensive handling for Neon's scale-to-zero feature, which automatically suspends the database after 5 minutes of inactivity. The solution ensures reliable database connectivity without requiring a paid plan upgrade.

## Problem

Neon's free tier scales databases to zero after 5 minutes of inactivity, causing:
- `SSL connection has been closed unexpectedly` errors
- Connection timeouts on first request after inactivity
- Failed queries when database is asleep

## Solution Architecture

Our multi-layered approach handles scale-to-zero gracefully:

### 1. **Connection Pool Configuration** (`app/config.py`)

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    # Test connections before using them (detects stale connections)
    "pool_pre_ping": True,
    
    # Recycle connections every 5 minutes (before scale-to-zero)
    "pool_recycle": 300,
    
    # Extended timeout for database wake-up (30s instead of default 10s)
    "connect_args": {
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
    
    # Connection pool sizing
    "pool_size": 5,
    "max_overflow": 10,
}
```

**Benefits:**
- `pool_pre_ping`: Validates connections before use
- `pool_recycle`: Prevents stale connections
- Extended `connect_timeout`: Allows time for database to wake up
- TCP keepalives: Maintains connection health

### 2. **Database Wake-up Utilities** (`app/utils/database.py`)

Three key functions:

#### `wake_database(max_retries=3, retry_delay=2.0)`
- Explicitly wakes the database with retry logic
- Handles SSL and connection errors gracefully
- Logs wake-up attempts and success/failure

#### `ensure_database_connection()`
- Quick connection health check
- Falls back to `wake_database()` if check fails
- Use before critical database operations

#### `get_database_status()`
- Returns connection status and latency
- Useful for health checks and monitoring

### 3. **Flask Before-Request Hook** (`app/__init__.py`)

Automatically wakes database before each request:

```python
@app.before_request
def ensure_db_awake():
    # Skip for static files
    if request.endpoint and 'static' in request.endpoint:
        return None
    
    # Ensure database is awake with retry logic
    ensure_database_connection()
    return None
```

**Benefits:**
- Transparent to application code
- Prevents cold-start errors
- Skips unnecessary checks for static files

## Usage

### Automatic (Recommended)

The before-request hook handles everything automatically. Just use your models normally:

```python
from app.models import TicketPrice

# This will work even if database was asleep
tickets = TicketPrice.query.filter_by(is_active=True).all()
```

### Manual (For Critical Operations)

For important operations, explicitly ensure connection:

```python
from app.utils.database import ensure_database_connection

# Ensure database is awake before critical operation
if ensure_database_connection():
    # Perform critical database operation
    result = perform_important_query()
else:
    # Handle connection failure
    log_error("Could not establish database connection")
```

### Health Checks

Monitor database status:

```python
from app.utils.database import get_database_status

status = get_database_status()
print(f"Connected: {status['connected']}")
print(f"Latency: {status['latency_ms']}ms")
```

## Testing

Run the test suite to verify wake-up functionality:

```bash
python test_db_wake.py
```

This tests:
1. Database status checking
2. Wake-up functionality
3. Connection ensuring
4. Query execution

## Configuration

### Environment Variables

Set your Neon connection string:

```bash
DATABASE_URL='postgresql://neondb_owner:password@host.neon.tech/neondb?sslmode=require'
```

The application automatically:
- Detects PostgreSQL URLs
- Converts to `postgresql+psycopg2://` for Flask-SQLAlchemy
- Applies connection pool settings

### Tuning Parameters

Adjust in `app/utils/database.py`:

```python
# Number of retry attempts
wake_database(max_retries=3)

# Delay between retries (seconds)
wake_database(retry_delay=2.0)
```

Adjust in `app/config.py`:

```python
# Recycle connections (should be < 5 minutes for Neon)
"pool_recycle": 300  # seconds

# Connection timeout (allow time for wake-up)
"connect_timeout": 30  # seconds
```

## Performance Considerations

### First Request After Sleep
- Expected latency: 2-5 seconds (database wake-up time)
- The before-request hook handles this transparently
- Users may experience slight delay but no errors

### Subsequent Requests
- Normal latency: <100ms
- Connection pool keeps database warm
- No wake-up delay needed

### Static Files
- Skipped by before-request hook
- No database overhead for CSS, JS, images

## Monitoring

Check logs for wake-up events:

```
⏳ Database appears to be asleep. Attempt 1/3. Retrying in 2s...
✅ Database awakened successfully after 2 attempt(s)
```

Or connection issues:

```
❌ Failed to wake database after 3 attempts: SSL connection has been closed
```

## Best Practices

1. **Don't disable the before-request hook** - It prevents 99% of scale-to-zero issues

2. **Use connection pooling settings** - Already configured in `Config` class

3. **For critical operations** - Use `ensure_database_connection()` explicitly

4. **Monitor latency** - Use `get_database_status()` in health endpoints

5. **Set appropriate timeouts** - 30s is good for Neon's wake-up time

## Troubleshooting

### Still Getting Connection Errors?

1. **Check connection string**: Ensure `DATABASE_URL` is set correctly
2. **Verify psycopg2**: Run `pip install psycopg2-binary`
3. **Check logs**: Look for wake-up attempt failures
4. **Increase retries**: Adjust `max_retries` in `wake_database()`
5. **Increase timeout**: Adjust `connect_timeout` in config

### Database Taking Too Long?

1. **Check Neon status**: Visit Neon dashboard
2. **Verify network**: Test connection with `psql`
3. **Adjust retry delay**: Increase `retry_delay` parameter
4. **Check logs**: Look for specific error messages

### High Latency?

- First request after sleep: Normal (2-5s)
- All requests slow: Check Neon plan and region
- Sporadic slowness: May need to adjust `pool_recycle`

## Dependencies

Ensure these are installed:

```bash
pip install psycopg2-binary
pip install SQLAlchemy>=2.0
pip install Flask-SQLAlchemy
```

## Related Files

- `app/config.py` - Connection pool configuration
- `app/utils/database.py` - Wake-up utilities
- `app/__init__.py` - Before-request hook
- `test_db_wake.py` - Test suite

## References

- [Neon Scale-to-Zero Documentation](https://neon.tech/docs/introduction/scale-to-zero)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [psycopg2 Connection Options](https://www.psycopg.org/docs/module.html#psycopg2.connect)
