"""Proveniência e licença por item do banco de nivelamento.

Motivo: hoje não há como saber de onde veio um item. Antes de ingerir qualquer
corpus externo (Tatoeba, listas de frequência, material licenciado), cada item
precisa carregar sua origem — caso contrário fontes se misturam e é impossível
remover uma delas se a licença mudar, ou provar atribuição quando exigida.

Fazer isso depois de misturar dezenas de milhares de frases seria caro e, na
prática, irreversível.

Decisões registradas:

1. Colunas novas em `placement_items`, não tabela `item_sources` separada. Uma
   tabela de fontes só se paga com metadados ricos por fonte (contato, contrato,
   validade); hoje três campos de texto resolvem, e a normalização pode vir
   depois sem perda.

2. `review_status` controla o que chega ao aluno. Item importado entra como
   `pending_review`: a calibragem automática de nível a partir de um corpus é
   heurística, e conteúdo não revisado não deve ser servido como avaliação.
   O seed próprio do projeto entra como `approved`.

3. Backfill dos 100 itens existentes:

       source        -> 'befluent_dev_seed'
       license       -> 'proprietary'
       review_status -> 'approved'   (já estão ativos e em uso; marcar como
                                      pendente desativaria o teste em produção)

   Isso registra o que sempre foi verdade: são itens próprios de
   desenvolvimento, ainda sem validação pedagógica formal. `review_status`
   'approved' significa "liberado para servir", não "validado por especialista".

4. Nada é apagado ou renomeado. Colunas são anuláveis com default, então a
   migration é segura em base com dados.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0004_item_provenance"
down_revision = "0003_levels_placement"
branch_labels = None
depends_on = None


NEW_COLUMNS: list[sa.Column] = [
    # Identificador curto da fonte: 'befluent_dev_seed', 'tatoeba', etc.
    sa.Column("source", sa.String(60), nullable=True),
    # Licença sob a qual o item pode ser usado e redistribuído.
    sa.Column("license", sa.String(80), nullable=True),
    # Texto de atribuição exigido pela licença, quando houver.
    sa.Column("attribution", sa.Text(), nullable=True),
    # Referência na fonte original (ids de frase do Tatoeba, ISBN, URL).
    sa.Column("source_ref", sa.String(200), nullable=True),
    # pending_review | approved | rejected
    sa.Column("review_status", sa.String(20), nullable=True),
]


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("placement_items"):
        # Falha explícita: marcar 0004 como aplicada sem criar colunas deixa o
        # schema inconsistente. Rode 0003 antes (placement_items).
        raise RuntimeError(
            "Migration 0004 exige a tabela placement_items (revision 0003). "
            "Aplique 0003_levels_placement antes de 0004_item_provenance."
        )

    added = []
    for column in NEW_COLUMNS:
        if not _has_column(inspector, "placement_items", column.name):
            op.add_column("placement_items", column)
            added.append(column.name)

    # Backfill: tudo que já existe é o seed próprio de desenvolvimento.
    op.execute(
        sa.text(
            """
            UPDATE placement_items
               SET source = COALESCE(source, 'befluent_dev_seed'),
                   license = COALESCE(license, 'proprietary'),
                   review_status = COALESCE(review_status, 'approved')
            """
        )
    )

    if "source" in added:
        op.create_index(
            "ix_placement_items_source", "placement_items", ["source"], unique=False
        )
    if "review_status" in added:
        op.create_index(
            "ix_placement_items_review_status",
            "placement_items",
            ["review_status"],
            unique=False,
        )


def downgrade() -> None:
    """No-op seguro.

    Metadados de proveniência não devem ser removidos automaticamente: em bases
    com dados, dropar essas colunas apaga auditoria de licença/fonte. Se um
    rollback for realmente necessário, faça-o manualmente com backup.
    """
    return
