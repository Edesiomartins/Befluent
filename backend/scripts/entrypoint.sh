#!/bin/sh
set -e
echo "Running migrations..."
alembic upgrade head
echo "Seeding languages..."
python -c "from app.core.database import SessionLocal; from app.services.seed import seed_languages; db=SessionLocal(); seed_languages(db); db.close()"
echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
