# Certificação PostgreSQL do placement v2 — 2bbf6b59c0cb0b5b

Data: 2026-10-09. Checkout testado: `ad05763`. Escopo: backend, sem alteração de aplicação, frontend, arquitetura ou migration.

## Resultado

**READY FOR DEPLOY.** Os quatro grupos PostgreSQL e a suíte backend integral passaram, sem falhas ou skips. `compileall` e `git diff --check` passaram. Gates 10 e 11 da estabilização anterior estão resolvidos; os demais gates já aprovados permanecem válidos. Nenhuma publicação foi realizada.

## Identidade e isolamento

- Servidor: **PostgreSQL 18.6**, `server_version_num=180006`, Linux musl/Alpine.
- Database e usuário confirmados por SQL: **befluent_test**.
- Único endpoint PostgreSQL utilizado: `127.0.0.1:55432`, túnel autorizado.
- URL validada antes dos testes: PostgreSQL, host/porta exatos, database `befluent_test`, sufixo `_test`.
- `POSTGRES_TEST_URL` definido somente no processo de teste; senha não registrada em `.env`, repositório, relatório ou log.
- `DATABASE_URL=sqlite://` nos processos de teste; nenhuma URL de produção usada.
- Fixture PostgreSQL cria schemas UUID próprios e os remove no teardown; não usa tabelas de produção.
- Evidência de identidade: [preflight.json](preflight.json).

## Quatro grupos PostgreSQL

| Grupo | Resultado |
|---|---|
| Parallel completion / stale status / downstream | PASS |
| Parallel session creation / delivery / exposure | PASS |
| Cross-schema cascade refusal | PASS |
| Fencing de soft pointers de outra conta no reset | PASS |

**4 passed, 0 skipped, 0 failed**, em 254,42s (4min14s), exit 0. Foram executados todos os arquivos encontrados com dependência de `POSTGRES_TEST_URL`/`postgres_reset_database`: `test_placement_completion_postgres.py`, `test_placement_exposure_postgres.py`, `test_reset_test_user_learning_postgres.py`.

Evidência: [postgres-tests.log](postgres-tests.log).

## Suíte integral e verificações

- Suíte backend integral, com `POSTGRES_TEST_URL`: **1.737 casos, 1.737 passed, 0 skipped, 0 failed**, 40 warnings, em 1546,56s (25min46s), exit 0. Os quatro testes PostgreSQL foram executados novamente dentro dela. Evidência: [full-suite.log](full-suite.log), [exit code](full-suite-exit.json).
- Execução integral: `pytest.main(['-o', 'addopts=', '-q', '-rs'])` no processo de verificação, com suporte psycopg Python descrito abaixo. Provedores mock; nenhuma credencial em arquivo.
- Os 40 warnings são de depreciação preexistente de `path_separator` na configuração Alembic; não houve falha classificada como flaky.
- `python -m compileall -q app tests`: **PASS**, exit 0.
- `git diff --check`: **PASS**, exit 0. Evidência das duas verificações: [final-checks.json](final-checks.json).
- Provedores: mock/controlados; certificação PostgreSQL não implica validação de provedor de IA/STT em produção.
- A suíte geral mantém seu isolamento SQLite; os quatro testes específicos usam PostgreSQL real. Não é uma conversão de toda a suíte para PostgreSQL.

## Ambiente e interrupção

O desligamento de 08/10 interrompeu a execução antes de salvar um resultado final dos quatro testes. A execução de 09/10 foi reiniciada; os logs agora são gravados durante os testes.

O Windows recusou a extensão binária de `psycopg` por Application Control. Foi utilizada a implementação Python do **mesmo psycopg 3.2.13**, com `libpq 18.3` já instalada e cujo carregamento foi permitido pelo Windows. O caminho dessa biblioteca foi selecionado somente no processo de verificação via resolução de `ctypes.util.find_library`. Nenhuma política de segurança foi alterada, nenhum arquivo foi desbloqueado, nenhum driver/dialeto do projeto foi trocado e nenhum arquivo de dependência foi modificado. A versão do cliente libpq é distinta da versão 18.6 do servidor confirmado por SQL.

## Achados e alterações

- P0/P1 novos: nenhum nos quatro testes PostgreSQL nem na suíte integral. Nenhuma correção de código foi necessária.
- Correções de aplicação nesta certificação: nenhuma.
- P2/P3 novos: nenhum. Backlog anterior de editorial/calibração, apoio nativo adicional e endurecimento de feedback histórico permanece fora desta rodada.
- Alterações desta rodada: somente relatório e evidências nesta pasta.
- Sem acesso a produção, commit, push ou deploy.

O status **NOT READY FOR DEPLOY** de `../placement-stabilization-2bbf6b59c0cb0b5b/report.md` é histórico e está substituído por esta certificação **READY FOR DEPLOY**, de 09/10/2026. Conclusão atualizada no Segundo Cérebro, ID 2bbf6b59c0cb0b5b. Não foram buscados novos refinamentos após os gates verdes.
