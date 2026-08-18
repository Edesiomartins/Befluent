"""Catálogo de vozes do Kokoro-82M por idioma — fonte única de verdade para o
Kokoro Voice Lab (`app/api/tts_lab.py` + frontend `/admin/tts-lab`, seção
"Kokoro Voice Lab"). Não é usado pelo TTS de produção (`app/services/speech.py`).

Os voice IDs abaixo foram confirmados em `VOICES.md` do repositório oficial
do modelo (https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md,
consultado em 2026-08-18), não inventados. `name` é derivado do próprio ID
(parte após o prefixo `xx_`/`xy_`); `gender` vem da convenção documentada
pelo modelo (segunda letra do prefixo: `f`=female, `m`=male).

Nenhum desses IDs foi testado contra a OpenRouter real nesta implementação
(seriam ~50 chamadas pagas só para popular esta config) — a confirmação é
só da lista oficial do modelo. `hexgrad/kokoro-82m` já é o modelo validado
em produção (mesmo endpoint `/audio/speech`), então o contrato de geração
(model + voice + text) é o mesmo já usado por `speech.py` e pelo TTS Lab
genérico; só o *conjunto* de voice IDs testável aqui é novo.

Os idiomas `en-US`/`en-GB`/`es-ES`/`fr-FR`/`ja-JP`/`zh-CN` cobrem os
idiomas atuais do BeFluent (inglês diferenciado em US/UK, conforme pedido).
`it-IT`/`pt-BR`/`hi-IN` são idiomas extras que o Kokoro já suporta e ficam
disponíveis só para exploração no laboratório — não fazem parte do
currículo do produto.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KokoroVoice:
    id: str
    name: str
    gender: str  # "female" | "male"


@dataclass(frozen=True)
class KokoroLanguage:
    code: str
    name: str
    voices: tuple[KokoroVoice, ...]


def _voice(voice_id: str, gender: str) -> KokoroVoice:
    display_name = voice_id.split("_", 1)[1].replace("_", " ").title()
    return KokoroVoice(id=voice_id, name=display_name, gender=gender)


def _voices(gender: str, *voice_ids: str) -> tuple[KokoroVoice, ...]:
    return tuple(_voice(voice_id, gender) for voice_id in voice_ids)


KOKORO_LANGUAGES: tuple[KokoroLanguage, ...] = (
    KokoroLanguage(
        "en-US",
        "English — US",
        _voices(
            "female",
            "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
            "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
        )
        + _voices(
            "male",
            "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
            "am_michael", "am_onyx", "am_puck", "am_santa",
        ),
    ),
    KokoroLanguage(
        "en-GB",
        "English — UK",
        _voices("female", "bf_alice", "bf_emma", "bf_isabella", "bf_lily")
        + _voices("male", "bm_daniel", "bm_fable", "bm_george", "bm_lewis"),
    ),
    KokoroLanguage(
        "es-ES",
        "Spanish",
        _voices("female", "ef_dora") + _voices("male", "em_alex", "em_santa"),
    ),
    KokoroLanguage(
        "fr-FR",
        "French",
        _voices("female", "ff_siwis"),
    ),
    KokoroLanguage(
        "ja-JP",
        "Japanese",
        _voices("female", "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro")
        + _voices("male", "jm_kumo"),
    ),
    KokoroLanguage(
        "zh-CN",
        "Chinese",
        _voices("female", "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi")
        + _voices("male", "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang"),
    ),
    KokoroLanguage(
        "it-IT",
        "Italian",
        _voices("female", "if_sara") + _voices("male", "im_nicola"),
    ),
    KokoroLanguage(
        "pt-BR",
        "Portuguese — Brazil",
        _voices("female", "pf_dora") + _voices("male", "pm_alex", "pm_santa"),
    ),
    KokoroLanguage(
        "hi-IN",
        "Hindi",
        _voices("female", "hf_alpha", "hf_beta") + _voices("male", "hm_omega", "hm_psi"),
    ),
)

_LANGUAGE_BY_CODE: dict[str, KokoroLanguage] = {lang.code: lang for lang in KOKORO_LANGUAGES}
_VOICE_LANGUAGE_BY_ID: dict[str, str] = {
    voice.id: lang.code for lang in KOKORO_LANGUAGES for voice in lang.voices
}


def list_languages() -> list[dict]:
    return [
        {
            "code": lang.code,
            "name": lang.name,
            "voices": [{"id": v.id, "name": v.name, "gender": v.gender} for v in lang.voices],
        }
        for lang in KOKORO_LANGUAGES
    ]


def get_language(code: str) -> KokoroLanguage | None:
    return _LANGUAGE_BY_CODE.get(code)


def is_valid_voice_for_language(language_code: str, voice_id: str) -> bool:
    return _VOICE_LANGUAGE_BY_ID.get(voice_id) == language_code
