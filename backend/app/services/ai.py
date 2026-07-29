"""Provedores de IA do BeFluent.

Dois caminhos, mesmo contrato de saída:

* `OpenRouterProvider` — renderiza o prompt da biblioteca (`app/prompts/library`)
  com o contexto do aluno e pede JSON estruturado ao modelo.
* `MockAIProvider` — monta a lição a partir de `lesson_bank`, que varia por faixa
  de nível. É o caminho ativo quando `AI_MOCK_MODE=true` (padrão do projeto).

Em ambos os casos a lição é calibrada pelo `LearnerContext`, ou seja, pelo
resultado do teste de nivelamento.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
from app.core.levels import LEVEL_INDEX, SKILL_LABELS, CEFRLevel
from app.core.levels import Skill
from app.prompts.library import (
    CONVERSATION,
    MODE_SKILL,
    get_mode_prompt,
    get_output_contract,
)
from app.services import lesson_bank
from app.services.learner_context import LearnerContext


#: Abaixo deste nível, o tutor acompanha cada fala com tradução — é a regra do
#: prompt de conversação ("tradução entre parênteses quando o nível exigir").
TRANSLATION_THRESHOLD = CEFRLevel.B1


class BaseAIProvider(ABC):
    @abstractmethod
    def conversation(self, text: str, language_code: str) -> dict: ...

    @abstractmethod
    def conversation_turn(
        self, text: str, context: LearnerContext, history: list[dict]
    ) -> dict: ...

    @abstractmethod
    def generate_lesson(self, mode: str, context: LearnerContext) -> dict: ...


def _needs_translation(level: str) -> bool:
    return LEVEL_INDEX[level] < LEVEL_INDEX[TRANSLATION_THRESHOLD]


def _conversation_envelope(context: LearnerContext, payload: dict, provider: str) -> dict:
    level = context.level_for_skill(MODE_SKILL["conversation"])
    return {
        "reply": payload.get("reply", ""),
        "reply_translation": payload.get("reply_translation"),
        "corrections": payload.get("corrections") or [],
        "natural_alternative": payload.get("natural_alternative"),
        "suggestions": payload.get("suggestions") or [],
        "corrections_available": payload.get("corrections_available", True),
        "provider": provider,
        "level": level,
        "level_source": context.level_source,
        "level_is_estimated": context.level_is_estimated,
        "shows_translation": _needs_translation(level),
    }


def _envelope(mode: str, context: LearnerContext, payload: dict, provider: str) -> dict:
    """Metadados comuns a toda lição: o que foi adaptado e com base em quê.

    O frontend usa isso para mostrar ao aluno por que aquela lição é aquela —
    sem isso a adaptação fica invisível e indistinguível de conteúdo fixo.
    """
    skill = MODE_SKILL.get(mode)
    return {
        **payload,
        "mode": mode,
        "provider": provider,
        "language_code": context.language_code,
        "level": context.level_for_skill(skill),
        "overall_level": context.level,
        "skill": skill,
        "skill_label": SKILL_LABELS.get(skill) if skill else None,
        "level_source": context.level_source,
        "level_is_estimated": context.level_is_estimated,
    }


class MockAIProvider(BaseAIProvider):
    """Conteúdo determinístico por faixa de nível, sem chamada externa."""

    def conversation(self, text, language_code):
        return {
            "reply": f"Resposta simulada em {language_code}: {text}",
            "corrections": [],
            "suggestions": ["Continue praticando!"],
            "provider": "mock",
        }

    def conversation_turn(self, text, context, history):
        """Avança um roteiro de prática no nível do aluno.

        Não devolve correções: analisar gramática exige o modelo. Fabricar uma
        correção aqui seria pior do que não corrigir — o aluno confiaria em algo
        que ninguém verificou. `corrections_available=False` diz isso à interface.
        """
        level = context.level_for_skill(MODE_SKILL["conversation"])
        band = lesson_bank.band_for(level)
        vocab = lesson_bank.VOCABULARY.get(
            context.language_code, lesson_bank.VOCABULARY["en"]
        )
        items = vocab.get(band) or vocab[lesson_bank.BAND_ELEMENTARY]

        # Uma fala do tutor por turno já ocorrido, dando a volta ao fim do roteiro.
        turn = sum(1 for message in history if message.get("role") == "assistant")
        item = items[turn % len(items)]

        return _conversation_envelope(
            context,
            {
                "reply": item["example"],
                "reply_translation": (
                    item["example_translation"] if _needs_translation(level) else None
                ),
                "corrections": [],
                "corrections_available": False,
                "suggestions": [other["term"] for other in items[:3]],
            },
            "mock",
        )

    def generate_lesson(self, mode: str, context: LearnerContext) -> dict:
        skill = MODE_SKILL.get(mode)
        level = context.level_for_skill(skill)
        band = lesson_bank.band_for(level)
        builder = _MOCK_BUILDERS.get(mode)
        if not builder:
            raise ValueError(mode)
        return _envelope(mode, context, builder(context, band, level), "mock")


# ---------------------------------------------------------------------------
# Construtores mock por modo
# ---------------------------------------------------------------------------


def _vocabulary(context: LearnerContext, band: str, level: str) -> dict:
    by_language = lesson_bank.VOCABULARY.get(
        context.language_code, lesson_bank.VOCABULARY["en"]
    )
    items = by_language.get(band) or by_language[lesson_bank.BAND_ELEMENTARY]
    return {
        "title": f"Vocabulário essencial · {level}",
        "objective": (
            "Ampliar o vocabulário de alta frequência que você já consegue usar "
            "no seu nível atual."
        ),
        "items": list(items),
    }


def _grammar(context: LearnerContext, band: str, level: str) -> dict:
    focus = lesson_bank.GRAMMAR_FOCUS[band]
    exercises = _GRAMMAR_EXERCISES.get(context.language_code, {}).get(band)
    return {
        "title": f"{focus['title']} · {level}",
        "objective": focus["objective"],
        "explanation": focus["explanation"],
        "patterns": list(focus["patterns"]),
        "examples": _GRAMMAR_EXAMPLES.get(context.language_code, {}).get(band, []),
        "exercises": exercises or [],
    }


def _reading(context: LearnerContext, band: str, level: str) -> dict:
    text = lesson_bank.READING_TEXTS[band]
    return {
        "title": f"{text['title']} · {level}",
        "objective": "Ler um texto calibrado para o seu nível e verificar a compreensão.",
        "text": text["text"],
        "note": text["note"],
        "glossary": [],
        "questions": [
            {
                "prompt": "Qual é a ideia principal do texto?",
                "options": [
                    "Uma descrição de rotina ou situação concreta.",
                    "Uma lista de instruções técnicas.",
                    "Um diálogo entre duas pessoas.",
                ],
                "answer": "Uma descrição de rotina ou situação concreta.",
            }
        ],
    }


def _listening(context: LearnerContext, band: str, level: str) -> dict:
    script = lesson_bank.LISTENING_SCRIPTS[band]
    return {
        "title": f"Compreensão auditiva · {level}",
        "objective": "Treinar escuta ativa com um objetivo definido, não escuta de fundo.",
        "transcript": script["transcript"],
        "speaking_rate": script["speaking_rate"],
        "note": script["note"],
        "questions": [
            {
                "prompt": "Qual é a informação central do áudio?",
                "options": [
                    "Uma informação prática sobre uma situação concreta.",
                    "Uma opinião sobre política internacional.",
                    "Uma receita de cozinha.",
                ],
                "answer": "Uma informação prática sobre uma situação concreta.",
            }
        ],
    }


def _writing(context: LearnerContext, band: str, level: str) -> dict:
    task = lesson_bank.WRITING_TASKS[band]
    return {
        "title": f"Produção escrita · {level}",
        "objective": "Produzir um texto no seu nível e receber correção estruturada.",
        "prompt": task["prompt"],
        "min_words": task["min_words"],
        "max_words": task["max_words"],
        "rubric_hints": list(task["rubric_hints"]),
        "useful_expressions": [],
    }


def _conversation(context: LearnerContext, band: str, level: str) -> dict:
    situation = lesson_bank.CONVERSATION_SITUATIONS[band]
    vocab = lesson_bank.VOCABULARY.get(context.language_code, lesson_bank.VOCABULARY["en"])
    items = vocab.get(band) or vocab[lesson_bank.BAND_ELEMENTARY]
    return {
        "title": f"Conversação · {level}",
        "objective": f"Praticar {situation['focus']} em uma situação realista.",
        "situation": situation["situation"],
        "opening": items[0]["example"],
        # Mesma regra dos turnos: acima de B1 o aluno pratica sem tradução.
        "opening_translation": (
            items[0]["example_translation"] if _needs_translation(level) else None
        ),
        "suggested_replies": [item["example"] for item in items[1:4]],
        "target_expressions": [item["term"] for item in items[:4]],
    }


def _pronunciation(context: LearnerContext, band: str, level: str) -> dict:
    sounds = lesson_bank.PRONUNCIATION_FOCUS.get(
        context.language_code, lesson_bank.PRONUNCIATION_FOCUS["en"]
    )
    vocab = lesson_bank.VOCABULARY.get(context.language_code, lesson_bank.VOCABULARY["en"])
    items = vocab.get(band) or vocab[lesson_bank.BAND_ELEMENTARY]
    return {
        "title": f"Pronúncia · {level}",
        "objective": "Treinar os sons que mais comprometem a compreensão.",
        "focus_sounds": list(sounds),
        "target_phrases": [
            {
                "phrase": item["example"],
                "translation": item["example_translation"],
                "focus": item["term"],
            }
            for item in items[:4]
        ],
    }


def _guided(context: LearnerContext, band: str, level: str) -> dict:
    focus = lesson_bank.GRAMMAR_FOCUS[band]
    examples = _GRAMMAR_EXAMPLES.get(context.language_code, {}).get(band, [])
    steps = [
        {
            "title": "A lógica",
            "explanation": focus["explanation"],
            "example": examples[0]["sentence"] if examples else "",
            "example_translation": examples[0]["translation"] if examples else "",
        }
    ]
    for index, pattern in enumerate(list(focus["patterns"])[:2], start=1):
        example = examples[index] if len(examples) > index else None
        steps.append(
            {
                "title": f"Padrão {index}",
                "explanation": pattern,
                "example": example["sentence"] if example else "",
                "example_translation": example["translation"] if example else "",
            }
        )
    return {
        "title": f"{focus['title']} · {level}",
        "objective": focus["objective"],
        "steps": steps,
        "check_question": (
            "Explique com suas palavras, sem repetir o exemplo: quando você usaria "
            "essa estrutura numa conversa real?"
        ),
    }


def _review(context: LearnerContext, band: str, level: str) -> dict:
    vocab = lesson_bank.VOCABULARY.get(context.language_code, lesson_bank.VOCABULARY["en"])
    items = vocab.get(band) or vocab[lesson_bank.BAND_ELEMENTARY]
    return {
        "title": f"Revisão ativa · {level}",
        "objective": "Recuperar da memória antes de ver a resposta — é o esforço que fixa.",
        "items": [
            {
                "prompt": f"Como se diz “{item['translation']}”?",
                "answer": item["term"],
                "hint": item["example_translation"],
            }
            for item in items
        ],
    }


_MOCK_BUILDERS = {
    "vocabulary": _vocabulary,
    "grammar": _grammar,
    "reading": _reading,
    "listening": _listening,
    "writing": _writing,
    "conversation": _conversation,
    "voice": _conversation,
    "pronunciation": _pronunciation,
    "guided": _guided,
    "review": _review,
}


#: Exemplos e exercícios de gramática do banco mock. Só inglês tem cobertura
#: completa; os demais idiomas caem no vocabulário da faixa, que é multilíngue.
_GRAMMAR_EXAMPLES: dict[str, dict[str, list[dict[str, str]]]] = {
    "en": {
        lesson_bank.BAND_BEGINNER: [
            {"sentence": "What is your name?", "translation": "Qual é o seu nome?"},
            {"sentence": "Where are you from?", "translation": "De onde você é?"},
            {"sentence": "What do you do?", "translation": "O que você faz?"},
        ],
        lesson_bank.BAND_ELEMENTARY: [
            {"sentence": "I worked late yesterday.", "translation": "Eu trabalhei até tarde ontem."},
            {"sentence": "I usually work from home.", "translation": "Eu normalmente trabalho de casa."},
            {"sentence": "She called, then she left.", "translation": "Ela ligou, depois saiu."},
        ],
        lesson_bank.BAND_INTERMEDIATE: [
            {"sentence": "I have been to Paris three times.", "translation": "Já estive em Paris três vezes."},
            {"sentence": "I went to Paris in 2019.", "translation": "Fui a Paris em 2019."},
            {"sentence": "I have been working here since March.", "translation": "Trabalho aqui desde março."},
        ],
        lesson_bank.BAND_UPPER: [
            {"sentence": "That might explain the delay.", "translation": "Isso talvez explique o atraso."},
            {"sentence": "If we had known, we would have waited.", "translation": "Se soubéssemos, teríamos esperado."},
            {"sentence": "It is arguably the better option.", "translation": "É, discutivelmente, a melhor opção."},
        ],
    }
}

_GRAMMAR_EXERCISES: dict[str, dict[str, list[dict]]] = {
    "en": {
        lesson_bank.BAND_BEGINNER: [
            {
                "prompt": "____ is your name?",
                "options": ["What", "Where", "Who"],
                "answer": "What",
                "rationale": "'What' pergunta pela informação; 'Where' pergunta lugar.",
            }
        ],
        lesson_bank.BAND_ELEMENTARY: [
            {
                "prompt": "I ____ late yesterday.",
                "options": ["worked", "work", "am working"],
                "answer": "worked",
                "rationale": "'Yesterday' fecha o tempo, então o passado simples é obrigatório.",
            }
        ],
        lesson_bank.BAND_INTERMEDIATE: [
            {
                "prompt": "I ____ to Paris three times.",
                "options": ["have been", "went", "was going"],
                "answer": "have been",
                "rationale": "Não há momento passado fechado: o que importa é a experiência acumulada.",
            }
        ],
        lesson_bank.BAND_UPPER: [
            {
                "prompt": "If we ____ earlier, we would have caught the train.",
                "options": ["had left", "left", "have left"],
                "answer": "had left",
                "rationale": "Hipótese contrafactual sobre o passado exige o mais-que-perfeito.",
            }
        ],
    }
}


class OpenRouterProvider(BaseAIProvider):
    def __init__(self):
        self.s = get_settings()

    @property
    def openrouter_ready(self) -> bool:
        return bool(self.s.openrouter_api_key and self.s.openrouter_model)

    def conversation(self, text, language_code):
        if not self.s.openrouter_api_key or not self.s.openrouter_model:
            return MockAIProvider().conversation(text, language_code)
        payload = {
            "model": self.s.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": f"Responda como tutor de {language_code} em JSON.",
                },
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            r = httpx.post(
                f"{self.s.openrouter_base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.s.openrouter_api_key}"},
                timeout=30,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return {
                "reply": content,
                "corrections": [],
                "suggestions": [],
                "provider": "openrouter",
            }
        except httpx.HTTPError as exc:
            raise RuntimeError("Falha temporária no serviço de IA.") from exc

    def conversation_turn(self, text, context, history):
        """Um turno de conversa pelo prompt do documento (Parte II · 3).

        Cai no mock em qualquer falha: o aluno no meio de um diálogo não pode
        receber um erro no lugar da resposta do tutor.
        """
        if not self.openrouter_ready:
            return MockAIProvider().conversation_turn(text, context, history)

        level = context.level_for_skill(MODE_SKILL["conversation"])
        contract = (
            '{"reply": str, "reply_translation": str|null, '
            '"corrections": [{"original": str, "corrected": str, "explanation": str}], '
            '"natural_alternative": str|null, "suggestions": [str]}'
        )
        instruction = CONVERSATION.render(context.to_prompt_context(Skill.SPEAKING), contract)
        if _needs_translation(level):
            instruction += (
                "\n\nO nível do aluno exige tradução: preencha `reply_translation` "
                "com a tradução em português da sua fala."
            )
        else:
            instruction += "\n\nO aluno dispensa tradução: deixe `reply_translation` nulo."

        messages = [{"role": "system", "content": instruction}]
        for message in history[-10:]:
            messages.append(
                {
                    "role": "assistant" if message.get("role") == "assistant" else "user",
                    "content": message.get("content", ""),
                }
            )
        messages.append({"role": "user", "content": text})

        try:
            response = httpx.post(
                f"{self.s.openrouter_base_url}/chat/completions",
                json={
                    "model": self.s.openrouter_model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                },
                headers={"Authorization": f"Bearer {self.s.openrouter_api_key}"},
                timeout=45,
            )
            response.raise_for_status()
            payload = json.loads(response.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("OpenRouter conversation_turn falhou; usando mock: %s", exc)
            return MockAIProvider().conversation_turn(text, context, history)

        if not isinstance(payload, dict) or not payload.get("reply"):
            logger.warning("OpenRouter conversation_turn sem reply válido; usando mock")
            return MockAIProvider().conversation_turn(text, context, history)
        return _conversation_envelope(context, payload, "openrouter")

    def generate_lesson(self, mode: str, context: LearnerContext) -> dict:
        """Gera a lição pelo prompt da biblioteca; cai no mock em qualquer falha.

        A lição nunca deve falhar por indisponibilidade do modelo: o aluno
        recebe o conteúdo do banco, com `provider` indicando a origem.
        """
        template = get_mode_prompt(mode)
        if not template:
            raise ValueError(mode)
        if not self.s.openrouter_api_key or not self.s.openrouter_model:
            return MockAIProvider().generate_lesson(mode, context)

        skill = MODE_SKILL.get(mode)
        prompt = template.render(
            context.to_prompt_context(skill), get_output_contract(mode)
        )
        payload = {
            "model": self.s.openrouter_model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        try:
            response = httpx.post(
                f"{self.s.openrouter_base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.s.openrouter_api_key}"},
                timeout=45,
            )
            response.raise_for_status()
            content = json.loads(response.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("OpenRouter generate_lesson(%s) falhou; usando mock: %s", mode, exc)
            return MockAIProvider().generate_lesson(mode, context)

        if not isinstance(content, dict) or not content.get("title"):
            logger.warning("OpenRouter generate_lesson(%s) sem title válido; usando mock", mode)
            return MockAIProvider().generate_lesson(mode, context)
        return _envelope(mode, context, content, "openrouter")


def get_ai_provider() -> BaseAIProvider:
    s = get_settings()
    if s.ai_mock_mode:
        logger.info("IA em MockAIProvider (AI_MOCK_MODE=true)")
        return MockAIProvider()
    if not s.openrouter_api_key:
        logger.warning("IA em MockAIProvider (OPENROUTER_API_KEY ausente)")
        return MockAIProvider()
    return OpenRouterProvider()
