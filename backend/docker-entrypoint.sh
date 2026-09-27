#!/bin/sh
set -e

echo "=== Running Database Migrations (Alembic) ==="
alembic upgrade head

echo "=== Seeding Initial Data (Idempotent) ==="
python -m scripts.seed_data || echo "Warning: Seed data skipped or already populated."

echo "=== Starting FastAPI Application ==="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
