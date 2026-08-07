"""Sobe a API em SQLite para inspeção local, sem depender do PostgreSQL.

Uso: python scripts/dev_sqlite.py
Não é caminho de produção — o Docker/Coolify continua usando PostgreSQL.
"""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "tmp" / "dev.sqlite3"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
os.environ.setdefault("AI_MOCK_MODE", "true")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:3000")
# Sem isso o `.env` de produção (`COOKIE_DOMAIN=.medquesthub.com.br`) vaza para
# o servidor local: o navegador descarta o cookie de sessão em `localhost` e o
# login responde 200 mas toda rota autenticada volta 401.
os.environ.setdefault("COOKIE_DOMAIN", "")

import uvicorn  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import Base, User, UserPreference  # noqa: E402
from app.services.placement_seed import seed_placement_items  # noqa: E402
from app.services.seed import seed_languages  # noqa: E402

DEV_EMAIL = "dev@befluent.local"
DEV_PASSWORD = "senha-de-desenvolvimento"


def bootstrap() -> None:
    # Alembic, não `create_all`: `create_all` cria tabela que falta mas nunca
    # adiciona coluna a tabela que já existe. Um banco de dev criado antes de
    # uma migration ficaria sem as colunas novas e quebraria em query — a mesma
    # deriva que a migration 0002 teve que consertar em produção.
    from alembic import command
    from alembic.config import Config

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, "head")

    with SessionLocal() as db:
        seed_languages(db)
        seed_placement_items(db)
        from sqlalchemy import select

        if not db.scalar(select(User).where(User.email == DEV_EMAIL)):
            user = User(
                email=DEV_EMAIL,
                name="Dev",
                password_hash=hash_password(DEV_PASSWORD),
            )
            db.add(user)
            db.flush()
            db.add(UserPreference(user_id=user.id))
        db.commit()
    print(f"Banco local: {DB_PATH}")
    print(f"Login de desenvolvimento: {DEV_EMAIL} / {DEV_PASSWORD}")


if __name__ == "__main__":
    bootstrap()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
