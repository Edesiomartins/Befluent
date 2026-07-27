#!/usr/bin/env python3
"""Cria um usuário inicial opcional a partir de variáveis de ambiente.

Com cadastro público habilitado, este script é opcional.
Se INITIAL_ADMIN_* estiver definido e o e-mail ainda não existir, cria a conta.
Não bloqueia múltiplos usuários.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User, UserPreference


def main() -> int:
    email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    name = os.getenv("INITIAL_ADMIN_NAME", "Administrador").strip() or "Administrador"

    if not email or not password:
        print("INITIAL_ADMIN_* não definido — pulando bootstrap. Use o cadastro na interface.")
        return 0

    if len(password) < 8:
        print("AVISO: INITIAL_ADMIN_PASSWORD deve ter pelo menos 8 caracteres. Usuário não criado.")
        return 0

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            print("Usuário inicial já existe; nenhuma alteração feita.")
            return 0

        user = User(email=email, password_hash=hash_password(password), name=name)
        db.add(user)
        db.flush()
        db.add(UserPreference(user_id=user.id))
        db.commit()
        print(f"Usuário inicial criado: {email}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
