"""Pronúncia clássica reconstruída — isolada do latim eclesiástico.

Convenção adotada (uma reconstrução pedagógica entre variantes acadêmicas):

- c = /k/ em todas as posições
- g = /g/ em todas as posições
- v consonantal ≈ /w/
- ae = /ae̯/ (ditongo)
- oe = /oe̯/
- i consonantal = /j/
- qu = /kʷ/
- ti + vogal: sem palatalização eclesiástica (/ti/, não /tsi/)
- s surda /s/
- r vibrante
- ph ≈ /pʰ/, th ≈ /tʰ/, ch ≈ /kʰ/ (aspiradas clássicas; aproximação pedagógica)

Não confundir com a pronúncia eclesiástica (italiana) do código `la`.
"""

from __future__ import annotations

CLASSICAL_PRONUNCIATION_CONVENTION = (
    "Pronúncia clássica reconstruída (convenção BeFluent): c e g sempre duros "
    "(/k/, /g/); v consonantal ≈ /w/; ae/oe como ditongos; ti sem palatalização "
    "eclesiástica; ph/th/ch aspirados. Diferente do latim eclesiástico (`la`)."
)

_EXAMPLES: dict[str, str] = {
    "caelum": "Na pronúncia clássica reconstruída: /ˈkae̯.lum/ (c=/k/, ae ditongo).",
    "caesar": "Na pronúncia clássica reconstruída: /ˈkae̯.sar/ (não 'Chésar' eclesiástico).",
    "cicero": "Na pronúncia clássica reconstruída: /ˈki.ke.ro/ (ambos os c = /k/).",
    "ecclesia": "Na pronúncia clássica reconstruída: /ekˈkle.si.a/ (c=/k/, sem /tʃ/).",
    "via": "Na pronúncia clássica reconstruída: /ˈwi.a/ (v ≈ /w/).",
    "vinum": "Na pronúncia clássica reconstruída: /ˈwi.num/ (v ≈ /w/).",
    "gratia": "Na pronúncia clássica reconstruída: /ˈgra.ti.a/ (ti sem /tsi/ eclesiástico).",
    "ratio": "Na pronúncia clássica reconstruída: /ˈra.ti.o/ (ti = /ti/, não /tsi/).",
    "regina": "Na pronúncia clássica reconstruída: /reˈgi.na/ (g=/g/, não /dʒ/).",
    "angelus": "Na pronúncia clássica reconstruída: /ˈan.ge.lus/ (g=/g/).",
    "sanctus": "Na pronúncia clássica reconstruída: /ˈsank.tus/ (c=/k/).",
    "credo": "Na pronúncia clássica reconstruída: /ˈkre.do/ (c=/k/).",
    "quattuor": "Na pronúncia clássica reconstruída: /ˈkʷat.tu.or/ (qu=/kʷ/).",
    "philosophia": "Na pronúncia clássica reconstruída: /pʰi.loˈso.pʰi.a/ (ph aspirado).",
}


def classical_example_guide() -> dict[str, str]:
    return dict(_EXAMPLES)


def describe_classical_rule(term: str) -> str:
    key = term.strip().casefold()
    if key in _EXAMPLES:
        return _EXAMPLES[key]
    return (
        f"Na pronúncia clássica reconstruída, «{term}» segue c/g duros, "
        "v≈/w/ e ditongos ae/oe — não a leitura eclesiástica."
    )
