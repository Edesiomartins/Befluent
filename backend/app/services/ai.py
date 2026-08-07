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

    `thread` é a continuidade declarada: de onde veio o material reaproveitado.
    Vale para os dois provedores — no mock ele é garantido pelos construtores
    abaixo; no OpenRouter é uma instrução do prompt, então o campo diz o que foi
    **pedido**, não o que o modelo comprovadamente usou.
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
        "thread": {
            "carried_terms": context.carryover_terms,
            "carried_patterns": list(context.carryover_patterns),
            "sources": list(context.carryover_sources),
            "recycled_terms": context.recycled_terms,
            "guaranteed": provider == "mock",
        },
    }


# --------------------------------------------------------------------- o fio
#
# O mock precisa reaproveitar o material dos blocos anteriores do dia. Sem isto,
# o cronograma volta a ser cinco lições independentes: `lesson_bank` devolve a
# mesma lista por faixa de nível, então o bloco de conversação do dia 40 abriria
# com as mesmas palavras do dia 3 — e nenhuma delas seria a que o aluno acabou
# de estudar no bloco anterior.


def _carried(context: LearnerContext) -> list[dict[str, str]]:
    """Itens que este bloco herdou, do mais recente para o mais antigo."""
    return [*context.carryover_items, *context.recycled_items]


def _rotate(items: list, context: LearnerContext) -> list:
    """Gira o banco pelo número do dia.

    O banco é pequeno e declaradamente provisório: girar não cria conteúdo novo,
    mas evita que dois dias na mesma faixa abram exatamente iguais — que é o que
    fazia o cronograma parecer parado.
    """
    if not items or not context.day_number:
        return list(items)
    offset = (context.day_number - 1) % len(items)
    return [*items[offset:], *items[:offset]]


def _target_items(context: LearnerContext, band: str, count: int = 4) -> list[dict[str, str]]:
    """Léxico de trabalho do bloco: o herdado primeiro, o banco só completa."""
    carried = [item for item in _carried(context) if item.get("term")]
    if len(carried) >= count:
        return carried[:count]

    known = {item["term"].casefold() for item in carried}
    extra = [
        item
        for item in _rotate(lesson_bank.vocabulary(context.language_code, band), context)
        if item["term"].casefold() not in known
    ]
    return [*carried, *extra[: count - len(carried)]]


def _phrases(items: list[dict[str, str]]) -> list[dict[str, str]]:
    """Itens com exemplo utilizável. Um termo herdado sem frase não vira alvo
    de pronúncia: mandar o aluno repetir uma palavra solta não treina ritmo."""
    return [item for item in items if item.get("example")]


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
        items = lesson_bank.vocabulary(context.language_code, band)

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
    """Bloco que **abre** o dia: é ele que define o léxico dos blocos seguintes.

    Os itens saem girados pelo número do dia, e o léxico dos dias anteriores da
    semana entra separado, marcado como retomada — misturar os dois faria o
    aluno achar que está aprendendo palavra nova quando está revendo.
    """
    items = _rotate(lesson_bank.vocabulary(context.language_code, band), context)
    revisited = [item for item in context.recycled_items if item.get("term")]
    return {
        "title": f"Vocabulário essencial · {level}",
        "objective": (
            "Ampliar o vocabulário de alta frequência que você já consegue usar "
            "no seu nível atual. Estas palavras voltam nos próximos blocos de hoje."
        ),
        "items": list(items),
        "revisited_items": revisited[:3],
        "thread_note": (
            "As palavras deste bloco são o material dos blocos seguintes: você vai "
            "reencontrá-las na estrutura, no texto ou áudio, na produção e na revisão."
        ),
    }


def _grammar(context: LearnerContext, band: str, level: str) -> dict:
    """Estrutura aplicada ao léxico que acabou de ser ativado."""
    focus = lesson_bank.grammar_focus(context.language_code, band)
    carried = [item for item in _carried(context) if item.get("term")][:4]
    return {
        "title": f"{focus['title']} · {level}",
        "objective": focus["objective"],
        "explanation": focus["explanation"],
        "patterns": list(focus["patterns"]),
        "examples": lesson_bank.grammar_examples(context.language_code, band),
        "exercises": lesson_bank.grammar_exercises(context.language_code, band),
        "apply_to_terms": [item["term"] for item in carried],
        "thread_note": (
            "Monte uma frase com cada padrão acima usando as palavras que você "
            "acabou de ver no bloco de vocabulário."
            if carried
            else None
        ),
    }


def _reading(context: LearnerContext, band: str, level: str) -> dict:
    """Texto do banco, mas com o glossário do dia — não um glossário genérico."""
    text = lesson_bank.reading_text(context.language_code, band)
    carried = [item for item in _carried(context) if item.get("term")]
    return {
        "title": f"{text['title']} · {level}",
        "objective": "Ler um texto calibrado para o seu nível e verificar a compreensão.",
        "text": text["text"],
        "note": text["note"],
        "glossary": [
            {"term": item["term"], "translation": item.get("translation", "")}
            for item in carried[:6]
        ],
        "watch_for": [item["term"] for item in carried[:4]],
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
    """Escuta com objetivo ativo: caçar no áudio as palavras do bloco anterior."""
    script = lesson_bank.listening_script(context.language_code, band)
    carried = [item for item in _carried(context) if item.get("term")]
    return {
        "title": f"Compreensão auditiva · {level}",
        "objective": (
            "Treinar escuta ativa com um objetivo definido, não escuta de fundo."
            if not carried
            else "Escutar procurando as palavras que você ativou no início do dia."
        ),
        "transcript": script["transcript"],
        "speaking_rate": script["speaking_rate"],
        "note": script["note"],
        "watch_for": [item["term"] for item in carried[:4]],
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
    """Produção escrita com as expressões do dia como material obrigatório."""
    task = lesson_bank.writing_task(context.language_code, band)
    carried = [item for item in _carried(context) if item.get("term")]
    return {
        "title": f"Produção escrita · {level}",
        "objective": "Produzir um texto no seu nível e receber correção estruturada.",
        "prompt": task["prompt"],
        "min_words": task["min_words"],
        "max_words": task["max_words"],
        "rubric_hints": list(task["rubric_hints"]),
        "useful_expressions": [item["term"] for item in carried[:6]],
        "must_use": [item["term"] for item in carried[:3]],
        "thread_note": (
            "Use no texto, obrigatoriamente, as expressões marcadas — é assim que "
            "vocabulário reconhecido vira vocabulário produzido."
            if carried
            else None
        ),
    }


def _conversation(context: LearnerContext, band: str, level: str) -> dict:
    """Produção falada sobre o léxico e as estruturas já vistos no dia."""
    situation = lesson_bank.conversation_situation(context.language_code, band)
    working = _target_items(context, band, count=4)
    openers = _phrases(working) or _phrases(
        _rotate(lesson_bank.vocabulary(context.language_code, band), context)
    )
    opener = openers[0]
    return {
        "title": f"Conversação · {level}",
        "objective": f"Praticar {situation['focus']} em uma situação realista.",
        "situation": situation["situation"],
        "opening": opener["example"],
        # Mesma regra dos turnos: acima de B1 o aluno pratica sem tradução.
        "opening_translation": (
            opener.get("example_translation") if _needs_translation(level) else None
        ),
        "suggested_replies": [item["example"] for item in openers[1:4]],
        "target_expressions": [item["term"] for item in working],
        "thread_note": (
            "As expressões-alvo são as do bloco de vocabulário de hoje."
            if context.carryover_items
            else None
        ),
    }


def _pronunciation(context: LearnerContext, band: str, level: str) -> dict:
    """Sons do idioma treinados nas frases do léxico do dia."""
    sounds = lesson_bank.pronunciation_focus(context.language_code)
    working = _phrases(_target_items(context, band, count=6)) or _phrases(
        _rotate(lesson_bank.vocabulary(context.language_code, band), context)
    )
    return {
        "title": f"Pronúncia · {level}",
        "objective": "Treinar os sons que mais comprometem a compreensão.",
        "focus_sounds": list(sounds),
        "target_phrases": [
            {
                "phrase": item["example"],
                "translation": item.get("example_translation", ""),
                "focus": item["term"],
            }
            for item in working[:4]
        ],
    }


def _guided(context: LearnerContext, band: str, level: str) -> dict:
    focus = lesson_bank.grammar_focus(context.language_code, band)
    examples = lesson_bank.grammar_examples(context.language_code, band)
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
    """Recuperação ativa do que foi visto — hoje primeiro, banco só se faltar.

    No cronograma o bloco de revisão vem da fila real do SRS
    (`progression._review_payload`); este construtor atende as lições avulsas e
    o caso em que o fio existe mas a fila ainda não.
    """
    items = [
        item
        for item in _carried(context)
        if item.get("term") and item.get("translation")
    ] or list(lesson_bank.vocabulary(context.language_code, band))
    return {
        "title": f"Revisão ativa · {level}",
        "objective": "Recuperar da memória antes de ver a resposta — é o esforço que fixa.",
        "items": [
            {
                "prompt": f"Como se diz “{item['translation']}”?",
                "answer": item["term"],
                "hint": item.get("example_translation") or item.get("example", ""),
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
