"""Teaching Engine — núcleo pedagógico entre currículo e atividades.

Introduz `LearningObjective` (catálogo por idioma+nível, como `GrammarTopic`)
e o rastro de aprendizagem por aluno: `UserObjectiveProgress`,
`LearningAttempt`, `LearningEvidence`, `LearningError`, `Remediation`.

Aditiva: cria seis tabelas novas e uma coluna nova (`curriculum_blocks.
objective_id`, nullable). Sem DROP nem ALTER de nada existente; todo bloco já
criado fica com `objective_id=NULL` e continua funcionando exatamente como
antes — `block.status == "completed"` não passa a significar domínio.

Downgrade remove apenas o que esta revisão criou.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0007_teaching_engine"
down_revision = "0006_curriculum"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "learning_objectives"):
        op.create_table(
            "learning_objectives",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("language_id", sa.String(length=36), sa.ForeignKey("languages.id"), nullable=False),
            sa.Column("level", sa.String(length=10), nullable=False),
            sa.Column("code", sa.String(length=40), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("can_do", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("skill_focus", sa.String(length=30), nullable=False),
            sa.Column("prerequisites_json", sa.JSON(), nullable=False),
            sa.Column("target_vocabulary_json", sa.JSON(), nullable=False),
            sa.Column("target_patterns_json", sa.JSON(), nullable=False),
            sa.Column("pronunciation_focus_json", sa.JSON(), nullable=False),
            sa.Column("mastery_policy_json", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("language_id", "code", name="uq_learning_objective_code"),
        )
        op.create_index("ix_learning_objectives_language_id", "learning_objectives", ["language_id"])
        op.create_index("ix_learning_objectives_level", "learning_objectives", ["level"])
        op.create_index("ix_learning_objectives_skill_focus", "learning_objectives", ["skill_focus"])
        op.create_index("ix_learning_objectives_is_active", "learning_objectives", ["is_active"])

    if not _has_table(inspector, "user_objective_progress"):
        op.create_table(
            "user_objective_progress",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_language_id", sa.String(length=36), sa.ForeignKey("user_languages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("objective_id", sa.String(length=36), sa.ForeignKey("learning_objectives.id", ondelete="CASCADE"), nullable=False),
            sa.Column("state", sa.String(length=30), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("mastered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_reasons_json", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_language_id", "objective_id", name="uq_user_objective_progress"),
        )
        op.create_index("ix_user_objective_progress_user_language_id", "user_objective_progress", ["user_language_id"])
        op.create_index("ix_user_objective_progress_objective_id", "user_objective_progress", ["objective_id"])
        op.create_index("ix_user_objective_progress_state", "user_objective_progress", ["state"])

    if not _has_table(inspector, "learning_attempts"):
        op.create_table(
            "learning_attempts",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_language_id", sa.String(length=36), sa.ForeignKey("user_languages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("objective_id", sa.String(length=36), sa.ForeignKey("learning_objectives.id", ondelete="CASCADE"), nullable=False),
            sa.Column("curriculum_block_id", sa.String(length=36), sa.ForeignKey("curriculum_blocks.id", ondelete="SET NULL"), nullable=True),
            sa.Column("lesson_id", sa.String(length=36), sa.ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True),
            sa.Column("activity_type", sa.String(length=50), nullable=False),
            sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("student_response", sa.Text(), nullable=True),
            sa.Column("result", sa.String(length=20), nullable=False),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("provider", sa.String(length=30), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_learning_attempts_user_language_id", "learning_attempts", ["user_language_id"])
        op.create_index("ix_learning_attempts_objective_id", "learning_attempts", ["objective_id"])
        op.create_index("ix_learning_attempts_curriculum_block_id", "learning_attempts", ["curriculum_block_id"])

    if not _has_table(inspector, "learning_evidence"):
        op.create_table(
            "learning_evidence",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_language_id", sa.String(length=36), sa.ForeignKey("user_languages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("objective_id", sa.String(length=36), sa.ForeignKey("learning_objectives.id", ondelete="CASCADE"), nullable=False),
            sa.Column("attempt_id", sa.String(length=36), sa.ForeignKey("learning_attempts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("evidence_type", sa.String(length=40), nullable=False),
            sa.Column("is_transfer", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_learning_evidence_user_language_id", "learning_evidence", ["user_language_id"])
        op.create_index("ix_learning_evidence_objective_id", "learning_evidence", ["objective_id"])
        op.create_index("ix_learning_evidence_attempt_id", "learning_evidence", ["attempt_id"])

    if not _has_table(inspector, "learning_errors"):
        op.create_table(
            "learning_errors",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_language_id", sa.String(length=36), sa.ForeignKey("user_languages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("objective_id", sa.String(length=36), sa.ForeignKey("learning_objectives.id", ondelete="SET NULL"), nullable=True),
            sa.Column("attempt_id", sa.String(length=36), sa.ForeignKey("learning_attempts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("category", sa.String(length=40), nullable=False),
            sa.Column("original", sa.Text(), nullable=False),
            sa.Column("expected", sa.Text(), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("language_feature", sa.String(length=120), nullable=True),
            sa.Column("recurring", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("occurrences", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_learning_errors_user_language_id", "learning_errors", ["user_language_id"])
        op.create_index("ix_learning_errors_objective_id", "learning_errors", ["objective_id"])
        op.create_index("ix_learning_errors_category", "learning_errors", ["category"])
        op.create_index("ix_learning_errors_resolved", "learning_errors", ["resolved"])

    if not _has_table(inspector, "remediations"):
        op.create_table(
            "remediations",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("error_id", sa.String(length=36), sa.ForeignKey("learning_errors.id", ondelete="CASCADE"), nullable=False),
            sa.Column("action", sa.String(length=30), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("next_attempt_id", sa.String(length=36), sa.ForeignKey("learning_attempts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_remediations_error_id", "remediations", ["error_id"])

    if not _has_column(inspector, "curriculum_blocks", "objective_id"):
        # `batch_alter_table`: SQLite não altera constraints (inclusive FK) via
        # ALTER TABLE direto de forma confiável — produção é Postgres, mas o
        # teste local roda em SQLite.
        with op.batch_alter_table("curriculum_blocks") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "objective_id",
                    sa.String(length=36),
                    sa.ForeignKey(
                        "learning_objectives.id",
                        ondelete="SET NULL",
                        name="fk_curriculum_blocks_objective_id",
                    ),
                    nullable=True,
                )
            )
        op.create_index("ix_curriculum_blocks_objective_id", "curriculum_blocks", ["objective_id"])


def downgrade() -> None:
    """Remove apenas o que esta revisão criou, na ordem das dependências."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_column(inspector, "curriculum_blocks", "objective_id"):
        # O índice sai primeiro, como operação avulsa: dentro do mesmo bloco
        # batch ele confunde a reconstrução da tabela (o modo batch tenta
        # recriar todo índice refletido, inclusive um que aponta para a coluna
        # sendo removida). `batch_alter_table` só entra para o DROP COLUMN em
        # si, que o SQLite não suporta via ALTER direto numa coluna com FK
        # (o teste local roda em SQLite; produção é Postgres).
        op.drop_index("ix_curriculum_blocks_objective_id", table_name="curriculum_blocks")
        with op.batch_alter_table("curriculum_blocks") as batch_op:
            batch_op.drop_column("objective_id")

    for table in (
        "remediations",
        "learning_errors",
        "learning_evidence",
        "learning_attempts",
        "user_objective_progress",
        "learning_objectives",
    ):
        if _has_table(inspector, table):
            op.drop_table(table)
