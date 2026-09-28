"""Latim clássico sai do catálogo; eclesiástico e italiano permanecem."""

from sqlalchemy import select

from app.models import Language, User, UserLanguage
from app.services.seed import seed_languages


def test_seed_retires_classical_latin_without_touching_other_languages(db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    classical = Language(
        code="la-classical",
        name_pt="Latim Clássico",
        native_name="Lingua Latina",
        description="Pronúncia reconstruída",
        strategy_summary="Fora do catálogo.",
        is_active=True,
    )
    db_session.add(classical)
    db_session.flush()
    profile = UserLanguage(
        user_id=user.id,
        language_id=classical.id,
        is_active=True,
        onboarding_completed=True,
    )
    db_session.add(profile)
    db_session.commit()

    la_before = db_session.scalar(select(Language).where(Language.code == "la"))
    it_before = db_session.scalar(select(Language).where(Language.code == "it"))
    assert la_before is not None and la_before.is_active is True
    assert it_before is not None and it_before.is_active is True
    la_name = la_before.name_pt
    it_name = it_before.name_pt

    seed_languages(db_session)

    db_session.refresh(classical)
    db_session.refresh(profile)
    la_after = db_session.scalar(select(Language).where(Language.code == "la"))
    it_after = db_session.scalar(select(Language).where(Language.code == "it"))

    assert classical.is_active is False
    assert profile.is_active is False
    assert la_after.is_active is True
    assert la_after.name_pt == la_name
    assert it_after.is_active is True
    assert it_after.name_pt == it_name
    assert db_session.get(UserLanguage, profile.id) is not None
