"""
SALESTORM Setup Script — uses psycopg2 directly, no psql needed.
Run: python setup_db.py
"""
import sys
import os

print("=" * 50)
print("  SALESTORM — Database Setup")
print("=" * 50)

# ── Step 1: Get postgres superuser password ───────────────────────────────────
import getpass
print("\nEnter your PostgreSQL superuser (postgres) password:")
pg_password = getpass.getpass("postgres password: ")

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ── Step 2: Connect as superuser and create user + database ───────────────────
print("\n[1] Connecting to PostgreSQL as superuser...")
try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="postgres",
        user="postgres",
        password=pg_password,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    print("    Connected OK")
except Exception as e:
    print(f"\n  ERROR: Cannot connect to PostgreSQL: {e}")
    print("\n  Make sure PostgreSQL 18 is running.")
    print("  Open Windows Services (services.msc) and start 'postgresql-x64-18'")
    sys.exit(1)

print("\n[2] Creating user 'salestorm'...")
try:
    cur.execute("CREATE USER salestorm WITH PASSWORD 'salestorm_secret';")
    print("    User created.")
except psycopg2.errors.DuplicateObject:
    print("    User already exists — skipping.")

print("\n[3] Creating database 'salestorm'...")
try:
    cur.execute("CREATE DATABASE salestorm OWNER salestorm;")
    print("    Database created.")
except psycopg2.errors.DuplicateDatabase:
    print("    Database already exists — skipping.")

print("\n[4] Granting privileges...")
cur.execute("GRANT ALL PRIVILEGES ON DATABASE salestorm TO salestorm;")
cur.execute("ALTER USER salestorm CREATEDB;")
print("    Privileges granted.")

cur.close()
conn.close()

# ── Step 3: Test the new connection ───────────────────────────────────────────
print("\n[5] Testing salestorm connection...")
try:
    conn2 = psycopg2.connect(
        "postgresql://salestorm:salestorm_secret@localhost:5432/salestorm"
    )
    conn2.close()
    print("    Connection OK")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

# ── Step 4: Create tables and seed demo data ──────────────────────────────────
print("\n[6] Creating tables and seeding demo data...")

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

os.environ["DATABASE_URL"] = "postgresql://salestorm:salestorm_secret@localhost:5432/salestorm"
os.environ["REDIS_URL"]    = "redis://localhost:6379/0"
os.environ["SECRET_KEY"]   = "dev_secret_key"
os.environ["ENVIRONMENT"]  = "development"
os.environ["LOG_LEVEL"]    = "INFO"
os.environ["RESERVATION_EXPIRY_SECONDS"] = "30"
os.environ["QUEUE_ADMISSION_RATE"]       = "50"
os.environ["DEMO_PRODUCT_SKU"]           = "P001"
os.environ["DEMO_INITIAL_INVENTORY"]     = "100"

try:
    from app.core.init_db import init_db
    init_db()
    print("    Tables and demo data created OK")
except Exception as e:
    print(f"    WARNING: {e}")
    print("    (Redis may not be running — that is OK for now, tables are still created)")

print("\n" + "=" * 50)
print("  Setup complete!")
print()
print("  Next steps:")
print("  1. Start backend:  python start.py")
print("  2. Start frontend: cd frontend && npm install && npm run dev")
print("=" * 50)
