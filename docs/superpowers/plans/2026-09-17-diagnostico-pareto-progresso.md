# Diagnóstico Pareto e Progresso por Domínio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Tornar o nivelamento confiável por habilidade e fazer a aba Progresso mostrar domínio demonstrado, em vez de premiar conclusão de atividades.

**Architecture:** O placement terá estado adaptativo e evidência por habilidade objetiva. O Teaching Engine continua como fonte de verdade; GET /api/v1/progress agrega seus estados e eventos em série temporal, renderizada com SVG acessível.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, pytest, Next.js/React, TypeScript, Vitest, Tailwind e SVG nativo.

**Spec:** docs/superpowers/specs/2026-09-17-diagnostico-pareto-progresso-design.md

## Global Constraints

- Não trocar stack, IA/STT, FSRS ou infraestrutura fluentia-*.
- Fala e escrita heurística são registradas, mas não definem CEFR ou domínio.
- CurriculumBlock concluído não aumenta domínio sem evidência.
- Manter campos atuais de GET /api/v1/progress.
- Não mostrar CEFR, percentual ou gráfico artificial durante calibração.
- Usar SVG acessível; não adicionar biblioteca de gráficos.

---

## File structure

- backend/app/services/placement_engine.py: adaptação, evidência e prioridades por habilidade.
- backend/app/api/placement_tests.py: fluxo de item, resultado, perfil e currículo.
- backend/app/services/progress.py: domínio agregado, timeline e caminho CEFR.
- backend/app/api/progress.py: bloco mastery retrocompatível.
- frontend/components/mastery-progress-chart.tsx: gráfico e tabela acessível.
- frontend/app/(app)/progress/page.tsx: domínio, CEFR, habilidades e prioridades.
- backend/tests/test_placement_engine.py, backend/tests/test_placement_api.py, backend/tests/test_progress_mastery.py, backend/tests/test_api.py e frontend/tests/progress.test.tsx: testes.

### Task 1: Adaptar placement por habilidade

**Files:**

- Modify: backend/app/services/placement_engine.py
- Test: backend/tests/test_placement_engine.py

**Interfaces:** Produzir SkillTestState, TestState.skill_states, state_for(state, skill), register_answer(state, record), next_skill(state) e estimate_skill_level(answers).

- [ ] **Step 1: Escrever testes que falham**

~~~python
def test_acerto_em_leitura_nao_promove_escuta():
    state = engine.TestState()
    for _ in range(3):
        engine.register_answer(state, record(Skill.READING, "A2", 1.0))
    assert state.skill_states[Skill.READING].current_band == "B1"
    assert state.skill_states[Skill.LISTENING].current_band == "A2"

def test_nao_estima_faixa_sem_quatro_itens_e_dois_na_faixa():
    answers = [record(Skill.READING, "A2", 1.0) for _ in range(3)]
    assert engine.estimate_skill_level(answers) is None
    answers.append(record(Skill.READING, "A1", 1.0))
    assert engine.estimate_skill_level(answers) is None
~~~

- [ ] **Step 2: Confirmar falha**

Run: pytest backend/tests/test_placement_engine.py -k "habilidade or faixa" -v

Expected: FAIL; o motor ainda usa faixa única e aceita poucos itens.

- [ ] **Step 3: Implementar estado por habilidade**

~~~python
@dataclass
class SkillTestState:
    current_band: str = CEFRLevel.A2
    consecutive_correct: int = 0
    consecutive_wrong: int = 0

@dataclass
class TestState:
    initial_band: str = CEFRLevel.A2
    answers: list[AnswerRecord] = field(default_factory=list)
    skill_states: dict[str, SkillTestState] = field(default_factory=dict)

def state_for(state: TestState, skill: str) -> SkillTestState:
    return state.skill_states.setdefault(skill, SkillTestState(state.initial_band))
~~~

Atualizar register_answer para alterar apenas state_for(state, record.skill). Atualizar next_skill para escolher a habilidade objetiva com menos respostas e priorizar as que ainda não atingiram quatro itens.

- [ ] **Step 4: Implementar evidência mínima**

~~~python
MIN_ITEMS_PER_SKILL = 4
MIN_ITEMS_AT_DECIDING_BAND = 2

def estimate_skill_level(answers: list[AnswerRecord]) -> str | None:
    if len(answers) < MIN_ITEMS_PER_SKILL:
        return None
    accuracy = _band_accuracy(answers)
    mastered = [level for level, (mean, count) in accuracy.items()
                if mean >= BAND_MASTERY_THRESHOLD and count >= MIN_ITEMS_AT_DECIDING_BAND]
    return max(mastered, key=LEVEL_INDEX.get) if mastered else None
~~~

Não inferir faixa abaixo quando a amostra é insuficiente; retornar None.

- [ ] **Step 5: Verificar e commitar**

Run: pytest backend/tests/test_placement_engine.py -v

Expected: PASS.

~~~bash
git add backend/app/services/placement_engine.py backend/tests/test_placement_engine.py
git commit -m "feat: separate placement adaptation by skill"
~~~

### Task 2: Tornar o resultado do placement seguro e acionável

**Files:**

- Modify: backend/app/api/placement_tests.py
- Modify: frontend/types/placement.ts
- Modify: frontend/app/(app)/placement-test/[id]/resultado/page.tsx
- Test: backend/tests/test_placement_api.py
- Test: frontend/tests/placement-test.test.tsx

**Interfaces:** Produzir diagnostic_status: ready ou calibrating, skills[].status incluindo calibrating, e no máximo três recomendações {skill, reason, priority, href}.

- [ ] **Step 1: Escrever testes que falham**

~~~python
def test_escrita_heuristica_nao_entra_no_nivel_geral(client, auth, db_session):
    body = _complete_with_heuristic_writing(client, auth, db_session)
    assert "writing" not in body["weights_used"]

def test_amostra_sem_evidencia_retorna_calibrating(client, auth, db_session):
    body = _complete_only_available_items(client, auth, db_session)
    assert body["diagnostic_status"] == "calibrating"
    assert body["overall_level"] is None
~~~

- [ ] **Step 2: Confirmar falha**

Run: pytest backend/tests/test_placement_api.py -k "heuristica or calibrating" -v

Expected: FAIL; escrita ainda pesa e o contrato não expõe calibração.

- [ ] **Step 3: Implementar resultado e prioridades**

Passar somente registros objetivos para engine.build_result. Persistir escrita como amostra com feedback preliminar. Limitar recomendações a três na ordem: habilidade sem evidência, habilidade abaixo do geral, menor acurácia. Incluir /learn como href quando não houver objetivo específico.

- [ ] **Step 4: Bloquear currículo longo sem evidência**

~~~python
profile.diagnostic_completed = result["diagnostic_status"] == "ready"
profile.current_level = result["overall_level"]
profile.recommendations_json = result["recommendations"]
if result["diagnostic_status"] == "ready":
    ensure_active_curriculum(db, profile.id, duration_days=90, generated_from=GeneratedFrom.PLACEMENT)
~~~

Em calibração, não gravar CEFR e não criar plano de 90 dias; a tela direciona às prioridades.

- [ ] **Step 5: Atualizar contrato e resultado frontend**

Adicionar diagnostic_status e calibrating aos tipos. Quando overall_level for nulo, renderizar “Estamos calibrando suas habilidades”, prioridades e nunca um código CEFR vazio.

- [ ] **Step 6: Verificar e commitar**

Run: pytest backend/tests/test_placement_api.py backend/tests/test_placement_engine.py -v

Run: npm test -- --run frontend/tests/placement-test.test.tsx

Expected: PASS.

~~~bash
git add backend/app/api/placement_tests.py backend/tests/test_placement_api.py frontend/types/placement.ts frontend/app/(app)/placement-test/[id]/resultado/page.tsx frontend/tests/placement-test.test.tsx
git commit -m "feat: make placement results evidence-based"
~~~

### Task 3: Agregar domínio e timeline no backend

**Files:**

- Modify: backend/app/services/progress.py
- Modify: backend/app/api/progress.py
- Create: backend/tests/test_progress_mastery.py
- Modify: backend/tests/test_api.py

**Interfaces:** Produzir mastery_percent_for_state(state, has_open_error) e aggregate_mastery_progress(db, user_language_id, days, tz); o endpoint retorna mastery sem remover campos existentes.

- [ ] **Step 1: Escrever testes que falham**

~~~python
def test_mastery_e_erro_aberto_tem_contribuicao_honesta():
    assert mastery_percent_for_state(MasteryState.MASTERED, has_open_error=False) == 100
    assert mastery_percent_for_state(MasteryState.NEEDS_REMEDIATION, has_open_error=True) == 35

def test_bloco_concluido_sem_objetivo_nao_gera_dominio(db_session):
    result = aggregate_mastery_progress(db_session, ul.id, days=7, tz=tz)
    assert result["status"] == "calibrating"
    assert result["overall_percent"] is None
~~~

- [ ] **Step 2: Confirmar falha**

Run: pytest backend/tests/test_progress_mastery.py -v

Expected: FAIL; agregação de domínio ainda não existe.

- [ ] **Step 3: Implementar contribuição e agregação por habilidade**

~~~python
MASTERY_PERCENT = {
    MasteryState.NOT_STARTED: 0, MasteryState.LEARNING: 25,
    MasteryState.PRACTICING: 50, MasteryState.NEEDS_REMEDIATION: 35,
    MasteryState.NEEDS_REVIEW: 35, MasteryState.RETRYING: 45,
    MasteryState.MASTERED: 100,
}

def mastery_percent_for_state(state: str, *, has_open_error: bool) -> int:
    return min(MASTERY_PERCENT.get(state, 0), 35) if has_open_error else MASTERY_PERCENT.get(state, 0)
~~~

Fazer join de UserObjectiveProgress com LearningObjective.skill_focus e erros abertos. Não usar sessões, minutos ou conclusão administrativa no domínio. Sem objetivo iniciado/evidência, devolver overall_percent None e status calibrating.

- [ ] **Step 4: Implementar série temporal e CEFR**

Para cada dia solicitado, calcular a série somente com eventos datados até aquele
dia: LearningAttempt correto/parcial/incorreto, LearningEvidence criada e
LearningError aberto/resolvido. Uma tentativa correta soma evidência; uma
incorreta ou erro aberto reduz a contribuição do objetivo; uma remediação
resolvida permite recuperação. Não projetar o estado atual de
UserObjectiveProgress para datas passadas, pois ele não guarda histórico. Sem
evento até a data, usar percent nulo, não zero.

~~~python
{"status": "ready", "overall_percent": 54, "by_skill": [...],
 "timeline": [{"date": "2026-09-17", "percent": 54}],
 "cefr": {"current": "A2", "next": "B1", "readiness_percent": 54},
 "priorities": [...]}
~~~

cefr é None sem nível; priorities usa recommendations_json, rótulo e link, limitado a três.

- [ ] **Step 5: Expor e verificar**

No endpoint, retornar mastery indisponível quando não houver idioma ativo. Manter todos os campos antigos.

Run: pytest backend/tests/test_progress_mastery.py backend/tests/test_progress_sessions.py backend/tests/test_api.py -k "progress" -v

Expected: PASS.

~~~bash
git add backend/app/services/progress.py backend/app/api/progress.py backend/tests/test_progress_mastery.py backend/tests/test_api.py
git commit -m "feat: expose mastery-based learning progress"
~~~

### Task 4: Renderizar domínio e caminho CEFR na aba Progresso

**Files:**

- Create: frontend/components/mastery-progress-chart.tsx
- Modify: frontend/app/(app)/progress/page.tsx
- Modify: frontend/tests/progress.test.tsx

**Interfaces:** Consumir mastery da Task 3; produzir MasteryProgressChart({ timeline }) com SVG e tabela aria-label="Domínio por dia".

- [ ] **Step 1: Escrever testes que falham**

~~~tsx
it("mostra domínio, caminho CEFR e tabela acessível", async () => {
  apiMock.mockResolvedValue({ ...base, mastery: readyMastery });
  render(<ProgressPage />);
  expect(await screen.findByText("Domínio demonstrado")).toBeInTheDocument();
  expect(screen.getByText("A2 → B1")).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Domínio por dia" })).toBeInTheDocument();
});

it("não mostra zero artificial durante calibração", async () => {
  apiMock.mockResolvedValue({ ...base, mastery: calibratingMastery });
  render(<ProgressPage />);
  expect(await screen.findByText(/dados em calibração/i)).toBeInTheDocument();
  expect(screen.queryByText("0%")).not.toBeInTheDocument();
});
~~~

- [ ] **Step 2: Confirmar falha**

Run: npm test -- --run frontend/tests/progress.test.tsx

Expected: FAIL; mastery ainda não é renderizado.

- [ ] **Step 3: Implementar gráfico acessível**

Criar mastery-progress-chart.tsx; renderizar polyline somente para pontos numéricos, title e desc no SVG e tabela expansível. Série vazia ou nula deve mostrar texto de calibração, sem linha em zero.

- [ ] **Step 4: Integrar os cartões à página**

Adicionar antes de “Ritmo de estudo” uma seção com domínio geral, A2 → B1, barras por habilidade e até três links de prioridade. Manter minutos, sessões e streak como métricas de hábito separadas. Os controles 7/30 dias atualizam as duas séries na mesma chamada.

- [ ] **Step 5: Verificar e commitar**

Run: npm test -- --run frontend/tests/progress.test.tsx

Expected: PASS para pronto, calibração, erro, 30 dias e acessibilidade.

~~~bash
git add frontend/components/mastery-progress-chart.tsx frontend/app/(app)/progress/page.tsx frontend/tests/progress.test.tsx
git commit -m "feat: show mastery progress and CEFR path"
~~~

### Task 5: Usar prioridades na semana de calibração

**Files:**

- Modify: backend/app/services/curriculum_generator.py
- Modify: backend/app/services/progression.py
- Modify: backend/tests/test_curriculum_generator.py
- Modify: backend/tests/test_curriculum_progression.py

**Interfaces:** day_block_skills(..., priority_skills=(), week_number=1) prioriza uma lacuna; checkpoint inicial é identificado por result_json["calibration_checkpoint"].

- [ ] **Step 1: Escrever testes que falham**

~~~python
def test_semana_um_prioriza_escuta_recomendada(db_session):
    profile.recommendations_json = [{"skill": "listening", "priority": 1}]
    curriculum = generate_curriculum(db_session, profile.id, 90)
    assert _skills_for_week(db_session, curriculum, 1).count(BlockSkill.LISTENING) > 1

def test_checkpoint_calibracao_nao_promove_cefr(db_session):
    outcome = apply_checkpoint_outcome(db_session, calibration_checkpoint)
    assert outcome["promoted"] is False
~~~

- [ ] **Step 2: Confirmar falha**

Run: pytest backend/tests/test_curriculum_generator.py backend/tests/test_curriculum_progression.py -k "calibracao" -v

Expected: FAIL; semana 1 ainda usa alternância padrão.

- [ ] **Step 3: Implementar prioridade limitada**

Na semana 1, substituir no máximo um bloco opcional por dia pela habilidade prioritária; nunca remover vocabulário, gramática ou revisão. Semanas seguintes e currículos existentes não mudam.

- [ ] **Step 4: Implementar checkpoint sem promoção**

Reutilizar create_checkpoint_test ao fim da semana 1 e marcar calibration_checkpoint. Em apply_checkpoint_outcome, atualizar apenas recomendações e níveis sustentados; retornar promoted False e não reescrever semanas futuras.

- [ ] **Step 5: Verificar e commitar**

Run: pytest backend/tests/test_curriculum_generator.py backend/tests/test_curriculum_progression.py backend/tests/test_placement_api.py -v

Expected: PASS.

~~~bash
git add backend/app/services/curriculum_generator.py backend/app/services/progression.py backend/tests/test_curriculum_generator.py backend/tests/test_curriculum_progression.py
git commit -m "feat: prioritize calibration week from placement gaps"
~~~

### Task 6: Documentar e verificar integração

**Files:**

- Modify: docs/assessment-system.md
- Modify: docs/api-specification.md

- [ ] **Step 1: Documentar contrato e limites**

Registrar a regra de quatro itens/dois na faixa, escrita/fala fora do CEFR e o bloco opcional mastery de GET /api/v1/progress.

- [ ] **Step 2: Executar backend completo**

Run: pytest backend/tests -q

Expected: PASS.

- [ ] **Step 3: Executar frontend completo**

Run: npm test -- --run

Expected: PASS.

- [ ] **Step 4: Build sem deploy**

Run: npm run lint && npm run build

Expected: exit 0; não publicar no Coolify.

- [ ] **Step 5: Revisar e commitar**

Run: git diff --check HEAD~5..HEAD && git status --short

Expected: sem whitespace inválido e árvore limpa antes do commit de documentação.

~~~bash
git add docs/assessment-system.md docs/api-specification.md
git commit -m "docs: document evidence-based placement and progress"
~~~

## Acceptance checks

- Acerto em leitura não promove escuta.
- Menos de quatro itens, ou menos de dois na faixa decisiva, não produz CEFR.
- Escrita heurística não muda overall_level ou weights_used.
- Calibração não exibe 0%, CEFR inventado ou plano longo automático.
- Erro aberto não eleva domínio; bloco concluído sem evidência não entra na curva.
- A aba mostra gráfico, habilidades, caminho CEFR e até três prioridades.
- Não há deploy sem confirmação explícita do usuário.
