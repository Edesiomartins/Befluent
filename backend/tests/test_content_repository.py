"""Repositório de conteúdo — apenas unidades aprovadas."""

from sqlalchemy import select

from app.core.content_policy import ValidationStatus
from app.models import ContentSource, ContentUnit, Language
from app.services.content_repository import fetch_approved_unit, public_unit_or_none


def _seed(db, *, unit_status=ValidationStatus.APPROVED, source_status=ValidationStatus.APPROVED):
    lang = db.scalar(select(Language).where(Language.code == "en"))
    source = ContentSource(
        title="Fonte teste",
        language_id=lang.id,
        review_status=source_status,
        usage_policy="OPEN_LICENSE",
    )
    db.add(source)
    db.flush()
    # mode "guided" não faz parte do seed starter — evita falso positivo.
    unit = ContentUnit(
        source_id=source.id,
        language_id=lang.id,
        cefr_level="A2",
        skill="vocabulary_grammar",
        mode="guided",
        title="Unidade guiada de teste",
        payload_json={"text": "Hello world", "internal_notes": "privado"},
        validation_status=unit_status,
        is_active=True,
    )
    db.add(unit)
    db.flush()
    return unit


def test_fetch_approved_unit(db_session):
    unit = _seed(db_session)
    db_session.commit()
    found = fetch_approved_unit(
        db_session,
        language_id=unit.language_id,
        level="A2",
        skill="vocabulary_grammar",
        mode="guided",
    )
    assert found is not None
    assert found.id == unit.id
    public = public_unit_or_none(found)
    assert public is not None
    assert "internal_notes" not in public["payload"]


def test_pending_blocked(db_session):
    unit = _seed(db_session, unit_status=ValidationStatus.PENDING_REVIEW)
    db_session.commit()
    found = fetch_approved_unit(
        db_session,
        language_id=unit.language_id,
        level="A2",
        skill="vocabulary_grammar",
        mode="guided",
    )
    assert found is None


def test_rejected_source_blocked(db_session):
    unit = _seed(db_session, source_status=ValidationStatus.REJECTED)
    db_session.commit()
    found = fetch_approved_unit(
        db_session,
        language_id=unit.language_id,
        level="A2",
        skill="vocabulary_grammar",
        mode="guided",
    )
    assert found is None
