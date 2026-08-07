"""Gerador do cronograma: níveis de entrada, meta, pesos e particularidades."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.curriculum import ALLOWED_DURATIONS, BlockSkill
from app.core.errors import APIError
from app.core.levels import CEFRLevel, LevelSource
from app.models import (
    Curriculum,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    User,
    UserLanguage,
)
from app.services import curriculum_bank
from app.services.curriculum_generator import (
    generate_curriculum,
    median_level,
    target_level_for,
    week_levels,
    weight_for,
)

LANGUAGES = ["en", "es-ES", "fr", "ja", "zh-CN"]

#: Segunda-feira, para o cronograma começar sempre no mesmo dia da semana.
START = date(2026, 8, 3)


def make_profile(db, language_code="en", levels=None, user_email="admin@befluent.local"):
    """Perfil linguístico com níveis por competência já gravados."""
    user = db.scalar(select(User).where(User.email == user_email))
    language = db.scalar(select(Language).where(Language.code == language_code))
    levels = levels or {
        "vocabulary_grammar_level": CEFRLevel.A2,
        "reading_level": CEFRLevel.A2,
        "listening_level": CEFRLevel.A1,
        "writing_level": CEFRLevel.A2,
        "speaking_level": CEFRLevel.A2,
    }
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        diagnostic_completed=True,
        current_level=CEFRLevel.A2,
        level_source=LevelSource.PLACEMENT_TEST,
        **levels,
    )
    db.add(profile)
    db.commit()
    return profile


def days_of(db, curriculum):
    return list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
        )
    )


def blocks_of(db, day):
    return list(
        db.scalars(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
    )


class TestNiveis:
    def test_mediana_usa_a_menor_das_centrais(self):
        # Quatro competências: A1, A2, B1, B2 -> mediana conservadora = A2.
        assert (
            median_level(
                {
                    "a": CEFRLevel.A1,
                    "b": CEFRLevel.A2,
                    "c": CEFRLevel.B1,
                    "d": CEFRLevel.B2,
                }
            )
            == CEFRLevel.A2
        )

    def test_mediana_com_numero_impar(self):
        assert (
            median_level({"a": CEFRLevel.A1, "b": CEFRLevel.B1, "c": CEFRLevel.B2})
            == CEFRLevel.B1
        )

    def test_meta_do_plano_longo_e_b2(self):
        assert target_level_for(CEFRLevel.PRE_A1, 180) == CEFRLevel.B2
        assert target_level_for(CEFRLevel.B1, 180) == CEFRLevel.B2

    def test_meta_do_plano_curto_sobe_dois_subniveis(self):
        assert target_level_for(CEFRLevel.PRE_A1, 90) == CEFRLevel.A2
        assert target_level_for(CEFRLevel.A1, 90) == CEFRLevel.B1

    def test_meta_do_plano_curto_tem_teto_b2(self):
        assert target_level_for(CEFRLevel.B1, 90) == CEFRLevel.B2
        assert target_level_for(CEFRLevel.B2, 90) == CEFRLevel.B2

    def test_semanas_distribuidas_entre_entrada_e_meta(self):
        levels = week_levels(CEFRLevel.A2, CEFRLevel.B2, 13)
        assert levels[0] == CEFRLevel.A2
        assert levels[-1] == CEFRLevel.B2
        assert set(levels) == {CEFRLevel.A2, CEFRLevel.B1, CEFRLevel.B2}

    def test_semanas_nunca_retrocedem(self):
        from app.core.levels import LEVEL_INDEX

        indexes = [LEVEL_INDEX[level] for level in week_levels(CEFRLevel.A1, CEFRLevel.B2, 26)]
        assert indexes == sorted(indexes)

    def test_entrada_igual_a_meta_concentra_em_um_nivel(self):
        assert set(week_levels(CEFRLevel.B2, CEFRLevel.B2, 13)) == {CEFRLevel.B2}


class TestGeracao:
    def test_exige_nivelamento_concluido(self, db_session):
        profile = make_profile(
            db_session,
            levels={
                "vocabulary_grammar_level": None,
                "reading_level": None,
                "listening_level": None,
                "writing_level": None,
                "speaking_level": None,
            },
        )
        with pytest.raises(APIError) as exc:
            generate_curriculum(db_session, profile.id, 90)
        assert exc.value.code == "placement_required"

    def test_recusa_duracao_invalida(self, db_session):
        profile = make_profile(db_session)
        with pytest.raises(APIError) as exc:
            generate_curriculum(db_session, profile.id, 120)
        assert exc.value.code == "invalid_duration"

    @pytest.mark.parametrize("duration", ALLOWED_DURATIONS)
    def test_gera_um_dia_por_dia_de_plano(self, db_session, duration):
        profile = make_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, duration, start_date=START)
        db_session.commit()

        days = days_of(db_session, curriculum)
        assert len(days) == duration
        assert [day.day_number for day in days] == list(range(1, duration + 1))
        assert days[0].scheduled_date == START
        assert days[-1].scheduled_date == START + timedelta(days=duration - 1)

    @pytest.mark.parametrize("duration", ALLOWED_DURATIONS)
    def test_todo_dia_tem_bloco_de_revisao(self, db_session, duration):
        profile = make_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, duration, start_date=START)
        db_session.commit()
        for day in days_of(db_session, curriculum):
            skills = [block.skill for block in blocks_of(db_session, day)]
            assert BlockSkill.REVIEW in skills, f"dia {day.day_number} sem revisão"

    def test_dia_cheio_cobre_entrada_e_saida(self, db_session):
        profile = make_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        # Dia 1 = segunda-feira, dia cheio.
        day = days_of(db_session, curriculum)[0]
        skills = {block.skill for block in blocks_of(db_session, day)}
        assert BlockSkill.VOCABULARY in skills
        assert BlockSkill.GRAMMAR in skills
        assert skills & {BlockSkill.LISTENING, BlockSkill.READING}
        assert skills & {BlockSkill.CONVERSATION, BlockSkill.WRITING}

    def test_dia_cheio_cabe_na_faixa_de_minutos(self, db_session):
        profile = make_profile(
            db_session,
            levels={
                "vocabulary_grammar_level": CEFRLevel.A2,
                "reading_level": CEFRLevel.A2,
                "listening_level": CEFRLevel.A2,
                "writing_level": CEFRLevel.A2,
                "speaking_level": CEFRLevel.A2,
            },
        )
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        day = days_of(db_session, curriculum)[0]
        total = sum(block.estimated_minutes for block in blocks_of(db_session, day))
        assert 45 <= total <= 60

    def test_domingo_e_dia_leve(self, db_session):
        profile = make_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        sundays = [
            day for day in days_of(db_session, curriculum) if day.scheduled_date.weekday() == 6
        ]
        assert sundays
        for day in sundays:
            skills = [block.skill for block in blocks_of(db_session, day)]
            assert set(skills) == {BlockSkill.REVIEW, BlockSkill.READING}

    def test_semanas_pares_sao_checkpoint(self, db_session):
        profile = make_profile(db_session)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        weeks = list(
            db_session.scalars(
                select(CurriculumWeek)
                .where(CurriculumWeek.curriculum_id == curriculum.id)
                .order_by(CurriculumWeek.week_number)
            )
        )
        assert weeks
        for week in weeks:
            assert week.is_checkpoint is (week.week_number % 2 == 0)
            assert week.theme, "semana sem tema comunicativo"

    def test_regenerar_arquiva_o_anterior(self, db_session):
        profile = make_profile(db_session)
        first = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        second = generate_curriculum(db_session, profile.id, 180, start_date=START)
        db_session.commit()

        db_session.refresh(first)
        assert first.status == "regenerated"
        assert second.status == "active"
        # O anterior continua existindo: histórico não é apagado.
        assert db_session.get(Curriculum, first.id) is not None


class TestPesosAdaptativos:
    def test_competencia_abaixo_da_mediana_recebe_mais_tempo(self):
        levels = {
            "vocabulary_grammar": CEFRLevel.B1,
            "reading": CEFRLevel.B1,
            "listening": CEFRLevel.A1,
            "writing": CEFRLevel.B1,
            "speaking": CEFRLevel.B1,
        }
        assert weight_for(BlockSkill.LISTENING, levels, CEFRLevel.B1) > 1.0
        assert weight_for(BlockSkill.READING, levels, CEFRLevel.B1) == 1.0

    def test_competencia_acima_da_mediana_entra_em_manutencao(self):
        levels = {
            "vocabulary_grammar": CEFRLevel.A2,
            "reading": CEFRLevel.B2,
            "listening": CEFRLevel.A2,
            "writing": CEFRLevel.A2,
            "speaking": CEFRLevel.A2,
        }
        assert weight_for(BlockSkill.READING, levels, CEFRLevel.A2) < 1.0

    def test_lacuna_vira_minutos_no_cronograma(self, db_session):
        profile = make_profile(
            db_session,
            levels={
                "vocabulary_grammar_level": CEFRLevel.B1,
                "reading_level": CEFRLevel.B1,
                "listening_level": CEFRLevel.A1,
                "writing_level": CEFRLevel.B1,
                "speaking_level": CEFRLevel.B1,
            },
        )
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()

        listening = [
            block
            for day in days_of(db_session, curriculum)
            for block in blocks_of(db_session, day)
            if block.skill == BlockSkill.LISTENING
        ]
        reading = [
            block
            for day in days_of(db_session, curriculum)
            for block in blocks_of(db_session, day)
            if block.skill == BlockSkill.READING
        ]
        assert listening and reading
        assert listening[0].estimated_minutes > reading[0].estimated_minutes

    def test_lacuna_vira_mais_blocos_no_cronograma(self, db_session):
        profile = make_profile(
            db_session,
            levels={
                "vocabulary_grammar_level": CEFRLevel.B1,
                "reading_level": CEFRLevel.B1,
                "listening_level": CEFRLevel.A1,
                "writing_level": CEFRLevel.B1,
                "speaking_level": CEFRLevel.B1,
            },
        )
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()

        counts = {BlockSkill.LISTENING: 0, BlockSkill.READING: 0}
        for day in days_of(db_session, curriculum):
            for block in blocks_of(db_session, day):
                if block.skill in counts:
                    counts[block.skill] += 1
        assert counts[BlockSkill.LISTENING] > counts[BlockSkill.READING]


class TestIdiomas:
    @pytest.mark.parametrize("language_code", LANGUAGES)
    def test_gera_para_os_cinco_idiomas(self, db_session, language_code):
        profile = make_profile(db_session, language_code=language_code)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()

        days = days_of(db_session, curriculum)
        assert len(days) == 90
        for day in days:
            blocks = blocks_of(db_session, day)
            assert blocks, f"{language_code}: dia {day.day_number} sem blocos"
            for block in blocks:
                assert block.topic, f"{language_code}: bloco sem tópico"
                assert block.cefr_level

    @pytest.mark.parametrize("language_code", ["ja", "zh-CN"])
    def test_pronuncia_diaria_em_japones_e_mandarim(self, db_session, language_code):
        profile = make_profile(db_session, language_code=language_code)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        uteis = [
            day
            for day in days_of(db_session, curriculum)
            if day.scheduled_date.weekday() != 6
        ]
        for day in uteis:
            skills = [block.skill for block in blocks_of(db_session, day)]
            assert BlockSkill.PRONUNCIATION in skills

    @pytest.mark.parametrize("language_code", ["en", "es-ES", "fr"])
    def test_pronuncia_tres_vezes_por_semana_nos_demais(self, db_session, language_code):
        profile = make_profile(db_session, language_code=language_code)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        primeira_semana = [
            day for day in days_of(db_session, curriculum) if day.day_number <= 7
        ]
        com_pronuncia = [
            day
            for day in primeira_semana
            if BlockSkill.PRONUNCIATION in [b.skill for b in blocks_of(db_session, day)]
        ]
        assert len(com_pronuncia) == 3

    def test_japones_comeca_por_kana(self, db_session):
        profile = make_profile(db_session, language_code="ja")
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        escrita = [
            block
            for day in days_of(db_session, curriculum)
            if day.day_number <= 14
            for block in blocks_of(db_session, day)
            if block.skill == BlockSkill.WRITING
        ]
        assert escrita
        assert all("kana" in block.topic for block in escrita)

    def test_japones_progride_para_kanji(self, db_session):
        profile = make_profile(db_session, language_code="ja")
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        escrita = [
            block
            for day in days_of(db_session, curriculum)
            if day.day_number > 21
            for block in blocks_of(db_session, day)
            if block.skill == BlockSkill.WRITING
        ]
        assert escrita
        assert all("kanji" in block.topic for block in escrita)

    def test_mandarim_trabalha_tons_desde_o_dia_1(self, db_session):
        profile = make_profile(db_session, language_code="zh-CN")
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        day = days_of(db_session, curriculum)[0]
        pronuncia = [
            block for block in blocks_of(db_session, day) if block.skill == BlockSkill.PRONUNCIATION
        ]
        assert pronuncia
        assert "tons" in pronuncia[0].topic

    def test_mandarim_escreve_hanzi_progressivo(self, db_session):
        profile = make_profile(db_session, language_code="zh-CN")
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        escrita = [
            block
            for day in days_of(db_session, curriculum)
            for block in blocks_of(db_session, day)
            if block.skill == BlockSkill.WRITING
        ]
        assert escrita
        assert all("hanzi" in block.topic for block in escrita)

    @pytest.mark.parametrize("language_code", ["fr", "es-ES"])
    def test_transparencia_lexical_ganha_escuta_extra(self, db_session, language_code):
        profile = make_profile(db_session, language_code=language_code)
        curriculum = generate_curriculum(db_session, profile.id, 90, start_date=START)
        db_session.commit()
        listening = [
            block
            for day in days_of(db_session, curriculum)
            for block in blocks_of(db_session, day)
            if block.skill == BlockSkill.LISTENING
        ]
        reading = [
            block
            for day in days_of(db_session, curriculum)
            for block in blocks_of(db_session, day)
            if block.skill == BlockSkill.READING and day.scheduled_date.weekday() != 6
        ]
        assert listening and reading
        assert listening[0].estimated_minutes > reading[0].estimated_minutes


class TestBancoDeTemas:
    def test_todos_os_idiomas_tem_tema_em_todo_nivel(self):
        assert curriculum_bank.coverage_report() == {}

    @pytest.mark.parametrize("language_code", LANGUAGES)
    def test_temas_nao_se_repetem_dentro_do_nivel(self, language_code):
        for level in (CEFRLevel.PRE_A1, CEFRLevel.A1, CEFRLevel.A2, CEFRLevel.B1, CEFRLevel.B2):
            themes = curriculum_bank.themes_for(language_code, level)
            assert len(themes) == len(set(themes)), f"{language_code}/{level} com tema duplicado"

    def test_japones_abre_por_hiragana(self):
        themes = curriculum_bank.themes_for("ja", CEFRLevel.PRE_A1)
        assert "Hiragana" in themes[0]

    def test_mandarim_abre_por_pinyin_e_tons(self):
        themes = curriculum_bank.themes_for("zh-CN", CEFRLevel.PRE_A1)
        assert "tons" in themes[0].lower()
