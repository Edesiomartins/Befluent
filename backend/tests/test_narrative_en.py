"""Narrativa do inglês: elenco fixo e um episódio por tema.

O que os testes travam: a cena existe para os temas cobertos e é a mesma para o
mesmo tema (não sorteada a cada abertura); o elenco é recorrente; a cena só
aparece em `en`; tema sem episódio devolve ausência declarada, nunca uma cena
genérica inventada; e cada fala tem tradução.
"""

from sqlalchemy import select

from app.models import Language, User, UserLanguage
from app.services import narrative_en
from app.services.curriculum_generator import generate_curriculum


def _profile(db, *, code: str = "en") -> UserLanguage:
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == code))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        diagnostic_completed=True,
        current_level="A1",
        level_source="placement_test",
        vocabulary_grammar_level="A1",
        reading_level="A1",
        listening_level="A1",
        writing_level="A1",
        speaking_level="A1",
    )
    db.add(profile)
    db.flush()
    return profile


def test_tema_coberto_tem_episodio_estavel():
    first = narrative_en.episode_for("Apresentações e rotina", day_number=1)
    again = narrative_en.episode_for("Apresentações e rotina", day_number=1)

    assert first is not None
    assert first == again, "a cena do mesmo tema e dia não pode mudar entre aberturas"
    assert first["title"]
    assert first["lines"], "uma cena sem falas não é cena"


def test_toda_fala_tem_traducao_e_personagem_do_elenco():
    cast = {member["name"] for member in narrative_en.CAST}

    for theme in narrative_en.covered_themes():
        episode = narrative_en.episode_for(theme, day_number=1)
        assert episode is not None
        for line in episode["lines"]:
            assert line["speaker"] in cast, f"{line['speaker']} não está no elenco"
            assert line["text"].strip()
            assert line["translation_pt"].strip()


def test_tema_sem_episodio_devolve_none():
    assert narrative_en.episode_for("Tema que não existe no banco", day_number=1) is None


def test_dias_diferentes_do_mesmo_tema_avancam_a_cena():
    episodes = {
        narrative_en.episode_for("Apresentações e rotina", day_number=day)["title"]
        for day in (1, 2, 3)
    }

    assert len(episodes) > 1, "a semana inteira não pode repetir a mesma cena"


def test_dia_do_cronograma_em_ingles_traz_a_cena(client, auth, db_session):
    profile = _profile(db_session, code="en")
    generate_curriculum(db_session, profile.id, 90)
    db_session.commit()

    response = client.get("/api/v1/curriculum/day/today?language_code=en", headers=auth)

    assert response.status_code == 200
    day = response.json()["day"]
    assert day["story"] is not None
    assert day["story"]["lines"]


def test_dia_do_cronograma_em_frances_nao_traz_cena(client, auth, db_session):
    profile = _profile(db_session, code="fr")
    generate_curriculum(db_session, profile.id, 90)
    db_session.commit()

    response = client.get("/api/v1/curriculum/day/today?language_code=fr", headers=auth)

    assert response.status_code == 200
    assert response.json()["day"]["story"] is None
