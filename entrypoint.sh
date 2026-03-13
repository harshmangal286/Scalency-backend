#!/bin/bash
# entrypoint.sh – runs once before Uvicorn starts.
# Handles DB table creation so it never races across multiple worker processes.

set -e

echo "[entrypoint] Waiting for PostgreSQL to be ready..."

# Retry loop – Postgres may still be initialising when this container starts
until python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
" 2>/dev/null; do
  echo "[entrypoint] Database not ready yet, retrying in 2s..."
  sleep 2
done

echo "[entrypoint] Database is up. Running table creation..."
python -c "from app.core.database import create_tables; create_tables()"
echo "[entrypoint] Tables are ready."

echo "[entrypoint] Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
