"""Garante que revision ids caibam em alembic_version.version_num (VARCHAR(32))."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

# Postgres legado do Coolify ainda usa VARCHAR(32) até a 0005 ampliar.
MAX_LEGACY_VERSION_NUM = 32


def test_all_revision_ids_fit_legacy_varchar32():
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(cfg)
    too_long = []
    for rev in scripts.walk_revisions():
        if len(rev.revision) > MAX_LEGACY_VERSION_NUM:
            too_long.append((rev.revision, len(rev.revision)))
    assert too_long == [], f"Revision ids > {MAX_LEGACY_VERSION_NUM} chars: {too_long}"


def test_heads_is_single_linear_chain():
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(cfg)
    heads = scripts.get_heads()
    assert len(heads) == 1
    assert heads[0] == "0008_teaching_engine_v2"
