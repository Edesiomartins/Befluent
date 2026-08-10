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
from app.core.errors import APIError

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
from app.services.vocabulary_selection import select_daily_vocabulary


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


def _conversation_envelope(
    context: LearnerContext, payload: dict, provider: str, model: str | None = None
) -> dict:
    level = context.level_for_skill(MODE_SKILL["conversation"])
    return {
        "reply": payload.get("reply", ""),
        "reply_translation": payload.get("reply_translation"),
        "corrections": payload.get("corrections") or [],
        "natural_alternative": payload.get("natural_alternative"),
        "suggestions": payload.get("suggestions") or [],
        "corrections_available": payload.get("corrections_available", True),
        "provider": provider,
        "model": model,
        "level": level,
        "level_source": context.level_source,
        "level_is_estimated": context.level_is_estimated,
        "shows_translation": _needs_translation(level),
    }


def _envelope(
    mode: str, context: LearnerContext, payload: dict, provider: str, model: str | None = None
) -> dict:
    """Metadados comuns a toda lição: o que foi adaptado e com base em quê.

    O frontend usa isso para mostrar ao aluno por que aquela lição é aquela —
    sem isso a adaptação fica invisível e indistinguível de conteúdo fixo.

    `thread` é a continuidade declarada: de onde veio o material reaproveitado.
    Vale para os dois provedores — no mock ele é garantido pelos construtores
    abaixo; no OpenRouter é uma instrução do prompt, então o campo diz o que foi
    **pedido**, não o que o modelo comprovadamente usou.
    """
    from app.services.lesson_envelope import apply_lesson_envelope

    return apply_lesson_envelope(
        payload,
        context=context,
        mode=mode,
        provider=provider,
        content_origin=provider,
        model=model,
        thread_guaranteed=provider == "mock",
    )


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
    selected = select_daily_vocabulary(
        context.language_code,
        band,
        day_number=context.day_number,
        week_theme=context.curriculum_week_theme,
        recycled_items=context.recycled_items,
        exposed_items=context.exposed_items,
        count=count,
    )
    extra = [
        item
        for item in selected["new_items"]
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

    `items` = léxico **novo** do dia (subconjunto do banco, preferindo o tema
    da semana). `revisited_items` = spiral da semana (não misturar com SRS).
    """
    selected = select_daily_vocabulary(
        context.language_code,
        band,
        day_number=context.day_number,
        week_theme=context.curriculum_week_theme,
        recycled_items=context.recycled_items,
        exposed_items=context.exposed_items,
    )
    return {
        "title": f"Vocabulário essencial · {level}",
        "objective": (
            "Ampliar o vocabulário de alta frequência que você já consegue usar "
            "no seu nível atual. Estas palavras voltam nos próximos blocos de hoje."
        ),
        "items": list(selected["new_items"]),
        "revisited_items": list(selected["revisited_items"]),
        "selection_policy": selected["selection_policy"],
        "content_roles": dict(selected["content_roles"]),
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
                "rationale": (
                    "O texto do banco apresenta uma situação concreta ou rotina "
                    "calibrada ao nível — não um manual técnico nem um diálogo."
                ),
                "option_rationales": {
                    "Uma descrição de rotina ou situação concreta.": (
                        "Corresponde ao tipo de texto usado nesta faixa."
                    ),
                    "Uma lista de instruções técnicas.": (
                        "O texto não é um passo a passo técnico."
                    ),
                    "Um diálogo entre duas pessoas.": (
                        "Não há turnos de fala entre personagens."
                    ),
                },
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
                "rationale": (
                    "Os scripts do banco trazem informação prática de uma situação "
                    "cotidiana, não opinião política nem receita."
                ),
                "option_rationales": {
                    "Uma informação prática sobre uma situação concreta.": (
                        "Alinha com o objetivo de escuta desta faixa."
                    ),
                    "Uma opinião sobre política internacional.": (
                        "O áudio não discute política."
                    ),
                    "Uma receita de cozinha.": (
                        "Não há passos de preparo de comida no script."
                    ),
                },
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


class OpenRouterUnavailableError(RuntimeError):
    """Nenhum modelo OpenRouter (primário nem fallback) respondeu com um payload válido.

    Reusado fora deste módulo (`app.services.writing_evaluation`) — é o mesmo
    contrato de falha para toda chamada OpenRouter do backend.
    """


def _openrouter_completion(
    s, model: str, messages: list[dict], timeout: int
) -> dict:
    from app.services.provider_resilience import call_with_policy

    def _once() -> dict:
        response = httpx.post(
            f"{s.openrouter_base_url}/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            headers={"Authorization": f"Bearer {s.openrouter_api_key}"},
            timeout=timeout,
        )
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"])

    # max_retries=0: uma tentativa no modelo; falha → fallback de modelo
    # (evita primary×2 + fallback×2). 429 ainda pode ter 1 retry interno.
    result = call_with_policy(
        provider_name=f"openrouter:{model}",
        operation=_once,
        max_retries=0,
        base_backoff=0.4,
    )
    logger.info(
        "ai_capability=chat provider=openrouter model=%s attempts=%s rate_limited=%s circuit=%s",
        model,
        result.attempts,
        result.rate_limited,
        result.circuit_state,
    )
    if not result.ok:
        if result.error is not None:
            raise result.error
        raise OpenRouterUnavailableError("OpenRouter indisponível.")
    return result.value  # type: ignore[return-value]


def openrouter_chat_with_fallback(
    s, messages: list[dict], is_valid, timeout: int = 45
) -> tuple[dict, str]:
    """Tenta o modelo primário e, se falhar, o modelo de fallback do OpenRouter.

    `is_valid` julga o payload já parseado: uma resposta 200 fora do contrato
    esperado é tratada como falha para efeito de fallback, não é repassada ao
    chamador como se fosse válida. Único ponto de chamada OpenRouter do
    backend — reusado por `conversation_turn`, `generate_lesson` e pela
    avaliação de escrita (`app.services.writing_evaluation`) para evitar
    duplicar a lógica de tentativa/registro entre eles.

    401/403/404 não entram em retry infinito (ver `provider_resilience`).
    429 respeita Retry-After quando disponível.
    """
    models = [m for m in (s.openrouter_model, s.openrouter_fallback_model) if m]
    last_error: Exception | None = None
    for index, model in enumerate(models):
        try:
            payload = _openrouter_completion(s, model, messages, timeout)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning("OpenRouter modelo %s falhou HTTP %s", model, status)
            last_error = exc
            # Auth / not found: não martelar o próximo com a mesma chave inválida
            # em loop; ainda assim tenta o fallback de modelo uma vez.
            if status in (401, 403) and index == 0 and len(models) > 1:
                continue
            if status in (401, 403, 404):
                break
            continue
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
            logger.warning("OpenRouter modelo %s falhou: %s", model, exc)
            last_error = exc
            continue
        if not is_valid(payload):
            logger.warning("OpenRouter modelo %s respondeu fora do contrato esperado", model)
            last_error = ValueError("invalid_payload")
            continue
        if index > 0:
            logger.info("ai_fallback_used provider=openrouter model=%s", model)
        return payload, model
    raise OpenRouterUnavailableError("Nenhum modelo OpenRouter respondeu.") from last_error


class OpenRouterProvider(BaseAIProvider):
    def __init__(self):
        self.s = get_settings()

    @property
    def openrouter_ready(self) -> bool:
        models = [m for m in (self.s.openrouter_model, self.s.openrouter_fallback_model) if m]
        return bool(self.s.openrouter_api_key and models)

    def _unavailable_or_dev_mock(self, mock_factory):
        """Ponto único de decisão em caso de indisponibilidade da IA.

        Em produção uma falha real de IA nunca vira conteúdo simulado — o
        chamador recebe um erro explícito e recuperável (503). Fora de
        produção, o mock preserva o fluxo de desenvolvimento sem exigir
        credenciais reais.
        """
        if self.s.environment == "production":
            raise APIError(
                503,
                "ai_unavailable",
                "O serviço de IA está temporariamente indisponível.",
                retryable=True,
            )
        logger.warning("IA indisponível fora de produção; usando MockAIProvider (desenvolvimento)")
        return mock_factory()

    def conversation(self, text, language_code):
        if not self.openrouter_ready:
            return self._unavailable_or_dev_mock(
                lambda: MockAIProvider().conversation(text, language_code)
            )
        messages = [
            {
                "role": "system",
                "content": f"Responda como tutor de {language_code} em JSON.",
            },
            {"role": "user", "content": text},
        ]
        try:
            payload, model = openrouter_chat_with_fallback(
                self.s, messages, lambda p: isinstance(p, dict) and bool(p.get("reply"))
            )
        except OpenRouterUnavailableError:
            return self._unavailable_or_dev_mock(
                lambda: MockAIProvider().conversation(text, language_code)
            )
        return {
            "reply": payload.get("reply", ""),
            "corrections": payload.get("corrections") or [],
            "suggestions": payload.get("suggestions") or [],
            "provider": "openrouter",
            "model": model,
        }

    def conversation_turn(self, text, context, history):
        """Um turno de conversa pelo prompt do documento (Parte II · 3)."""
        if not self.openrouter_ready:
            return self._unavailable_or_dev_mock(
                lambda: MockAIProvider().conversation_turn(text, context, history)
            )

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
            payload, model = openrouter_chat_with_fallback(
                self.s,
                messages,
                lambda p: isinstance(p, dict) and bool(p.get("reply")),
            )
        except OpenRouterUnavailableError:
            return self._unavailable_or_dev_mock(
                lambda: MockAIProvider().conversation_turn(text, context, history)
            )
        return _conversation_envelope(context, payload, "openrouter", model)

    def generate_lesson(self, mode: str, context: LearnerContext) -> dict:
        """Gera a lição pelo prompt da biblioteca, com fallback de modelo OpenRouter."""
        template = get_mode_prompt(mode)
        if not template:
            raise ValueError(mode)
        if not self.openrouter_ready:
            return self._unavailable_or_dev_mock(
                lambda: MockAIProvider().generate_lesson(mode, context)
            )

        skill = MODE_SKILL.get(mode)
        prompt = template.render(
            context.to_prompt_context(skill), get_output_contract(mode)
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            content, model = openrouter_chat_with_fallback(
                self.s,
                messages,
                lambda p: isinstance(p, dict) and bool(p.get("title")),
            )
        except OpenRouterUnavailableError:
            return self._unavailable_or_dev_mock(
                lambda: MockAIProvider().generate_lesson(mode, context)
            )
        return _envelope(mode, context, content, "openrouter", model)


def get_ai_provider() -> BaseAIProvider:
    s = get_settings()
    if s.ai_mock_mode:
        logger.info("IA em MockAIProvider (AI_MOCK_MODE=true)")
        return MockAIProvider()
    return OpenRouterProvider()
