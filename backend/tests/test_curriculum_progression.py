"""Checkpoint quinzenal, promoção de nível e origem do nível avaliado."""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.curriculum import BlockStatus
from app.core.errors import APIError
from app.core.levels import CEFRLevel, LevelSource
from app.core.levels import TestStatus as PlacementStatus
from app.models import (
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    PlacementTest,
    User,
    UserLanguage,
)
from app.services.curriculum_generator import generate_curriculum
from app.services.progression import (
    CHECKPOINT_SOURCE,
    PROMOTION_SCORE,
    apply_checkpoint_outcome,
    evaluate_promotion,
    start_checkpoint,
)

START = date(2026, 8, 3)


def setup_profile(db, language_code="en", entry=CEFRLevel.A2):
    user = db.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db.scalar(select(Language).where(Language.code == language_code))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        diagnostic_completed=True,
        current_level=entry,
        level_source=LevelSource.PLACEMENT_TEST,
        vocabulary_grammar_level=entry,
        reading_level=entry,
        listening_level=entry,
        writing_level=entry,
        speaking_level=entry,
    )
    db.add(profile)
    db.commit()
    return profile, user


def week_of(db, curriculum, number):
    return db.scalar(
        select(CurriculumWeek).where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumWeek.week_number == number,
        )
    )


def record_checkpoint(db, curriculum, user, *, week_number, band, accuracy, minutes_ago=0):
    """Checkpoint concluído com o acerto informado."""
    test = PlacementTest(
        user_id=user.id,
        language_code="en",
        status=PlacementStatus.COMPLETED,
        source=CHECKPOINT_SOURCE,
        completed_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        overall_level=band,
        total_score=accuracy * 20,
        result_json={
            "curriculum_id": curriculum.id,
            "week_number": week_number,
            "cefr_focus": band,
            "total_score": accuracy * 20,
            "max_score": 20,
        },
    )
    db.add(test)
    db.commit()
    return test


class TestAberturaDoCheckpoint:
    def test_semana_impar_nao_tem_checkpoint(self, db_session):
        profile, user = setup_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        with pytest.raises(APIError) as exc:
            start_checkpoint(
                db_session, user=user, curriculum=curriculum, week=week_of(db_session, curriculum, 1)
            )
        assert exc.value.code == "not_a_checkpoint_week"

    def test_abre_na_faixa_da_semana(self, db_session):
        profile, user = setup_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        week = week_of(db_session, curriculum, 2)

        test = start_checkpoint(db_session, user=user, curriculum=curriculum, week=week)
        db_session.commit()

        assert test.source == CHECKPOINT_SOURCE
        assert test.current_level_band == week.cefr_focus
        assert test.result_json["curriculum_id"] == curriculum.id
        assert test.result_json["week_number"] == 2

    def test_reabrir_retoma_o_mesmo_teste(self, db_session):
        profile, user = setup_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        week = week_of(db_session, curriculum, 2)

        first = start_checkpoint(db_session, user=user, curriculum=curriculum, week=week)
        db_session.commit()
        second = start_checkpoint(db_session, user=user, curriculum=curriculum, week=week)
        db_session.commit()
        assert first.id == second.id

    def test_checkpoint_nao_bloqueia_o_teste_completo(self, client, auth, db_session):
        """A guarda de 30 dias vale entre nivelamentos, não contra checkpoints."""
        profile, user = setup_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        record_checkpoint(
            db_session, curriculum, user, week_number=2, band=CEFRLevel.A2, accuracy=0.9
        )

        response = client.post(
            "/api/v1/placement-tests",
            json={"language_code": "en", "declared_beginner": False},
            headers=auth,
        )
        assert response.status_code == 200
        assert response.json()["status"] == PlacementStatus.IN_PROGRESS

    def test_checkpoint_nao_aparece_como_teste_atual(self, client, auth, db_session):
        profile, user = setup_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        start_checkpoint(
            db_session, user=user, curriculum=curriculum, week=week_of(db_session, curriculum, 2)
        )
        db_session.commit()

        body = client.get("/api/v1/placement-tests/current?language_code=en", headers=auth).json()
        assert body["test"] is None

    def test_rota_abre_o_checkpoint(self, client, auth, db_session):
        profile, _ = setup_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()

        response = client.post(
            f"/api/v1/curriculum/{curriculum.id}/checkpoint/2/start", headers=auth
        )
        assert response.status_code == 200
        body = response.json()
        assert body["placement_test_id"]
        assert body["week_number"] == 2
        assert body["notice"]

    def test_rota_recusa_semana_sem_checkpoint(self, client, auth, db_session):
        profile, _ = setup_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        response = client.post(
            f"/api/v1/curriculum/{curriculum.id}/checkpoint/1/start", headers=auth
        )
        assert response.status_code == 409

    def test_checkpoint_de_cronograma_alheio_responde_404(
        self, client, auth, db_session, other_user
    ):
        outro = db_session.get(User, other_user)
        language = db_session.scalar(select(Language).where(Language.code == "en"))
        profile = UserLanguage(
            user_id=outro.id,
            language_id=language.id,
            diagnostic_completed=True,
            vocabulary_grammar_level=CEFRLevel.A2,
            reading_level=CEFRLevel.A2,
            listening_level=CEFRLevel.A2,
            writing_level=CEFRLevel.A2,
            speaking_level=CEFRLevel.A2,
        )
        db_session.add(profile)
        db_session.commit()
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()

        response = client.post(
            f"/api/v1/curriculum/{curriculum.id}/checkpoint/2/start", headers=auth
        )
        assert response.status_code == 404


class TestPromocao:
    def _curriculum(self, db):
        profile, user = setup_profile(db)
        curriculum = generate_curriculum(db, profile.id, 180, start_date=START)
        db.commit()
        return curriculum, user, profile

    def test_um_checkpoint_nao_promove(self, db_session):
        curriculum, user, _ = self._curriculum(db_session)
        record_checkpoint(
            db_session, curriculum, user, week_number=2, band=CEFRLevel.A2, accuracy=0.95
        )
        result = evaluate_promotion(db_session, curriculum)
        assert result["promoted"] is False
        assert result["reason"] == "insufficient_checkpoints"

    def test_dois_checkpoints_consistentes_promovem(self, db_session):
        curriculum, user, _ = self._curriculum(db_session)
        band = week_of(db_session, curriculum, 2).cefr_focus
        record_checkpoint(
            db_session, curriculum, user, week_number=2, band=band, accuracy=0.85, minutes_ago=10
        )
        record_checkpoint(
            db_session, curriculum, user, week_number=4, band=band, accuracy=0.9, minutes_ago=1
        )

        result = evaluate_promotion(db_session, curriculum)
        assert result["promoted"] is True
        assert result["from_level"] == band
        assert result["weeks_updated"] > 0
        assert result["blocks_updated"] > 0

    def test_desempenho_abaixo_do_limiar_nao_promove(self, db_session):
        curriculum, user, _ = self._curriculum(db_session)
        band = week_of(db_session, curriculum, 2).cefr_focus
        record_checkpoint(
            db_session, curriculum, user, week_number=2, band=band, accuracy=0.9, minutes_ago=10
        )
        record_checkpoint(
            db_session,
            curriculum,
            user,
            week_number=4,
            band=band,
            accuracy=PROMOTION_SCORE - 0.05,
            minutes_ago=1,
        )
        result = evaluate_promotion(db_session, curriculum)
        assert result["promoted"] is False
        assert result["reason"] == "below_threshold"

    def test_checkpoints_de_faixas_diferentes_nao_promovem(self, db_session):
        curriculum, user, _ = self._curriculum(db_session)
        record_checkpoint(
            db_session,
            curriculum,
            user,
            week_number=2,
            band=CEFRLevel.A2,
            accuracy=0.9,
            minutes_ago=10,
        )
        record_checkpoint(
            db_session,
            curriculum,
            user,
            week_number=4,
            band=CEFRLevel.B1,
            accuracy=0.9,
            minutes_ago=1,
        )
        result = evaluate_promotion(db_session, curriculum)
        assert result["promoted"] is False
        assert result["reason"] == "different_bands"

    def test_promocao_nao_reescreve_bloco_concluido(self, db_session):
        curriculum, user, _ = self._curriculum(db_session)
        band = week_of(db_session, curriculum, 2).cefr_focus

        # Bloco concluído numa semana futura da mesma faixa.
        futuro = db_session.scalar(
            select(CurriculumWeek)
            .where(
                CurriculumWeek.curriculum_id == curriculum.id,
                CurriculumWeek.week_number > 4,
                CurriculumWeek.cefr_focus == band,
            )
            .order_by(CurriculumWeek.week_number)
        )
        assert futuro is not None
        block = db_session.scalar(
            select(CurriculumBlock)
            .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
            .where(CurriculumDay.week_id == futuro.id)
        )
        block.status = BlockStatus.COMPLETED
        nivel_original = block.cefr_level
        db_session.commit()

        record_checkpoint(
            db_session, curriculum, user, week_number=2, band=band, accuracy=0.9, minutes_ago=10
        )
        record_checkpoint(
            db_session, curriculum, user, week_number=4, band=band, accuracy=0.9, minutes_ago=1
        )
        evaluate_promotion(db_session, curriculum)
        db_session.commit()

        db_session.refresh(block)
        assert block.cefr_level == nivel_original

    def test_promocao_nao_mexe_em_semanas_ja_passadas(self, db_session):
        curriculum, user, _ = self._curriculum(db_session)
        band = week_of(db_session, curriculum, 2).cefr_focus
        semana_2_antes = week_of(db_session, curriculum, 2).cefr_focus

        record_checkpoint(
            db_session, curriculum, user, week_number=2, band=band, accuracy=0.9, minutes_ago=10
        )
        record_checkpoint(
            db_session, curriculum, user, week_number=4, band=band, accuracy=0.9, minutes_ago=1
        )
        evaluate_promotion(db_session, curriculum)
        db_session.commit()

        assert week_of(db_session, curriculum, 2).cefr_focus == semana_2_antes


class TestOrigemDoNivel:
    def test_checkpoint_grava_origem_propria(self, db_session):
        profile, user = setup_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        test = record_checkpoint(
            db_session, curriculum, user, week_number=2, band=CEFRLevel.A2, accuracy=0.9
        )

        apply_checkpoint_outcome(db_session, test)
        db_session.commit()
        db_session.refresh(profile)

        # Um nível vindo de 14 itens não pode se apresentar como o teste completo.
        assert profile.level_source == LevelSource.CHECKPOINT
