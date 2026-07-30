"""Migration 0003: preservação de dados legados e backfill de níveis CEFR."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings

LEGACY_ROWS = [
    ("ul-1", "iniciante", "A1"),
    ("ul-2", "basico", "A2"),
    ("ul-3", "intermediario", "B1"),
    ("ul-4", "avancado", "C1"),
    ("ul-5", "nao-sei", None),
    ("ul-6", "B2", "B2"),
]


@pytest.fixture
def migrated_legacy_db(tmp_path: Path):
    """Banco no estado 0002 com usuário, idioma e níveis legados; sobe para head."""
    db_path = tmp_path / "legacy_levels.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    os.environ["DATABASE_URL"] = url
    from app.core import config as config_mod

    config_mod.get_settings.cache_clear()

    command.upgrade(cfg, "0002_ensure_schema")

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO languages (id, code, name_pt, native_name, description, "
                "strategy_summary, is_active) "
                "VALUES ('l1', 'en', 'Inglês', 'English', '', '', 1)"
            )
        )
        # Um usuário por rótulo legado: user_languages tem UNIQUE(user_id, language_id).
        for index, (row_id, legacy_level, _) in enumerate(LEGACY_ROWS):
            user_id = f"u{index + 1}"
            conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, name, is_active, created_at, updated_at) "
                    "VALUES (:id, :email, 'hash', 'Legado', 1, '2026-01-01', '2026-01-01')"
                ),
                {"id": user_id, "email": f"legado{index + 1}@befluent.local"},
            )
            conn.execute(
                text(
                    "INSERT INTO user_languages "
                    "(id, user_id, language_id, level_estimate, onboarding_completed, "
                    " diagnostic_completed, is_active, started_at, updated_at) "
                    "VALUES (:id, :user_id, 'l1', :level, 1, 0, 1, '2026-01-01', '2026-01-01')"
                ),
                {"id": row_id, "user_id": user_id, "level": legacy_level},
            )

    command.upgrade(cfg, "head")
    return engine


def test_backfill_converte_rotulos_legados(migrated_legacy_db):
    with migrated_legacy_db.connect() as conn:
        for row_id, _, expected_cefr in LEGACY_ROWS:
            current = conn.execute(
                text("SELECT current_level FROM user_languages WHERE id = :id"), {"id": row_id}
            ).scalar()
            assert current == expected_cefr, f"{row_id} deveria virar {expected_cefr}"


def test_backfill_preserva_rotulo_original(migrated_legacy_db):
    """`level_estimate` continua como registro histórico do que foi declarado."""
    with migrated_legacy_db.connect() as conn:
        for row_id, legacy_level, _ in LEGACY_ROWS:
            stored = conn.execute(
                text("SELECT level_estimate FROM user_languages WHERE id = :id"), {"id": row_id}
            ).scalar()
            assert stored == legacy_level


def test_nivel_desconhecido_fica_pendente(migrated_legacy_db):
    with migrated_legacy_db.connect() as conn:
        source = conn.execute(
            text("SELECT level_source FROM user_languages WHERE id = 'ul-5'")
        ).scalar()
        assert source == "pending"


def test_niveis_convertidos_marcados_como_declarados(migrated_legacy_db):
    """Nível convertido nunca é apresentado como se viesse de teste."""
    with migrated_legacy_db.connect() as conn:
        for row_id in ("ul-1", "ul-2", "ul-3", "ul-4", "ul-6"):
            source = conn.execute(
                text("SELECT level_source FROM user_languages WHERE id = :id"), {"id": row_id}
            ).scalar()
            assert source == "self_declared"
            assert source != "placement_test"


def test_dados_do_usuario_preservados(migrated_legacy_db):
    with migrated_legacy_db.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM users")).scalar() == len(LEGACY_ROWS)
        assert conn.execute(text("SELECT COUNT(*) FROM user_languages")).scalar() == len(LEGACY_ROWS)
        assert conn.execute(
            text("SELECT onboarding_completed FROM user_languages WHERE id = 'ul-1'")
        ).scalar() == 1


def test_tabelas_de_placement_criadas(migrated_legacy_db):
    with migrated_legacy_db.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
    for expected in (
        "placement_tests",
        "placement_items",
        "placement_test_sections",
        "placement_test_answers",
    ):
        assert expected in tables


def test_tabelas_legadas_intactas(migrated_legacy_db):
    """O stub `assessments` não é renomeado nem removido."""
    with migrated_legacy_db.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
    for legacy in ("assessments", "assessment_questions", "assessment_attempts"):
        assert legacy in tables


def test_migration_e_idempotente(migrated_legacy_db, tmp_path):
    """Rodar upgrade de novo em banco já migrado não quebra nem duplica dados."""
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", str(migrated_legacy_db.url))
    command.upgrade(cfg, "head")

    with migrated_legacy_db.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM user_languages")).scalar() == len(LEGACY_ROWS)


def test_0004_adds_provenance_and_preserves_items(tmp_path):
    """A 0004 rodando sobre base com itens: nada é perdido, tudo é rotulado."""
    import sqlite3

    from alembic import command
    from alembic.config import Config

    db = tmp_path / "prov.sqlite3"
    url = f"sqlite:///{db.as_posix()}"
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()

    # Sobe até a 0003 e insere um item como se fosse do seed antigo.
    command.upgrade(config, "0003_levels_placement")
    conn = sqlite3.connect(db)
    conn.execute(
        """
        INSERT INTO placement_items
            (id, external_key, language_code, cefr_level, skill, item_type,
             prompt, difficulty, discrimination, is_active, version,
             created_at, updated_at)
        VALUES ('item-1', 'en-a2-01', 'en', 'A2', 'vocabulary_grammar',
                'multiple_choice', 'Escolha a opção correta.', 0.5, 1.0, 1, 1,
                '2026-01-01 00:00:00', '2026-01-01 00:00:00')
        """
    )
    conn.commit()
    conn.close()

    command.upgrade(config, "0004_item_provenance")

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT prompt, source, license, review_status FROM placement_items WHERE id='item-1'"
    ).fetchone()
    total = conn.execute("SELECT COUNT(*) FROM placement_items").fetchone()[0]
    conn.close()

    assert total == 1, "a migration não pode perder itens existentes"
    assert row[0] == "Escolha a opção correta.", "o conteúdo do item é preservado"
    assert row[1] == "befluent_dev_seed"
    assert row[2] == "proprietary"
    # 'approved' e não 'pending_review': marcar pendente desativaria o teste
    # que já está em produção.
    assert row[3] == "approved"


def test_0004_downgrade_is_noop(tmp_path):
    """Downgrade da 0004 é no-op: colunas de proveniência permanecem."""
    import sqlite3

    from alembic import command
    from alembic.config import Config

    db = tmp_path / "prov_down.sqlite3"
    url = f"sqlite:///{db.as_posix()}"
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()

    command.upgrade(config, "0004_item_provenance")
    command.downgrade(config, "0003_levels_placement")

    conn = sqlite3.connect(db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(placement_items)")}
    conn.close()

    assert "source" in columns
    assert "review_status" in columns
    assert "prompt" in columns
