"""
SALESTORM — Start Backend Server
Run: python start.py
"""
import os
import sys

os.environ["DATABASE_URL"]               = "postgresql://salestorm:salestorm_secret@localhost:5432/salestorm"
os.environ["REDIS_URL"]                  = "redis://localhost:6379/0"
os.environ["SECRET_KEY"]                 = "dev_secret_key"
os.environ["ENVIRONMENT"]               = "development"
os.environ["LOG_LEVEL"]                  = "INFO"
os.environ["RESERVATION_EXPIRY_SECONDS"] = "30"
os.environ["QUEUE_ADMISSION_RATE"]       = "50"
os.environ["DEMO_PRODUCT_SKU"]           = "P001"
os.environ["DEMO_INITIAL_INVENTORY"]     = "100"

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

print("=" * 50)
print("  SALESTORM Backend starting...")
print("  API:      http://localhost:8000")
print("  Docs:     http://localhost:8000/docs")
print("  Health:   http://localhost:8000/health")
print("  Metrics:  http://localhost:8000/metrics")
print("=" * 50)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
