# Etapa 1 — checklist da execução local

Marca só o que esta rodada executou. Ambiente: SQLite local, mock, desktop `1280×800` e mobile `390×844`, mesma conta. Não é homologação.

## Desktop

| Item | Feito | Observação |
|---|---|---|
| Conversação por texto | sim | Turno `provider=mock`. Nasceram duas conversas; a tela usou `4292fb07-11cd-4288-bf6a-3cea9847ddb8`. |
| Conversação por voz (UI) | sim | Tela `/learn/voice` abriu. Captura `desktop-conversa-voz.png`. |
| STT | stub | `POST /speech/transcribe` 200, `provider=mock`. Transcrição não arquivada. Fala humana pendente. |
| TTS | stub | `POST /speech/synthesize` 200, `audio/wav`. Audição humana pendente. |
| Ciclo de vocabulário | sim | Lição `046d936d-e2fb-46b7-b3ef-482454a50b10`, fluxo `1b3f8ea4-551e-4b2c-8d83-104060a435b6`, 12 atividades. |
| Erro | sim | Terceiro envio mudou o trace para retry. |
| Retry | sim | `same_activity_retry` em `fr-b1-reading-opinion`. |
| Retomada | não se aplica | A sessão começou aqui. |
| Seleção | sim | 12 entregues, motivo `freshness_budget_modality_interaction`. |
| Exclusão | sim | 17 linhas: `family`, `cooldown`, `quality`, `budget`. |
| Esgotamento da sessão | não | `fallback_used` falso e sem `exhaustion` na abertura. |
| Esgotamento do pool de retry | sim | `pool_exhausted` / `no_candidates`, e a mesma atividade ficou. |
| Evidências | sim | `docs/stage-1-reference/evidence/`. |

## Mobile

| Item | Feito | Observação |
|---|---|---|
| Conversação por texto | sim, outra conversa | `b92ed7ae-2bde-4e48-8a91-31477ab77d27`. O GET da conversa do desktop respondeu 200. Não é a mesma conversa. |
| Conversação por voz | não | A tela de voz não foi reaberta no viewport mobile. |
| STT / TTS | não | Só no desktop, e só como stub. |
| Ciclo de vocabulário | sim, a mesma sessão | Viewport trocado na tela aberta. `GET /lessons/046d936d-e2fb-46b7-b3ef-482454a50b10/vocabulary-cycle` devolveu o fluxo `1b3f8ea4-…`. O hub não foi recarregado para não criar outra lição. |
| Erro | não repetido | O erro já estava na sessão. |
| Retry | estado preservado | O GET ainda traz `same_activity_retry` e `fr-b1-reading-opinion`. |
| Retomada | sim | `desktop_flow_id` = `mobile_flow_id`. |
| Seleção / exclusão | lidas de novo | O trace vigente na retomada é o do retry, não uma seleção nova. |
| Esgotamento | o do retry | `pool_exhausted` / `no_candidates` continua no payload. A abertura da sessão não esgotou. |
| Evidências | sim | `mobile-vocabulario-mesma-tela.png`, `mobile-vocabulario-retomada.png`, `mobile-conversa-texto.png`. |

## Limitações

- Áudio real: pendente.
- Homologação e produção (`d7fba8d` publicado): não verificadas aqui.
- `session.log` está coberto por `*.log` no `.gitignore`.
- `falha.png` não é o resultado final.
