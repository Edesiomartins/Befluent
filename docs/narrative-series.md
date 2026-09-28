# Série narrativa — "Bell & Sons" (inglês)

Relacionados: [learning-engine.md](learning-engine.md), [decisions.md](decisions.md) (D-025),
[design-system.md](design-system.md).

## Por que existe

O cronograma dava tema e sequência, mas nenhum motivo para voltar amanhã além
de disciplina. No produto de referência (Gymglish / Le Monde Langues) o que
sustenta o hábito é a história: elenco fixo, episódio curto, situação comum.

## Escopo

- **Só `en`.** `narrative_en.episode_for_language` devolve `None` para qualquer
  outro idioma. Não existe cena traduzida: seria conteúdo inglês com rótulo de
  outro idioma. Uma série em espanhol, francês, japonês, mandarim ou latim
  exigiria elenco, roteiro e revisão próprios — cada uma é uma decisão nova.
- **Curada em código**, em `backend/app/services/narrative_en.py`. Sem IA: a
  cena não é gerada na hora e é revisável por diff.
- **Determinística.** A cena sai do tema da semana + número do dia
  (`(day_number - 1) % episódios do tema`). Reabrir a jornada devolve a mesma
  cena; dias seguintes do mesmo tema avançam.
- **Ausência declarada.** Tema sem episódio não recebe cena genérica: o dia vem
  com `story: null` e a tela não renderiza nada.

## Elenco

| Personagem | Função |
|---|---|
| Nora | Gerente da livraria Bell & Sons, em Bristol. Direta, listas para tudo. |
| Theo | Barista do café da livraria. Escreve um romance que ninguém leu. |
| Priya | Jornalista freelancer. Trabalha nas mesas do fundo e ouve tudo. |
| Mr. Okafor | Dono do prédio. Fala pouco e cobra em dia. |

Tom: adulto, humor seco, situação real. Sem mascote e sem infantilização —
mesma regra do [design-system.md](design-system.md).

## Temas cobertos

Apresentações e rotina (3 episódios) · Família e pessoas próximas (2) · Comida e
restaurante (1) · Casa e moradia (1) · Direções e transporte (1) · Compras e
dinheiro (1).

O resto do currículo segue sem cena até alguém escrever os episódios.

## Como acrescentar um episódio

1. A chave de `_EPISODES` é o tema **exatamente** como o `curriculum_bank` o
   escreve. Se o tema mudar de nome lá, a cena desaparece em vez de casar com o
   tema errado — é proposital.
2. Toda fala precisa de `speaker` (do elenco), `text` e `translation_pt`. O
   teste `test_toda_fala_tem_traducao_e_personagem_do_elenco` recusa fala sem
   tradução ou com personagem fora do elenco.
3. `expressions` lista o que a cena planta e os blocos do dia reaproveitam.
4. Acrescentar episódio a um tema já coberto muda a rotação daquele tema — é o
   comportamento esperado (`test_dias_diferentes_do_mesmo_tema_avancam_a_cena`).

## Contrato na API

`GET /api/v1/curriculum/day/today` e `GET /api/v1/curriculum/day/{id}` devolvem,
dentro de `day`:

```json
"story": {
  "series": "Bell & Sons",
  "title": "First morning",
  "setting": "Segunda-feira, 7h40. …",
  "expressions": ["I'm", "Nice to meet you"],
  "lines": [{ "speaker": "Theo", "text": "…", "translation_pt": "…" }],
  "cast": [{ "name": "Theo", "role": "…" }],
  "episode_index": 1,
  "episodes_in_theme": 3
}
```

`null` onde não há série.

## Limites declarados

- A cena é leitura de apoio: **não** gera exercício, não conta como evidência e
  não entra no cálculo de domínio.
- Sem áudio próprio por personagem: o TTS tem uma voz por idioma
  ([TTS.md](TTS.md)), então a cena não é dublada por falante.
- Seis temas cobertos de cinquenta. A maior parte do currículo continua sem
  história.
