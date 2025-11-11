# cPanel Deployment Troubleshooting Guide

## Database Connection Error - "Connection Refused"

### Problem
Your Flask app on cPanel cannot connect to the Neon PostgreSQL database, showing error:
```
psycopg2.OperationalError: connection to server at "ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech" 
(3.218.140.61), port 5432 failed: Connection refused
```

### Root Causes & Solutions

---

## 1. Neon Database Auto-Suspend (Most Common)

**Problem:** Neon free tier databases automatically suspend after 5 minutes of inactivity.

**Solution:**

### A. Wake Up the Database
1. Go to [Neon Console](https://console.neon.tech)
2. Select your project: `ep-still-hill-adwc4dgs-pooler`
3. Click on your database
4. Click **"Resume"** or run any query in the SQL Editor
5. Wait 10-20 seconds for database to wake up
6. Restart your cPanel Python app

### B. Upgrade to Paid Plan (Recommended for Production)
- Neon Pro plan ($19/month) keeps databases always active
- No auto-suspend
- Better for production workloads

---

## 2. IP Allowlist Restrictions

**Problem:** Neon might be blocking connections from your cPanel server's IP address.

**Solution:**

### Find Your cPanel Server IP
```bash
# SSH into cPanel and run:
curl ifconfig.me
# Or
hostname -I
```

### Add IP to Neon Allowlist
1. Go to [Neon Console](https://console.neon.tech)
2. Navigate to your project
3. Click **Settings** → **IP Allow**
4. Add your cPanel server IP address
5. Click **Save**

**Note:** Some Neon plans require allowlist. Check your plan features.

---

## 3. Firewall Blocking Outbound Connections

**Problem:** cPanel server firewall blocks outbound connections to port 5432.

**Solution:**

### Contact Your Hosting Provider
Ask them to:
1. Allow outbound connections to `*.neon.tech` on port 5432
2. Whitelist these Neon IP ranges:
   - `3.218.140.61`
   - `44.198.216.75`
   - `54.156.15.30`

### Test Connection from cPanel
```bash
# SSH into cPanel and test:
nc -zv ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech 5432

# Or using telnet:
telnet ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech 5432

# Expected output if working:
# Connection to ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech 5432 port [tcp/postgresql] succeeded!
```

---

## 4. Incorrect Database Credentials

**Problem:** DATABASE_URL environment variable is incorrect or missing.

**Solution:**

### Verify Environment Variables on cPanel
1. Log into cPanel
2. Go to **Setup Python App**
3. Click **Edit** on your app
4. Check **Environment Variables** section
5. Verify `DATABASE_URL` is set correctly

### Get Correct Connection String from Neon
1. Go to [Neon Console](https://console.neon.tech)
2. Select your project
3. Click **Connection Details**
4. Copy the **Pooled connection** string (recommended for production)
5. Format should be:
   ```
   postgresql://username:password@ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech/dbname?sslmode=require
   ```

### Update cPanel Environment Variable
```bash
DATABASE_URL=postgresql://username:password@ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech/dbname?sslmode=require
```

**Important:** Use the **pooled connection** string (has `-pooler` in hostname) for better performance.

---

## 5. SSL/TLS Issues

**Problem:** SSL connection issues between cPanel and Neon.

**Solution:**

### Ensure SSL Mode in Connection String
Your `DATABASE_URL` must include `sslmode=require`:
```
postgresql://user:pass@host/db?sslmode=require
```

### Install Required SSL Certificates (if needed)
```bash
# On cPanel via SSH:
pip install certifi
```

---

## 6. cPanel Python App Configuration

**Problem:** App crashes before it can handle requests.

**Solution (Already Fixed in Code):**

The code has been updated to gracefully handle database connection errors at startup:
- `app/__init__.py` now has try/except in `ensure_tables_exist()`
- Database will wake up on first request instead of blocking startup
- Retry logic built into `before_request` handler

### Verify Passenger WSGI Configuration

Check `/home/pollinat/production/beeseasy/passenger_wsgi.py`:
```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/pollinat/production/beeseasy'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment to production
os.environ['FLASK_ENV'] = 'production'

# Import your Flask app
from run import app as application
```

---

## Quick Diagnostic Checklist

Run these checks in order:

### ✅ 1. Check if Neon database is active
- [ ] Log into Neon Console
- [ ] Verify database status shows "Active" (not "Idle" or "Suspended")
- [ ] Click "Resume" if suspended

### ✅ 2. Test database connection locally
```bash
# From your development machine:
psql "postgresql://username:password@ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech/dbname?sslmode=require"
```

### ✅ 3. Test from cPanel server
```bash
# SSH into cPanel:
nc -zv ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech 5432
```

### ✅ 4. Check cPanel error logs
```bash
# View recent errors:
tail -100 /home/pollinat/logs/beeseasy_error.log
```

### ✅ 5. Verify environment variables
- [ ] `DATABASE_URL` is set in cPanel Python App settings
- [ ] `FLASK_ENV=production`
- [ ] `SECRET_KEY` is set

### ✅ 6. Restart the app
- [ ] In cPanel → Setup Python App → Click "Restart"
- [ ] Wait 30 seconds
- [ ] Try accessing the website

---

## Recommended Production Setup

### 1. Use Neon Pooled Connection
Always use the connection string with `-pooler`:
```
postgresql://user:pass@ep-still-hill-adwc4dgs-pooler.c-2.us-east-1.aws.neon.tech/db
```

### 2. Set Connection Pool Parameters
In your production config or environment:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 5,
    'max_overflow': 10,
    'pool_timeout': 30,
    'pool_recycle': 1800,  # Recycle connections every 30 minutes
    'pool_pre_ping': True,  # Verify connections before using
}
```

### 3. Enable Database Wake-up Monitoring
The app already includes:
- ✅ Automatic retry on connection failure
- ✅ Database wake-up before each request
- ✅ Graceful error handling at startup

### 4. Monitor Your Logs
Set up log monitoring for these patterns:
- `"Database appears to be asleep"`
- `"Failed to establish database connection"`
- `"Connection refused"`

---

## Alternative: Use cPanel MySQL Instead

If Neon connection issues persist, consider using cPanel's built-in MySQL:

### Pros:
- ✅ No external connection needed
- ✅ No firewall issues
- ✅ Always available (no auto-suspend)
- ✅ Included with cPanel hosting

### Cons:
- ❌ Need to migrate from PostgreSQL to MySQL
- ❌ Some PostgreSQL-specific features won't work
- ❌ Would need to update models and migrations

### Quick Migration Steps (if needed):
1. Create MySQL database in cPanel
2. Update `DATABASE_URL` to MySQL format:
   ```
   mysql+pymysql://user:pass@localhost/dbname
   ```
3. Install MySQL driver: `pip install pymysql`
4. Run migrations: `flask db upgrade`
5. Seed data: `flask seed`

---

## Getting Help

### 1. Check Neon Status
- [Neon Status Page](https://status.neon.tech)

### 2. Contact Support
- **Neon Support:** support@neon.tech or via Discord
- **cPanel Hosting Support:** Contact your hosting provider

### 3. Debug Locally First
Always test database connection from your local machine before deploying:
```bash
# Test connection:
psql "$DATABASE_URL"

# Run app locally with production DB:
FLASK_ENV=production flask run
```

---

## Recent Code Changes (Applied)

The following fixes have been applied to handle database connection issues:

### `app/__init__.py`
- ✅ Added try/except to `ensure_tables_exist()` 
- ✅ App no longer crashes if database is unreachable at startup
- ✅ Enhanced `ensure_db_awake()` with error handling
- ✅ Database connection retries happen on first request

### Benefits:
- App starts successfully even if database is sleeping
- First request wakes up the database automatically
- Graceful degradation instead of crash loops

---

## Next Steps

1. **Immediate:** Wake up Neon database via console
2. **Short-term:** Verify cPanel server IP is whitelisted
3. **Long-term:** Consider Neon Pro plan for always-on database
4. **Alternative:** Evaluate cPanel MySQL for simpler deployment

---

**Last Updated:** December 2024  
**Related Files:** 
- `app/__init__.py` (startup logic)
- `app/utils/database.py` (connection utilities)
- `app/config.py` (database configuration)