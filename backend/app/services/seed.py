from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Language

LANGUAGES = [
    (
        "en",
        "Inglês",
        "English",
        None,
        "Inglês internacional",
        "Ênfase em conversação, escuta e vocabulário frequente.",
    ),
    (
        "es-ES",
        "Espanhol da Espanha",
        "Español",
        "Espanha",
        "Espanhol europeu, pronúncia, uso cotidiano e vosotros.",
        "Ênfase no espanhol europeu, vosotros, pronúncia e uso cotidiano.",
    ),
    (
        "fr",
        "Francês",
        "Français",
        None,
        "Francês padrão",
        "Ênfase em compreensão oral, liaison e comunicação prática.",
    ),
    (
        "ja",
        "Japonês",
        "日本語",
        None,
        "Japonês padrão",
        "Progressão por escrita, partículas, escuta e níveis de formalidade.",
    ),
    (
        "zh-CN",
        "Mandarim",
        "中文",
        "Simplificado",
        "Mandarim simplificado",
        "Ênfase em tons, pinyin, caracteres simplificados e comunicação.",
    ),
]


def seed_languages(db: Session) -> None:
    """Insere idiomas ausentes e atualiza rótulos oficiais sem apagar registros."""
    for code, name_pt, native, variant, description, strategy in LANGUAGES:
        existing = db.scalar(select(Language).where(Language.code == code))
        if existing is None:
            db.add(
                Language(
                    code=code,
                    name_pt=name_pt,
                    native_name=native,
                    variant_note=variant,
                    description=description,
                    strategy_summary=strategy,
                )
            )
            continue
        # Atualização não destrutiva de metadados oficiais
        existing.name_pt = name_pt
        existing.native_name = native
        existing.variant_note = variant
        existing.description = description
        existing.strategy_summary = strategy
        existing.is_active = True

    # Duplicatas de es-ES: manter o registro mais antigo ativo; desativar extras
    # sem DELETE (pode haver FKs).
    es_rows = list(
        db.scalars(select(Language).where(Language.code == "es-ES").order_by(Language.id)).all()
    )
    if len(es_rows) > 1:
        keeper = es_rows[0]
        keeper.name_pt = "Espanhol da Espanha"
        keeper.native_name = "Español"
        keeper.variant_note = "Espanha"
        keeper.description = "Espanhol europeu, pronúncia, uso cotidiano e vosotros."
        keeper.is_active = True
        for dup in es_rows[1:]:
            # Evita conflito de UNIQUE(code): move codigo temporario e desativa
            if dup.id != keeper.id:
                dup.code = f"es-ES-dup-{dup.id[:8]}"
                dup.is_active = False

    db.commit()
