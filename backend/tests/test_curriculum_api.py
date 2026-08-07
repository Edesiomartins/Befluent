"""Rotas do cronograma: autenticação, propriedade, execução e recuperação."""

from datetime import date, timedelta

from sqlalchemy import select

from app.core.curriculum import BlockSkill, BlockStatus, DayStatus
from app.core.levels import CEFRLevel, LevelSource
from app.models import (
    Curriculum,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    Lesson,
    ReviewItem,
    StudySession,
    User,
    UserLanguage,
)
from app.services.curriculum_generator import generate_curriculum
from app.services.progression import overdue_days

START = date(2026, 8, 3)


def setup_profile(db, language_code="en", user_email="admin@befluent.local", levels=None):
    user = db.scalar(select(User).where(User.email == user_email))
    language = db.scalar(select(Language).where(Language.code == language_code))
    skill_levels = {
        "vocabulary_grammar_level": CEFRLevel.A2,
        "reading_level": CEFRLevel.A2,
        "listening_level": CEFRLevel.A2,
        "writing_level": CEFRLevel.A2,
        "speaking_level": CEFRLevel.A2,
        **(levels or {}),
    }
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        diagnostic_completed=True,
        current_level=CEFRLevel.A2,
        level_source=LevelSource.PLACEMENT_TEST,
        **skill_levels,
    )
    db.add(profile)
    db.commit()
    return profile


def make_curriculum(db, profile, duration=90, start=START):
    curriculum = generate_curriculum(db, profile.id, duration, start_date=start)
    db.commit()
    return curriculum


def first_day(db, curriculum):
    return db.scalar(
        select(CurriculumDay)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(CurriculumWeek.curriculum_id == curriculum.id)
        .order_by(CurriculumDay.day_number)
    )


def blocks_of(db, day):
    return list(
        db.scalars(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
    )


class TestAutenticacao:
    def test_leitura_sem_sessao_e_bloqueada(self, client):
        assert client.get("/api/v1/curriculum/active?language_code=en").status_code == 401
        assert client.get("/api/v1/curriculum/day/today?language_code=en").status_code == 401
        assert client.get("/api/v1/curriculum/day/qualquer").status_code == 401

    def test_escrita_sem_csrf_e_bloqueada_antes_da_sessao(self, client):
        # A guarda de CSRF roda antes da autenticação: 403, não 401. É o
        # comportamento já existente nas demais rotas mutáveis.
        assert client.post(
            "/api/v1/curriculum", json={"language_code": "en", "duration_days": 90}
        ).status_code == 403
        assert client.post("/api/v1/curriculum/block/qualquer/start").status_code == 403
        assert client.post("/api/v1/curriculum/block/qualquer/complete").status_code == 403


class TestCriacao:
    def test_cria_cronograma_de_90_dias(self, client, auth, db_session):
        setup_profile(db_session)
        response = client.post(
            "/api/v1/curriculum",
            json={"language_code": "en", "duration_days": 90},
            headers=auth,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["duration_days"] == 90
        assert body["entry_level"] == "A2"
        # Plano curto sobe dois subníveis a partir da entrada, com teto B2.
        assert body["target_level"] == "B2"
        assert body["progress"]["days_total"] == 90
        assert body["progress"]["days_completed"] == 0
        assert body["disclaimer"]

    def test_cria_cronograma_de_180_dias_com_meta_b2(self, client, auth, db_session):
        setup_profile(db_session)
        body = client.post(
            "/api/v1/curriculum",
            json={"language_code": "en", "duration_days": 180},
            headers=auth,
        ).json()
        assert body["target_level"] == "B2"
        assert body["progress"]["days_total"] == 180

    def test_recusa_duracao_fora_das_permitidas(self, client, auth, db_session):
        setup_profile(db_session)
        response = client.post(
            "/api/v1/curriculum",
            json={"language_code": "en", "duration_days": 45},
            headers=auth,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_duration"

    def test_sem_nivelamento_pede_o_teste(self, client, auth, db_session):
        setup_profile(
            db_session,
            levels={
                "vocabulary_grammar_level": None,
                "reading_level": None,
                "listening_level": None,
                "writing_level": None,
                "speaking_level": None,
            },
        )
        response = client.post(
            "/api/v1/curriculum",
            json={"language_code": "en", "duration_days": 90},
            headers=auth,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "placement_required"

    def test_regenerar_arquiva_o_anterior(self, client, auth, db_session):
        setup_profile(db_session)
        first = client.post(
            "/api/v1/curriculum",
            json={"language_code": "en", "duration_days": 90},
            headers=auth,
        ).json()
        second = client.post(
            "/api/v1/curriculum",
            json={"language_code": "en", "duration_days": 180},
            headers=auth,
        ).json()
        assert first["id"] != second["id"]
        assert db_session.get(Curriculum, first["id"]).status == "regenerated"
        ativo = client.get("/api/v1/curriculum/active?language_code=en", headers=auth).json()
        assert ativo["id"] == second["id"]


class TestConsulta:
    def test_ativo_traz_semanas_com_tema(self, client, auth, db_session):
        profile = setup_profile(db_session)
        make_curriculum(db_session, profile)
        body = client.get("/api/v1/curriculum/active?language_code=en", headers=auth).json()
        assert body["weeks"]
        assert all(week["theme"] for week in body["weeks"])
        assert any(week["is_checkpoint"] for week in body["weeks"])
        assert body["progress"]["next_checkpoint_week"] == 2

    def test_sem_cronograma_responde_404(self, client, auth, db_session):
        setup_profile(db_session)
        response = client.get("/api/v1/curriculum/active?language_code=en", headers=auth)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "curriculum_not_found"

    def test_semana_traz_dias_e_blocos(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        body = client.get(f"/api/v1/curriculum/{curriculum.id}/week/1", headers=auth).json()
        assert body["week_number"] == 1
        assert len(body["days"]) == 7
        assert body["days"][0]["blocks"]
        assert body["days"][0]["total_minutes"] > 0

    def test_semana_inexistente_responde_404(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        response = client.get(f"/api/v1/curriculum/{curriculum.id}/week/999", headers=auth)
        assert response.status_code == 404

    def test_hoje_traz_o_primeiro_dia_em_aberto(self, client, auth, db_session):
        profile = setup_profile(db_session)
        make_curriculum(db_session, profile)
        body = client.get("/api/v1/curriculum/day/today?language_code=en", headers=auth).json()
        assert body["day"]["day_number"] == 1
        assert body["week"]["week_number"] == 1
        assert body["day"]["blocks"]

    def test_hoje_lista_dias_vencidos(self, client, auth, db_session):
        profile = setup_profile(db_session)
        make_curriculum(db_session, profile, start=date.today() - timedelta(days=10))
        body = client.get("/api/v1/curriculum/day/today?language_code=en", headers=auth).json()
        assert len(body["overdue_days"]) == 10
        assert body["curriculum"]["progress"]["needs_reschedule"] is True


class TestPropriedade:
    def test_cronograma_de_outro_usuario_responde_404(self, client, auth, db_session, other_user):
        outro = db_session.get(User, other_user)
        profile = setup_profile(db_session, user_email=outro.email)
        curriculum = make_curriculum(db_session, profile)

        response = client.get(f"/api/v1/curriculum/{curriculum.id}/week/1", headers=auth)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "curriculum_not_found"

    def test_bloco_de_outro_usuario_responde_404(self, client, auth, db_session, other_user):
        outro = db_session.get(User, other_user)
        profile = setup_profile(db_session, user_email=outro.email)
        curriculum = make_curriculum(db_session, profile)
        block = blocks_of(db_session, first_day(db_session, curriculum))[0]

        assert client.post(f"/api/v1/curriculum/block/{block.id}/start", headers=auth).status_code == 404
        assert client.post(f"/api/v1/curriculum/block/{block.id}/complete", headers=auth).status_code == 404

    def test_dia_de_outro_usuario_responde_404(self, client, auth, db_session, other_user):
        outro = db_session.get(User, other_user)
        profile = setup_profile(db_session, user_email=outro.email)
        curriculum = make_curriculum(db_session, profile)
        day = first_day(db_session, curriculum)
        assert client.get(f"/api/v1/curriculum/day/{day.id}", headers=auth).status_code == 404


class TestExecucaoDeBloco:
    def test_start_gera_licao_e_vincula(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        block = blocks_of(db_session, first_day(db_session, curriculum))[0]

        body = client.post(f"/api/v1/curriculum/block/{block.id}/start", headers=auth).json()
        assert body["lesson"]["title"]
        assert body["block"]["lesson_ref"]
        db_session.expire_all()
        assert db_session.get(CurriculumBlock, block.id).lesson_ref
        assert db_session.get(Lesson, body["lesson"]["lesson_id"]) is not None

    def test_start_e_idempotente(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        block = blocks_of(db_session, first_day(db_session, curriculum))[0]

        first = client.post(f"/api/v1/curriculum/block/{block.id}/start", headers=auth).json()
        second = client.post(f"/api/v1/curriculum/block/{block.id}/start", headers=auth).json()
        assert first["lesson"]["lesson_id"] == second["lesson"]["lesson_id"]
        total = db_session.scalar(
            select(Lesson).where(Lesson.user_language_id == profile.id)
        )
        assert total is not None
        assert len(list(db_session.scalars(select(Lesson)))) == 1

    def test_licao_do_bloco_usa_o_topico_do_cronograma(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        block = blocks_of(db_session, first_day(db_session, curriculum))[0]

        body = client.post(f"/api/v1/curriculum/block/{block.id}/start", headers=auth).json()
        assert body["lesson"]["topic"] == block.topic
        assert body["lesson"]["curriculum_block_id"] == block.id

    def test_bloco_de_revisao_consome_a_fila_do_srs(self, client, auth, db_session):
        profile = setup_profile(db_session)
        db_session.add(
            ReviewItem(
                user_language_id=profile.id,
                item_type="vocabulary",
                reference_id="ref-1",
                payload_json={"term": "water", "translation_pt": "água"},
            )
        )
        db_session.commit()
        curriculum = make_curriculum(db_session, profile)
        day = first_day(db_session, curriculum)
        review = next(b for b in blocks_of(db_session, day) if b.skill == BlockSkill.REVIEW)

        body = client.post(f"/api/v1/curriculum/block/{review.id}/start", headers=auth).json()
        assert body["lesson"]["source"] == "srs_queue"
        assert body["lesson"]["queue_empty"] is False
        assert body["lesson"]["items"][0]["payload"]["term"] == "water"

    def test_revisao_com_fila_vazia_declara_em_vez_de_inventar(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        day = first_day(db_session, curriculum)
        review = next(b for b in blocks_of(db_session, day) if b.skill == BlockSkill.REVIEW)

        body = client.post(f"/api/v1/curriculum/block/{review.id}/start", headers=auth).json()
        assert body["lesson"]["queue_empty"] is True
        assert body["lesson"]["items"] == []
        assert body["lesson"]["empty_notice"]

    def test_complete_marca_bloco_e_registra_score(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        block = blocks_of(db_session, first_day(db_session, curriculum))[0]

        body = client.post(
            f"/api/v1/curriculum/block/{block.id}/complete",
            json={"score": 0.9},
            headers=auth,
        ).json()
        assert body["block"]["status"] == BlockStatus.COMPLETED
        assert body["block"]["score"] == 0.9
        assert body["day_completed"] is False

    def test_dia_fecha_quando_todos_os_blocos_caem(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        day = first_day(db_session, curriculum)
        blocks = blocks_of(db_session, day)

        for block in blocks[:-1]:
            body = client.post(
                f"/api/v1/curriculum/block/{block.id}/complete", headers=auth
            ).json()
            assert body["day_completed"] is False

        body = client.post(
            f"/api/v1/curriculum/block/{blocks[-1].id}/complete", headers=auth
        ).json()
        assert body["day_completed"] is True
        assert body["day"]["status"] == DayStatus.COMPLETED
        assert body["day"]["completed_at"]
        assert body["progress"]["days_completed"] == 1

    def test_bloco_concluido_encerra_a_sessao_de_estudo(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        block = blocks_of(db_session, first_day(db_session, curriculum))[0]

        client.post(f"/api/v1/curriculum/block/{block.id}/start", headers=auth)
        client.post(f"/api/v1/curriculum/block/{block.id}/complete", headers=auth)

        db_session.expire_all()
        session = db_session.scalar(select(StudySession).where(StudySession.user_language_id == profile.id))
        assert session is not None
        assert session.status == "completed"
        assert session.ended_at is not None

    def test_score_fora_da_faixa_e_recusado(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        block = blocks_of(db_session, first_day(db_session, curriculum))[0]
        response = client.post(
            f"/api/v1/curriculum/block/{block.id}/complete",
            json={"score": 5},
            headers=auth,
        )
        assert response.status_code == 422


class TestReagendamento:
    def _atrasado(self, db, profile, dias=10):
        return make_curriculum(db, profile, start=date.today() - timedelta(days=dias))

    def test_dias_vencidos_sao_contados(self, db_session):
        profile = setup_profile(db_session)
        curriculum = self._atrasado(db_session, profile)
        days = list(
            db_session.scalars(
                select(CurriculumDay)
                .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
                .where(CurriculumWeek.curriculum_id == curriculum.id)
            )
        )
        assert len(overdue_days(days, reference=date.today())) == 10

    def test_estender_desloca_os_dias_pendentes(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = self._atrasado(db_session, profile)
        response = client.post(
            f"/api/v1/curriculum/{curriculum.id}/reschedule",
            json={"strategy": "extend"},
            headers=auth,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["offset_days"] == 10
        assert body["shifted_days"] == 90
        assert body["curriculum"]["progress"]["overdue_days"] == 0

    def test_comprimir_preserva_o_essencial_e_marca_o_atraso(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = self._atrasado(db_session, profile)
        response = client.post(
            f"/api/v1/curriculum/{curriculum.id}/reschedule",
            json={"strategy": "compress"},
            headers=auth,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["skipped_days"] == 10
        assert body["moved_blocks"] > 0

        db_session.expire_all()
        vencidos = list(
            db_session.scalars(
                select(CurriculumDay)
                .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
                .where(
                    CurriculumWeek.curriculum_id == curriculum.id,
                    CurriculumDay.scheduled_date < date.today(),
                )
            )
        )
        # O atraso fica visível: dia pulado, não apagado.
        assert all(day.status == DayStatus.SKIPPED for day in vencidos)

    def test_comprimir_nao_descarta_bloco_ja_concluido(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = self._atrasado(db_session, profile)
        day = first_day(db_session, curriculum)
        # Um bloco não essencial: seria descartado pela compressão se estivesse
        # pendente, mas concluído tem de sobreviver.
        block = next(
            b
            for b in blocks_of(db_session, day)
            if b.skill in {BlockSkill.CONVERSATION, BlockSkill.WRITING}
        )
        client.post(f"/api/v1/curriculum/block/{block.id}/complete", headers=auth)

        client.post(
            f"/api/v1/curriculum/{curriculum.id}/reschedule",
            json={"strategy": "compress"},
            headers=auth,
        )
        db_session.expire_all()
        preservado = db_session.get(CurriculumBlock, block.id)
        assert preservado is not None
        assert preservado.status == BlockStatus.COMPLETED

    def test_estrategia_invalida_e_recusada(self, client, auth, db_session):
        profile = setup_profile(db_session)
        curriculum = make_curriculum(db_session, profile)
        response = client.post(
            f"/api/v1/curriculum/{curriculum.id}/reschedule",
            json={"strategy": "apagar_tudo"},
            headers=auth,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_strategy"

    def test_reagendar_cronograma_alheio_responde_404(self, client, auth, db_session, other_user):
        outro = db_session.get(User, other_user)
        profile = setup_profile(db_session, user_email=outro.email)
        curriculum = make_curriculum(db_session, profile)
        response = client.post(
            f"/api/v1/curriculum/{curriculum.id}/reschedule",
            json={"strategy": "extend"},
            headers=auth,
        )
        assert response.status_code == 404
