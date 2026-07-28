"""Testes do motor de nivelamento (regras puras, sem banco)."""

from app.core.levels import Skill
from app.services import placement_engine as engine


def record(skill: str, level: str, score: float, ms: int | None = 5000):
    return engine.AnswerRecord(
        skill=skill, cefr_level=level, normalized_score=score, response_time_ms=ms
    )


def levels(mapping: dict[str, str]) -> dict[str, dict]:
    return {skill: {"estimated_level": level} for skill, level in mapping.items()}


class TestAdaptiveSelection:
    def test_promove_apos_tres_acertos(self):
        state = engine.TestState(current_band="A2")
        for _ in range(3):
            engine.register_answer(state, record(Skill.READING, "A2", 1.0))
        assert state.current_band == "B1"

    def test_rebaixa_apos_dois_erros(self):
        state = engine.TestState(current_band="B1")
        for _ in range(2):
            engine.register_answer(state, record(Skill.READING, "B1", 0.0))
        assert state.current_band == "A2"

    def test_nao_ultrapassa_faixa_testavel(self):
        state = engine.TestState(current_band="B2")
        for _ in range(9):
            engine.register_answer(state, record(Skill.READING, "B2", 1.0))
        assert state.current_band == "B2"

    def test_nao_desce_abaixo_de_pre_a1(self):
        state = engine.TestState(current_band="PRE_A1")
        for _ in range(6):
            engine.register_answer(state, record(Skill.READING, "PRE_A1", 0.0))
        assert state.current_band == "PRE_A1"

    def test_inicia_em_a2_ou_pre_a1_para_iniciante(self):
        assert engine.initial_band(False) == "A2"
        assert engine.initial_band(True) == "PRE_A1"

    def test_rotaciona_competencias(self):
        state = engine.TestState()
        first = engine.next_skill(state)
        engine.register_answer(state, record(first, "A2", 1.0))
        assert engine.next_skill(state) != first

    def test_para_no_maximo_de_itens(self):
        state = engine.TestState()
        for _ in range(engine.MAX_OBJECTIVE_ITEMS):
            engine.register_answer(state, record(Skill.READING, "A2", 1.0))
        assert engine.should_stop(state) is True

    def test_nao_para_antes_do_minimo(self):
        state = engine.TestState()
        for _ in range(engine.MIN_OBJECTIVE_ITEMS - 1):
            engine.register_answer(state, record(Skill.READING, "A2", 1.0))
        assert engine.should_stop(state) is False


class TestWeights:
    def test_todas_competencias(self):
        weights = engine.effective_weights(
            ["vocabulary_grammar", "reading", "listening", "writing", "speaking"]
        )
        assert all(abs(value - 0.20) < 1e-9 for value in weights.values())

    def test_sem_speaking(self):
        weights = engine.effective_weights(
            ["vocabulary_grammar", "reading", "listening", "writing"]
        )
        assert weights["vocabulary_grammar"] == 0.30
        assert weights["reading"] == 0.25
        assert weights["listening"] == 0.25
        assert weights["writing"] == 0.20

    def test_sem_listening_e_speaking(self):
        weights = engine.effective_weights(["vocabulary_grammar", "reading", "writing"])
        assert weights["vocabulary_grammar"] == 0.45
        assert weights["reading"] == 0.35
        assert weights["writing"] == 0.20

    def test_nunca_usa_media_simples_quando_falta_competencia(self):
        weights = engine.effective_weights(
            ["vocabulary_grammar", "reading", "listening", "writing"]
        )
        assert len(set(weights.values())) > 1
        assert abs(sum(weights.values()) - 1.0) < 1e-9


class TestOverallLevel:
    def test_exemplo_da_especificacao_nao_resulta_b2(self):
        """reading B2, vocab B2, listening B1, writing A2, speaking A2 -> não B2."""
        result, _ = engine.overall_level(
            levels(
                {
                    Skill.READING: "B2",
                    Skill.VOCABULARY_GRAMMAR: "B2",
                    Skill.LISTENING: "B1",
                    Skill.WRITING: "A2",
                    Skill.SPEAKING: "A2",
                }
            )
        )
        assert result != "B2"
        assert result == "B1"

    def test_limita_a_um_nivel_acima_da_menor_essencial(self):
        result, _ = engine.overall_level(
            levels(
                {
                    Skill.READING: "B2",
                    Skill.VOCABULARY_GRAMMAR: "B2",
                    Skill.LISTENING: "A1",
                }
            )
        )
        assert result == "A2"

    def test_sem_essenciais_usa_menor_avaliada(self):
        result, _ = engine.overall_level(
            levels({Skill.READING: "B2", Skill.VOCABULARY_GRAMMAR: "A2"})
        )
        assert result == "B1"

    def test_nao_classifica_em_c1_sem_itens_validados(self):
        result, _ = engine.overall_level(
            levels(
                {
                    Skill.READING: "C2",
                    Skill.VOCABULARY_GRAMMAR: "C2",
                    Skill.LISTENING: "C2",
                    Skill.SPEAKING: "C2",
                }
            )
        )
        assert result == "B2"

    def test_sem_resultados_retorna_none(self):
        result, weights = engine.overall_level({})
        assert result is None
        assert weights == {}


class TestConfidence:
    def test_dentro_do_intervalo(self):
        answers = [record(Skill.READING, "A2", 1.0) for _ in range(20)]
        value = engine.confidence(levels({Skill.READING: "A2"}), answers)
        assert 0 <= value <= 100

    def test_mais_itens_aumenta_confianca(self):
        skills = levels({Skill.READING: "A2", Skill.LISTENING: "A2"})
        poucos = engine.confidence(skills, [record(Skill.READING, "A2", 1.0) for _ in range(5)])
        muitos = engine.confidence(skills, [record(Skill.READING, "A2", 1.0) for _ in range(22)])
        assert muitos > poucos

    def test_dispersao_reduz_confianca(self):
        answers = [record(Skill.READING, "A2", 1.0) for _ in range(20)]
        consistente = engine.confidence(
            levels({Skill.READING: "B1", Skill.LISTENING: "B1"}), answers
        )
        disperso = engine.confidence(
            levels({Skill.READING: "B2", Skill.LISTENING: "PRE_A1"}), answers
        )
        assert disperso < consistente

    def test_respostas_muito_rapidas_reduzem_confianca(self):
        skills = levels({Skill.READING: "A2", Skill.LISTENING: "A2"})
        normal = engine.confidence(
            skills, [record(Skill.READING, "A2", 1.0, ms=8000) for _ in range(20)]
        )
        chute = engine.confidence(
            skills, [record(Skill.READING, "A2", 1.0, ms=300) for _ in range(20)]
        )
        assert chute < normal

    def test_rotulos(self):
        assert engine.confidence_label(80) == "alta"
        assert engine.confidence_label(50) == "moderada"
        assert engine.confidence_label(20) == "baixa"


class TestBuildResult:
    def test_registra_competencias_avaliadas_e_ausentes(self):
        answers = [record(Skill.READING, "A2", 1.0) for _ in range(4)]
        answers += [record(Skill.VOCABULARY_GRAMMAR, "A2", 1.0) for _ in range(4)]
        result = engine.build_result(answers, duration_seconds=300)

        assert set(result["assessed_skills"]) == {"reading", "vocabulary_grammar"}
        assert "speaking" in result["not_assessed_skills"]
        assert "listening" in result["not_assessed_skills"]
        assert result["weights_used"]

    def test_recomenda_competencia_abaixo_do_geral(self):
        answers = [record(Skill.READING, "B2", 1.0) for _ in range(4)]
        answers += [record(Skill.LISTENING, "A1", 0.0) for _ in range(4)]
        result = engine.build_result(answers)
        skills_recomendadas = {item["skill"] for item in result["recommendations"]}
        assert Skill.LISTENING in skills_recomendadas or Skill.SPEAKING in skills_recomendadas

    def test_speaking_nao_avaliada_gera_recomendacao(self):
        answers = [record(Skill.READING, "A2", 1.0) for _ in range(4)]
        result = engine.build_result(answers)
        recomendacoes = {
            (item["skill"], item["reason"]) for item in result["recommendations"]
        }
        assert (Skill.SPEAKING, "not_assessed") in recomendacoes


class TestSkillEstimation:
    def test_poucos_itens_nao_geram_estimativa(self):
        assert engine.estimate_skill_level([record(Skill.READING, "A2", 1.0)]) is None

    def test_faixa_dominada_define_nivel(self):
        answers = [record(Skill.READING, "B1", 1.0) for _ in range(4)]
        assert engine.estimate_skill_level(answers) == "B1"

    def test_sem_dominio_fica_abaixo_da_menor_faixa(self):
        answers = [record(Skill.READING, "A2", 0.0) for _ in range(4)]
        assert engine.estimate_skill_level(answers) == "A1"
