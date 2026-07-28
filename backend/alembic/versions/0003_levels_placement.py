"""Níveis CEFR e teste de nivelamento (incremental, não destrutivo).

Cria as tabelas do placement test e amplia `user_languages` com o perfil
linguístico por competência.

Decisões registradas:

1. Os sete níveis CEFR são constantes em `app.core.levels`, não uma tabela
   `language_levels`. São estáticos, não referenciados por FK e uma tabela
   exigiria migration + seed para sete linhas imutáveis.

2. Não foi criada tabela `user_language_profiles`. `user_languages` já é a
   relação usuário↔idioma; duplicá-la criaria duas fontes de verdade. As
   colunas de nível foram adicionadas nela.

3. O stub legado `assessments` / `assessment_questions` / `assessment_attempts`
   permanece intacto. Nada é renomeado nem removido.

4. Backfill de `level_estimate` (rótulos legados) para `current_level` (CEFR):

       iniciante      -> A1   (A1 e não PRE_A1: quem se declarou "iniciante"
                               no onboarding antigo não tinha a opção
                               "iniciante absoluto", então A1 é o piso menos
                               agressivo; o teste corrige depois)
       basico         -> A2
       intermediario  -> B1
       avancado       -> C1
       nao-sei        -> NULL, com level_source = 'pending'

   `level_estimate` NÃO é apagado: fica como registro histórico do que o
   usuário declarou. `level_source` dos convertidos é 'self_declared', o que
   deixa explícito no dashboard que o nível não veio de teste.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003_levels_placement"
down_revision = "0002_ensure_schema"
branch_labels = None
depends_on = None


NEW_USER_LANGUAGE_COLUMNS: list[sa.Column] = [
    sa.Column("current_level", sa.String(10), nullable=True),
    sa.Column("level_source", sa.String(30), nullable=True),
    sa.Column("level_assessed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("placement_test_id", sa.String(36), nullable=True),
    sa.Column("vocabulary_grammar_level", sa.String(10), nullable=True),
    sa.Column("reading_level", sa.String(10), nullable=True),
    sa.Column("listening_level", sa.String(10), nullable=True),
    sa.Column("writing_level", sa.String(10), nullable=True),
    sa.Column("speaking_level", sa.String(10), nullable=True),
    sa.Column("confidence_score", sa.Float(), nullable=True),
    sa.Column("recommendations_json", sa.JSON(), nullable=True),
]

# rotulo legado -> (codigo CEFR ou None, level_source)
LEGACY_BACKFILL: list[tuple[str, str | None, str]] = [
    ("iniciante", "A1", "self_declared"),
    ("basico", "A2", "self_declared"),
    ("básico", "A2", "self_declared"),
    ("intermediario", "B1", "self_declared"),
    ("intermediário", "B1", "self_declared"),
    ("avancado", "C1", "self_declared"),
    ("avançado", "C1", "self_declared"),
    ("nao-sei", None, "pending"),
    ("não-sei", None, "pending"),
]


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspector.get_columns(table)}


def _create_table_if_missing(inspector, name: str, *columns) -> bool:
    if inspector.has_table(name):
        return False
    op.create_table(name, *columns)
    return True


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ---------------------------------------------------------------- tabelas
    created = _create_table_if_missing(
        inspector,
        "placement_tests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_code", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(30), nullable=False, server_default="placement_test"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_level_band", sa.String(10), nullable=True),
        sa.Column("overall_level", sa.String(10), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    if created:
        op.create_index("ix_placement_tests_user_id", "placement_tests", ["user_id"])
        op.create_index("ix_placement_tests_language_code", "placement_tests", ["language_code"])
        op.create_index("ix_placement_tests_status", "placement_tests", ["status"])
    inspector = inspect(bind)

    created = _create_table_if_missing(
        inspector,
        "placement_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_key", sa.String(80), nullable=False),
        sa.Column("language_code", sa.String(10), nullable=False),
        sa.Column("cefr_level", sa.String(10), nullable=False),
        sa.Column("skill", sa.String(30), nullable=False),
        sa.Column("item_type", sa.String(40), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("passage", sa.Text(), nullable=True),
        sa.Column("options_json", sa.JSON(), nullable=True),
        sa.Column("correct_answer_json", sa.JSON(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.String(500), nullable=True),
        sa.Column("audio_script", sa.Text(), nullable=True),
        sa.Column("rubric_json", sa.JSON(), nullable=True),
        sa.Column("difficulty", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("discrimination", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("language_code", "external_key", name="uq_placement_items_lang_key"),
    )
    if created:
        op.create_index("ix_placement_items_external_key", "placement_items", ["external_key"])
        op.create_index("ix_placement_items_language_code", "placement_items", ["language_code"])
        op.create_index("ix_placement_items_cefr_level", "placement_items", ["cefr_level"])
        op.create_index("ix_placement_items_skill", "placement_items", ["skill"])
        op.create_index("ix_placement_items_is_active", "placement_items", ["is_active"])
    inspector = inspect(bind)

    created = _create_table_if_missing(
        inspector,
        "placement_test_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("test_id", sa.String(36), sa.ForeignKey("placement_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill", sa.String(30), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("estimated_level", sa.String(10), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="assessed"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("test_id", "skill", name="uq_placement_sections_test_skill"),
    )
    if created:
        op.create_index("ix_placement_test_sections_test_id", "placement_test_sections", ["test_id"])
    inspector = inspect(bind)

    created = _create_table_if_missing(
        inspector,
        "placement_test_answers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("test_id", sa.String(36), sa.ForeignKey("placement_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("placement_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill", sa.String(30), nullable=False),
        sa.Column("cefr_level", sa.String(10), nullable=False),
        sa.Column("answer_json", sa.JSON(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("raw_score", sa.Float(), nullable=True),
        sa.Column("normalized_score", sa.Float(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("evaluated_by", sa.String(30), nullable=False, server_default="auto"),
        sa.Column("feedback_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("test_id", "item_id", name="uq_placement_answers_test_item"),
    )
    if created:
        op.create_index("ix_placement_test_answers_test_id", "placement_test_answers", ["test_id"])
        op.create_index("ix_placement_test_answers_item_id", "placement_test_answers", ["item_id"])
    inspector = inspect(bind)

    # ------------------------------------------- colunas em user_languages
    for column in NEW_USER_LANGUAGE_COLUMNS:
        if not _has_column(inspector, "user_languages", column.name):
            op.add_column(
                "user_languages",
                sa.Column(column.name, column.type, nullable=True),
            )
    inspector = inspect(bind)

    if not any(
        idx.get("name") == "ix_user_languages_placement_test_id"
        for idx in inspector.get_indexes("user_languages")
    ):
        op.create_index(
            "ix_user_languages_placement_test_id", "user_languages", ["placement_test_id"]
        )

    # ------------------------------------------------------------- backfill
    user_languages = sa.table(
        "user_languages",
        sa.column("level_estimate", sa.String),
        sa.column("current_level", sa.String),
        sa.column("level_source", sa.String),
    )

    for legacy_label, cefr_code, source in LEGACY_BACKFILL:
        op.execute(
            user_languages.update()
            .where(
                sa.and_(
                    sa.func.lower(sa.column("level_estimate")) == legacy_label,
                    sa.column("current_level").is_(None),
                )
            )
            .values(current_level=cefr_code, level_source=source)
        )

    # Registros que já usavam o código CEFR diretamente.
    op.execute(
        user_languages.update()
        .where(
            sa.and_(
                sa.column("current_level").is_(None),
                sa.func.upper(sa.column("level_estimate")).in_(
                    ["PRE_A1", "A1", "A2", "B1", "B2", "C1", "C2"]
                ),
            )
        )
        .values(current_level=sa.func.upper(sa.column("level_estimate")), level_source="self_declared")
    )

    # Sem nível declarado: fica pendente (o dashboard recomenda o teste).
    op.execute(
        user_languages.update()
        .where(sa.column("level_source").is_(None))
        .values(level_source="pending")
    )


def downgrade() -> None:
    """No-op seguro: DROP removeria níveis e resultados de teste já coletados."""
    pass
