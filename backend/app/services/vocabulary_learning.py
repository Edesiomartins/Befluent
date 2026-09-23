"""Matrícula idempotente de conteúdo no ciclo de aprendizagem lexical."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import UserLanguage, VocabularyExample, VocabularyItem
from app.services import memory_engine


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _term_text(value: str | None) -> str | None:
    """Remove apenas espaço externo; espaços internos pertencem ao termo."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _user_language_lock_statement(user_language_id: str):
    return (
        select(UserLanguage)
        .where(UserLanguage.id == user_language_id)
        .with_for_update()
    )


def enroll_item(
    db: Session,
    *,
    user_language_id: str,
    term: str,
    translation_pt: str,
    reading_or_pinyin: str | None = None,
    notes: str | None = None,
    examples: Iterable[Mapping[str, str | None]] | None = None,
) -> VocabularyItem:
    """Matricula termo e exemplos sem depender de unique em dados antigos."""
    normalized_term = _term_text(term)
    normalized_translation = _clean(translation_pt)
    if not normalized_term or not normalized_translation:
        raise APIError(422, "invalid_vocabulary_item", "Termo e tradução são obrigatórios.")
    # Serializa matrículas do mesmo perfil antes de repetir a busca normalizada.
    # PostgreSQL emite SELECT ... FOR UPDATE; SQLite ignora o lock em testes.
    if db.scalar(_user_language_lock_statement(user_language_id)) is None:
        raise APIError(404, "user_language_not_found", "Perfil de idioma não encontrado.")

    item = db.scalar(
        select(VocabularyItem)
        .where(
            VocabularyItem.user_language_id == user_language_id,
            func.lower(func.trim(VocabularyItem.term)) == normalized_term.casefold(),
        )
        .order_by(VocabularyItem.created_at.asc(), VocabularyItem.id.asc())
        .limit(1)
    )
    if item is None:
        item = VocabularyItem(
            user_language_id=user_language_id,
            term=normalized_term,
            translation_pt=normalized_translation,
            reading_or_pinyin=_clean(reading_or_pinyin),
            notes=_clean(notes),
        )
        db.add(item)
        db.flush()
    else:
        if not item.translation_pt:
            item.translation_pt = normalized_translation
        if not item.reading_or_pinyin and reading_or_pinyin:
            item.reading_or_pinyin = _clean(reading_or_pinyin)
        if not item.notes and notes:
            item.notes = _clean(notes)

    for raw in examples or ():
        example_text = _clean(raw.get("example_text"))
        if not example_text:
            continue
        translation = _clean(raw.get("translation_pt"))
        existing = db.scalar(
            select(VocabularyExample)
            .where(
                VocabularyExample.vocabulary_item_id == item.id,
                VocabularyExample.example_text == example_text,
                VocabularyExample.translation_pt == translation,
            )
            .order_by(VocabularyExample.id.asc())
            .limit(1)
        )
        if existing is None:
            db.add(
                VocabularyExample(
                    vocabulary_item_id=item.id,
                    example_text=example_text,
                    translation_pt=translation,
                    audio_ref=_clean(raw.get("audio_ref")),
                )
            )

    db.flush()
    memory_engine.update_vocabulary_memory(db, item=item)
    return item


# Nome explícito para consumidores que preferem a entidade no verbo.
enroll_vocabulary_item = enroll_item
