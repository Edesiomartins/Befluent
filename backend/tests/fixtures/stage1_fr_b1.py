"""Identidade da fatia local FR B1 / pt-BR usada na Etapa 1.

Não gera conteúdo e não altera a seleção. Serve para o teste provar que a
fatia curada continua declarando o par de idiomas e não uma versão inventada.
"""

EXPECTED_ACTIVITY_IDS = (
    "fr-b1-presentation-pourtant",
    "fr-b1-listen-train",
    "fr-b1-reading-opinion",
    "fr-b1-gap-utile",
    "fr-b1-order-disagree",
    "fr-b1-match-courtesy",
    "fr-b1-guided-train",
    "fr-b1-repeat-agree",
    "fr-b1-transfer-station",
    "fr-b1-dictation-agree",
)

REFERENCE = {
    "target_language": "fr",
    "native_language": "pt-BR",
    "cefr_level": "B1",
    "source": "curated_fr_b1_slice",
    "content_version_status": "unknown",
}
