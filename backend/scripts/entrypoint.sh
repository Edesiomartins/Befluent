#!/bin/sh
set -e

echo "Running migrations..."
alembic upgrade head

echo "Seeding languages..."
python -c "from app.core.database import SessionLocal; from app.services.seed import seed_languages; db=SessionLocal(); seed_languages(db); db.close()"

echo "Seeding placement items..."
python -c "from app.core.database import SessionLocal; from app.services.placement_seed import seed_placement_items; db=SessionLocal(); print(seed_placement_items(db)); db.close()"

echo "Ensuring initial admin..."
python scripts/create_admin.py

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
