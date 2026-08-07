"""Cobertura do banco mock: nenhuma célula idioma × habilidade × faixa vazia.

Com `AI_MOCK_MODE=true` (padrão do projeto), uma célula vazia aqui é um bloco do
cronograma que abre sem nada dentro. O teste existe para que isso quebre no CI,
não na frente do aluno.
"""

import pytest

from app.core.levels import LEVEL_DETAILS, LEVEL_ORDER
from app.services import lesson_bank
from app.services.ai import _MOCK_BUILDERS, MockAIProvider
from app.services.learner_context import LearnerContext

LANGUAGES = lesson_bank.SUPPORTED_LANGUAGES
#: Campos que, vazios, deixariam a tela do aluno sem conteúdo.
CONTENT_FIELDS = (
    "items",
    "examples",
    "exercises",
    "text",
    "transcript",
    "prompt",
    "situation",
    "focus_sounds",
    "target_phrases",
    "steps",
    "patterns",
)


def context_for(language_code: str, level: str) -> LearnerContext:
    return LearnerContext(
        language_code=language_code,
        language_name_pt="Idioma",
        language_native_name="Idioma",
        level=level,
        level_name_pt=LEVEL_DETAILS[level]["name_pt"],
        level_description=LEVEL_DETAILS[level]["short_description"],
        level_source="placement_test",
        level_is_estimated=True,
        skill_levels={},
    )


def test_relatorio_de_cobertura_sem_lacunas():
    assert lesson_bank.coverage_report() == []


@pytest.mark.parametrize("language_code", LANGUAGES)
@pytest.mark.parametrize("band", lesson_bank.ALL_BANDS)
def test_leitura_e_escuta_tem_conteudo_no_idioma(language_code, band):
    reading = lesson_bank.reading_text(language_code, band)
    listening = lesson_bank.listening_script(language_code, band)
    assert reading["text"] and reading["title"]
    assert listening["transcript"] and listening["speaking_rate"]


@pytest.mark.parametrize("language_code", LANGUAGES)
@pytest.mark.parametrize("band", lesson_bank.ALL_BANDS)
def test_gramatica_tem_exemplos_e_exercicio(language_code, band):
    examples = lesson_bank.grammar_examples(language_code, band)
    exercises = lesson_bank.grammar_exercises(language_code, band)
    assert len(examples) >= 3
    assert exercises
    for exercise in exercises:
        # A resposta precisa estar entre as opções, senão o exercício é insolúvel.
        assert exercise["answer"] in exercise["options"]
        assert exercise["rationale"]


@pytest.mark.parametrize("language_code", LANGUAGES)
@pytest.mark.parametrize("level", LEVEL_ORDER)
@pytest.mark.parametrize("mode", sorted(_MOCK_BUILDERS))
def test_modo_mock_nunca_devolve_campo_vazio(language_code, level, mode):
    payload = MockAIProvider().generate_lesson(mode, context_for(language_code, level))
    assert payload["title"]
    for field in CONTENT_FIELDS:
        if field in payload:
            assert payload[field], f"{language_code}/{level}/{mode}: '{field}' vazio"


class TestParticularidadesDeEscrita:
    def test_japones_exige_kana_na_rubrica(self):
        task = lesson_bank.writing_task("ja", lesson_bank.BAND_BEGINNER)
        hints = " ".join(task["rubric_hints"])
        assert "kana" in hints
        assert "Romaji" in hints

    def test_mandarim_exige_hanzi_e_pinyin_com_tom(self):
        task = lesson_bank.writing_task("zh-CN", lesson_bank.BAND_BEGINNER)
        hints = " ".join(task["rubric_hints"])
        assert "hanzi" in hints
        assert "tom" in hints

    def test_ingles_nao_ganha_exigencia_de_escrita_extra(self):
        base = lesson_bank.WRITING_TASKS[lesson_bank.BAND_BEGINNER]["rubric_hints"]
        task = lesson_bank.writing_task("en", lesson_bank.BAND_BEGINNER)
        assert task["rubric_hints"] == list(base)

    def test_acessor_nao_muta_a_tabela_original(self):
        antes = list(lesson_bank.WRITING_TASKS[lesson_bank.BAND_BEGINNER]["rubric_hints"])
        lesson_bank.writing_task("ja", lesson_bank.BAND_BEGINNER)
        lesson_bank.writing_task("zh-CN", lesson_bank.BAND_BEGINNER)
        assert lesson_bank.WRITING_TASKS[lesson_bank.BAND_BEGINNER]["rubric_hints"] == antes


class TestPromptDeIdioma:
    def test_japones_pede_kana_e_furigana_no_prompt(self):
        block = context_for("ja", "A1").to_prompt_context()
        assert "furigana" in block
        assert "romaji" in block.lower()

    def test_mandarim_pede_pinyin_com_tom_no_prompt(self):
        block = context_for("zh-CN", "A1").to_prompt_context()
        assert "pinyin" in block.lower()
        assert "tom" in block.lower()

    def test_espanhol_fixa_a_variante_peninsular(self):
        block = context_for("es-ES", "A2").to_prompt_context()
        assert "vosotros" in block

    def test_topico_do_cronograma_entra_no_prompt(self):
        from app.services.learner_context import for_curriculum_block

        context = for_curriculum_block(
            context_for("en", "A2"),
            assessed_skill="reading",
            cefr_level="B1",
            topic="Viagem e hospedagem — leitura guiada",
            week_theme="Viagem e hospedagem",
        )
        block = context.to_prompt_context("reading")
        assert "Viagem e hospedagem — leitura guiada" in block
        assert "Tema da semana no cronograma: Viagem e hospedagem" in block
        # O nível do bloco vence o nível do perfil.
        assert "Nível CEFR do aluno: B1" in block
