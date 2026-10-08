import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PlacementTestIntroPage from "@/app/(app)/placement-test/page";
import PlacementTestRunnerPage from "@/app/(app)/placement-test/[id]/page";
import PlacementResultPage from "@/app/(app)/placement-test/[id]/resultado/page";

const replace = vi.fn();
const push = vi.fn();
const apiMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push, refresh: vi.fn() }),
  useParams: () => ({ id: "test-1" }),
}));

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status = 400, code?: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

const progress = {
  answered: 3,
  minimum: 12,
  target: 20,
  maximum: 30,
  writing_submitted: false,
};

const objectiveItem = {
  id: "item-1",
  skill: "vocabulary_grammar",
  skill_label: "Vocabulário e gramática",
  item_type: "multiple_choice",
  prompt: "Qual é a saudação usada pela manhã?",
  instructions: null,
  passage: null,
  options: ["Good morning", "Good night", "Goodbye", "See you"],
  audio_url: null,
  audio_script: null,
};

function mockRoute(handler: (path: string, options?: { method?: string }) => unknown) {
  apiMock.mockImplementation((path: string, options?: { method?: string }) =>
    Promise.resolve(handler(path, options)),
  );
}

beforeEach(() => {
  replace.mockReset();
  push.mockReset();
  apiMock.mockReset();
});

it.each([17, 9, 23])("encerra com %i atividades sem prometer total", async count => {
  mockRoute(path => path.endsWith("next-item") ? { item: null, stage: "ready_to_complete",
    progress: { ...progress, answered: count, activities_completed: count, stop_reason: "objective_coverage_satisfied" } } : { language_code: "en" });
  render(<PlacementTestRunnerPage />);
  expect(await screen.findByText(`${count} atividades concluídas`)).toBeInTheDocument();
  expect(screen.queryByText(/de aproximadamente/)).not.toBeInTheDocument();
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Ver meu resultado" })).toBeInTheDocument();
});

it.each(["bank_exhausted", "bank_freshness_exhausted"])("explica encerramento parcial por %s", async reason => {
  mockRoute(path => path.endsWith("next-item") ? { item: null, stage: "ready_to_complete",
    progress: { ...progress, activities_completed: 17, stop_reason: reason } } : { language_code: "en" });
  render(<PlacementTestRunnerPage />);
  expect(await screen.findByRole("heading", {
    name: "A coleta foi encerrada porque não há mais atividades inéditas adequadas disponíveis. Você receberá um perfil parcial.",
  })).toBeInTheDocument();
  expect(screen.getByText("17 atividades concluídas")).toBeInTheDocument();
  expect(screen.queryByText(/de aproximadamente/)).not.toBeInTheDocument();
});

it("explica ready_to_complete quando as evidências previstas foram reunidas", async () => {
  mockRoute(path => path.endsWith("next-item") ? { item: null, stage: "ready_to_complete",
    progress: { ...progress, activities_completed: 17, stop_reason: "objective_coverage_satisfied" } } : { language_code: "en" });
  render(<PlacementTestRunnerPage />);
  expect(await screen.findByRole("heading", {
    name: "Coleta concluída. As evidências previstas foram reunidas.",
  })).toBeInTheDocument();
  expect(screen.getByText("17 atividades concluídas")).toBeInTheDocument();
  expect(screen.queryByText(/de aproximadamente/)).not.toBeInTheDocument();
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
});

it("explica maximum_reached sem prometer perfil além das evidências", async () => {
  mockRoute(path => path.endsWith("next-item") ? { item: null, stage: "ready_to_complete",
    progress: { ...progress, activities_completed: 17, stop_reason: "maximum_reached" } } : { language_code: "en" });
  render(<PlacementTestRunnerPage />);
  expect(await screen.findByRole("heading", {
    name: "A coleta atingiu o limite desta sessão. Vamos apresentar as evidências disponíveis.",
  })).toBeInTheDocument();
  expect(screen.queryByText(/perfil parcial se faltar cobertura/)).not.toBeInTheDocument();
});

it("coleta fala por áudio e oferece pular sem inventar nível", async () => {
  mockRoute((path) => path.endsWith("next-item") ? {
    stage: "speaking", progress,
    item: { ...objectiveItem, id: "speaking-1", skill: "speaking", skill_label: "Fala",
      item_type: "speaking_prompt", prompt: "Descreva uma experiência em inglês", options: [] },
  } : { language_code: "en" });
  render(<PlacementTestRunnerPage />);
  expect(await screen.findByRole("button", { name: "Gravar resposta" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Pular avaliação de fala" })).toBeInTheDocument();
  expect(screen.getByText(/pronúncia e fluência/)).toBeInTheDocument();
});

describe("Tela inicial do teste", () => {
  it("explica o teste e avisa que não é certificação", async () => {
    mockRoute(() => ({ test: null }));
    render(<PlacementTestIntroPage />);

    expect(screen.getByText("Descubra seu nível atual")).toBeInTheDocument();
    expect(screen.getByText(/nível estimado/)).toBeInTheDocument();
    expect(screen.getByText(/não uma certificação oficial/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar teste" })).toBeInTheDocument();
  });

  it("avisa sobre fones e possibilidade de retomar", async () => {
    mockRoute(() => ({ test: null }));
    render(<PlacementTestIntroPage />);

    expect(screen.getByText(/fones de ouvido/)).toBeInTheDocument();
    expect(screen.getByText(/sair e retomar/)).toBeInTheDocument();
  });

  it("inicia o teste e navega para a execução", async () => {
    mockRoute((path) => (path.includes("current") ? { test: null } : { id: "novo-teste" }));
    render(<PlacementTestIntroPage />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar teste" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/placement-test/novo-teste"));
  });

  it("oferece retomar teste em andamento", async () => {
    mockRoute(() => ({
      test: { id: "test-1", progress: { ...progress, answered: 5 } },
    }));
    render(<PlacementTestIntroPage />);

    expect(await screen.findByText("Você tem um teste em andamento")).toBeInTheDocument();
    expect(screen.getByText(/5 atividades concluídas/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Retomar teste" })).toHaveAttribute(
      "href",
      "/placement-test/test-1",
    );
  });

  it("mostra erro real quando não consegue iniciar", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockImplementation((path: string) =>
      path.includes("current")
        ? Promise.resolve({ test: null })
        : Promise.reject(new ApiError("Você poderá refazer o teste em 30 dias.", 409)),
    );
    render(<PlacementTestIntroPage />);

    fireEvent.click(screen.getByRole("button", { name: "Iniciar teste" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Você poderá refazer o teste em 30 dias.",
    );
    expect(push).not.toHaveBeenCalled();
  });
});

describe("Execução do teste", () => {
  it("mostra questão objetiva com progresso acessível", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: objectiveItem, stage: "objective", progress }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);

    expect(await screen.findByText(objectiveItem.prompt)).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(screen.getByText("3 atividades concluídas")).toBeInTheDocument();
    expect(screen.getByText("Vocabulário e gramática")).toBeInTheDocument();
  });

  it("não revela o nível da questão nem a resposta correta", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? {
            item: {
              ...objectiveItem,
              correct_answer: "Good morning",
              explanation: "A saudação da manhã é a primeira opção.",
            },
            stage: "objective",
            progress,
          }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);
    await screen.findByText(objectiveItem.prompt);

    expect(screen.queryByText(/A1|A2|B1|B2/)).not.toBeInTheDocument();
    expect(screen.queryByText(/correta/i)).not.toBeInTheDocument();
    expect(screen.queryByText("A saudação da manhã é a primeira opção.")).not.toBeInTheDocument();
    expect(screen.queryByText(/alternativa correta/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/revisão item/i)).not.toBeInTheDocument();
  });

  it("exige seleção antes de continuar", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: objectiveItem, stage: "objective", progress }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);
    await screen.findByText(objectiveItem.prompt);

    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    fireEvent.click(screen.getByRole("radio", { name: "Good morning" }));
    expect(screen.getByRole("button", { name: "Continuar" })).toBeEnabled();
  });

  it("envia a resposta com tempo de resposta", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: objectiveItem, stage: "objective", progress }
        : path.includes("/answers")
          ? { accepted: true, progress }
          : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);
    await screen.findByText(objectiveItem.prompt);

    fireEvent.click(screen.getByRole("radio", { name: "Good morning" }));
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/placement-tests/test-1/answers",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ item_id: "item-1", answer: "Good morning" }),
        }),
      ),
    );
  });

  it("mostra atividade de escuta com botão de áudio", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? {
            item: {
              ...objectiveItem,
              skill: "listening",
              skill_label: "Compreensão auditiva",
              audio_script: "I would like a coffee.",
            },
            stage: "objective",
            progress,
          }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);

    expect(await screen.findByRole("button", { name: "Ouvir áudio" })).toBeInTheDocument();
  });

  it("mostra a etapa de escrita com contador", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? {
            item: {
              ...objectiveItem,
              skill: "writing",
              skill_label: "Escrita",
              item_type: "short_writing",
              prompt: "Escreva de 3 a 5 frases se apresentando.",
              options: [],
            },
            stage: "writing",
            progress,
          }
        : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);

    const textarea = await screen.findByLabelText("Sua resposta");
    fireEvent.change(textarea, { target: { value: "My name is Ana." } });
    expect(screen.getByText("15 caracteres")).toBeInTheDocument();
  });

  it("conclui o teste e vai para o resultado", async () => {
    mockRoute((path) =>
      path.includes("next-item")
        ? { item: null, stage: "ready_to_complete", progress }
        : path.includes("/complete")
          ? { id: "test-1", status: "completed" }
          : { language_code: "en" },
    );

    render(<PlacementTestRunnerPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Ver meu resultado" }));

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/placement-test/test-1/resultado"),
    );
  });

  it("mostra erro recuperável quando a API falha", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockImplementation((path: string) =>
      path.includes("next-item")
        ? Promise.reject(new ApiError("Falha ao carregar atividade.", 500))
        : Promise.resolve({ language_code: "en" }),
    );

    render(<PlacementTestRunnerPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Falha ao carregar atividade.");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});

describe("Resultado", () => {
  const result = {
    id: "test-1",
    language_code: "en",
    status: "completed",
    completed_at: "2026-07-27T12:00:00+00:00",
    duration_seconds: 900,
    overall_level: "B1",
    overall: {
      code: "B1",
      name_pt: "B1 — Intermediário",
      short_description: "Mantém conversas sobre temas familiares.",
      order_index: 3,
      testable: true,
    },
    confidence_score: 68,
    confidence_label: "moderada",
    items_answered: 20,
    weights_used: { reading: 0.25 },
    recommendations: [
      { skill: "writing", reason: "below_overall", priority: 1 },
      { skill: "speaking", reason: "not_assessed", priority: 2 },
    ],
    skills: [
      { skill: "reading", label: "Leitura", estimated_level: "B2", level: null, score: 4, max_score: 4, status: "assessed" },
      { skill: "writing", label: "Escrita", estimated_level: "A2", level: null, score: 1, max_score: 4, status: "assessed" },
      { skill: "speaking", label: "Fala", estimated_level: null, level: null, score: 0, max_score: 0, status: "not_available" },
    ],
    speaking_available: false,
    disclaimer: "Nível estimado. Não é uma certificação oficial.",
  };

  it("exibe nível geral, confiança e ressalva", async () => {
    mockRoute(() => result);
    render(<PlacementResultPage />);

    expect(await screen.findByText("Seu nível estimado")).toBeInTheDocument();
    expect(screen.getByText("B1")).toBeInTheDocument();
    expect(screen.getByText(/moderada \(68\/100\)/)).toBeInTheDocument();
    expect(
      screen.getByText("Nível estimado. Não é uma certificação oficial."),
    ).toBeInTheDocument();
  });

  it("mostra calibração sem CEFR nem oferta de cronograma longo", async () => {
    mockRoute(() => ({
      ...result,
      diagnostic_status: "calibrating",
      overall_level: null,
      overall: null,
      confidence_score: null,
      confidence_label: null,
      curriculum: null,
      priority_focus: [
        { skill: "listening", reason: "insufficient_evidence", priority: 1, href: "/learn" },
      ],
      recommendations: [
        { skill: "listening", reason: "insufficient_evidence", priority: 1, href: "/learn" },
      ],
      skills: result.skills.map((skill) => ({ ...skill, estimated_level: null, status: "calibrating" })),
    }));
    render(<PlacementResultPage />);

    expect(await screen.findByText("Estamos calibrando suas habilidades")).toBeInTheDocument();
    expect(screen.queryByText("B1")).not.toBeInTheDocument();
    expect(screen.queryByText("Monte seu cronograma")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Praticar compreensão auditiva" })).toHaveAttribute(
      "href",
      "/learn",
    );
  });

  it("lista competências avaliadas e não avaliadas", async () => {
    mockRoute(() => result);
    render(<PlacementResultPage />);

    // Rótulos se repetem entre a lista de competências e o bloco de prioridades.
    expect(await screen.findAllByText("Leitura")).not.toHaveLength(0);
    expect(screen.getAllByText("Escrita")).not.toHaveLength(0);
    expect(screen.getAllByText("Fala")).not.toHaveLength(0);
    expect(screen.getByText("não avaliada")).toBeInTheDocument();
    expect(screen.getByText(/avaliação de fala ainda não está disponível/)).toBeInTheDocument();
  });

  it("mostra prioridades de estudo", async () => {
    mockRoute(() => result);
    render(<PlacementResultPage />);

    expect(await screen.findByText("Pontos fortes e prioridades")).toBeInTheDocument();
    expect(screen.getByText(/abaixo do nível geral/)).toBeInTheDocument();
  });

  it("oferece caminhos após o resultado", async () => {
    mockRoute(() => result);
    render(<PlacementResultPage />);

    expect(await screen.findByRole("link", { name: "Ir para o dashboard" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("link", { name: "Ver painel" })).toBeInTheDocument();
  });

  it("com competências empatadas não aponta forte e fraco iguais", async () => {
    mockRoute(() => ({
      ...result,
      skills: [
        { skill: "reading", label: "Leitura", estimated_level: "B2", level: null, score: 4, max_score: 4, status: "assessed" },
        { skill: "listening", label: "Compreensão auditiva", estimated_level: "B2", level: null, score: 4, max_score: 4, status: "assessed" },
      ],
      recommendations: [],
    }));
    render(<PlacementResultPage />);

    expect(
      await screen.findByText("Seu desempenho ficou equilibrado entre as competências avaliadas."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Ponto forte")).not.toBeInTheDocument();
  });

  const partialSkills = [
    {
      skill: "vocabulary_grammar",
      label: "Vocabulário e gramática",
      estimated_level: "PRE_A1",
      level: null,
      score: 5,
      max_score: 8,
      status: "estimated",
      evidence_counts: { answered: 8, valid: 8, excluded: 0, by_cefr: {} },
    },
    {
      skill: "reading",
      label: "Leitura",
      estimated_level: null,
      level: null,
      score: 4,
      max_score: 4,
      status: "insufficient_evidence",
      evidence_counts: { answered: 4, valid: 4, excluded: 0, by_cefr: {} },
    },
    {
      skill: "listening",
      label: "Compreensão auditiva",
      estimated_level: null,
      level: null,
      score: 4,
      max_score: 4,
      status: "insufficient_evidence",
      evidence_counts: { answered: 4, valid: 4, excluded: 0, by_cefr: {} },
    },
    {
      skill: "writing",
      label: "Escrita",
      estimated_level: "B1",
      level: null,
      score: 0.96,
      max_score: 1,
      status: "provisional",
      evidence_counts: { answered: 1, valid: 1, excluded: 0, by_cefr: {} },
      feedback: "A alternativa correta era um texto mais longo.",
      explanation: "Revisão item a item da escrita.",
    },
    {
      skill: "speaking",
      label: "Fala",
      estimated_level: "A1",
      level: null,
      score: 0.7,
      max_score: 1,
      status: "provisional",
      evidence_counts: { answered: 1, valid: 1, excluded: 0, by_cefr: {} },
    },
  ];

  const partialResult = {
    ...result,
    overall_level: null,
    overall: null,
    profile_status: "partial" as const,
    overall_estimate_status: "partial" as const,
    diagnostic_status: "calibrating" as const,
    confidence_score: null,
    confidence_label: null,
    speaking_available: true,
    curriculum: null,
    recommendations: [],
    priority_focus: [],
    skills: partialSkills,
  };

  const plan = {
    id: "plan-1",
    duration_days: 90,
    entry_level: "A1",
    target_level: "A2",
    generated_from: "planning",
    entry_level_source: "planning",
    day_href: "/cronograma/dia/day-1",
  };

  function assessmentPartial(extra: Record<string, unknown> = {}) {
    mockRoute((path) => {
      if (String(path).includes("language-profiles")) {
        return { planning_level: "B2", planning_level_source: "prior_global", language_code: "en" };
      }
      return { ...partialResult, ...extra };
    });
  }

  it("mostra perfil parcial com planning_level sem chamá-lo de nível global", async () => {
    assessmentPartial({
      planning_level: "A1",
      planning_level_source: "partial_evidence",
      planning_level_reason: "Entrada operacional A1 apoiada por pelo menos duas competências.",
      planning_level_trace: { signals: [] },
      curriculum: plan,
    });
    render(<PlacementResultPage />);

    expect(await screen.findByRole("heading", { name: "Perfil de competências" })).toBeInTheDocument();
    expect(
      screen.getByText("Ainda não há evidência suficiente para determinar um nível global com segurança."),
    ).toBeInTheDocument();
    expect(screen.getByText("Nível recomendado para iniciar sua jornada: A1")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Esse nível é usado apenas para iniciar seu plano de estudo e será ajustado conforme novas evidências forem coletadas.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Começar minha jornada em A1" })).toHaveAttribute(
      "href",
      "/cronograma/dia/day-1",
    );
    expect(apiMock.mock.calls.some(([path]) => String(path).includes("language-profiles"))).toBe(false);
    expect(screen.getByText("Pré-A1")).toBeInTheDocument();
    expect(screen.getByText("5 acertos em 8 questões")).toBeInTheDocument();
    expect(screen.getAllByText("Faixa ainda não determinada")).toHaveLength(2);
    expect(screen.getAllByText("4 acertos em 4 questões")).toHaveLength(2);
    expect(screen.getByText("B1 — provisório")).toBeInTheDocument();
    expect(screen.getByText("1 produção escrita avaliada")).toBeInTheDocument();
    expect(screen.getByText("A1 — provisório")).toBeInTheDocument();
    expect(screen.getByText("1 amostra de fala avaliada")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Seu nível estimado" })).not.toBeInTheDocument();
    expect(screen.queryByText(/seu nível é a1/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/não entraram no cálculo do nível geral/)).not.toBeInTheDocument();
    expect(screen.queryByText(/resposta\(s\) coletada/)).not.toBeInTheDocument();
    expect(screen.queryByText(/na tarefa/)).not.toBeInTheDocument();
    expect(screen.queryByText(/de aproximadamente/)).not.toBeInTheDocument();
    expect(screen.queryByText(/alternativa correta/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Revisão item a item/)).not.toBeInTheDocument();
    expect(screen.queryByText("Monte seu cronograma")).not.toBeInTheDocument();
  });

  it("parcial com planning_level e sem currículo não oferece CTA de jornada", async () => {
    assessmentPartial({
      planning_level: "A1",
      planning_level_source: "partial_evidence",
      planning_level_trace: { assessment_proposed_level: "A1" },
      curriculum: null,
    });
    render(<PlacementResultPage />);

    expect(await screen.findByText("Nível recomendado para iniciar sua jornada: A1")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Começar minha jornada/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para o dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(screen.queryByText(/Este teste propôs/)).not.toBeInTheDocument();
  });

  it("explica quando a proposta do assessment difere da entrada aplicada", async () => {
    assessmentPartial({
      planning_level: "B2",
      planning_level_source: "prior_global",
      planning_level_reason:
        "Mantida a entrada anterior apoiada por nível global vigente; este assessment não a substitui.",
      planning_level_trace: {
        action: "retained_prior_planning",
        retained_global_level: "B2",
        assessment_proposed_level: "A1",
      },
      curriculum: { ...plan, entry_level: "B2", day_href: "/cronograma/dia/day-2" },
    });
    render(<PlacementResultPage />);

    expect(await screen.findByText("Nível recomendado para iniciar sua jornada: B2")).toBeInTheDocument();
    expect(
      screen.getByText("Este teste propôs A1. A entrada aplicada é B2, porque o planejamento anterior foi mantido."),
    ).toBeInTheDocument();
    expect(screen.getByText(/este assessment não a substitui/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Começar minha jornada em B2" })).toHaveAttribute(
      "href",
      "/cronograma/dia/day-2",
    );
    expect(screen.queryByRole("link", { name: "Começar minha jornada em A1" })).not.toBeInTheDocument();
    expect(screen.queryByText(/seu nível é b2/i)).not.toBeInTheDocument();
  });

  it("usa o perfil linguístico só quando o resultado não traz planning_level", async () => {
    mockRoute((path) =>
      String(path).includes("language-profiles")
        ? {
            planning_level: "A1",
            planning_level_source: "partial_evidence",
            planning_level_reason: "Entrada vinda do perfil.",
            planning_level_trace: { assessment_proposed_level: "PRE_A1" },
            language_code: "en",
          }
        : { ...partialResult, curriculum: plan },
    );
    render(<PlacementResultPage />);

    expect(await screen.findByRole("link", { name: "Começar minha jornada em A1" })).toHaveAttribute(
      "href",
      "/cronograma/dia/day-1",
    );
    expect(
      screen.getByText("Este teste propôs Pré-A1. A entrada aplicada é A1, porque o planejamento anterior foi mantido."),
    ).toBeInTheDocument();
    expect(apiMock.mock.calls.some(([path]) => String(path).includes("language-profiles"))).toBe(true);
  });

  it("mostra perfil parcial sem planning_level e sem CTA de jornada", async () => {
    mockRoute((path) =>
      String(path).includes("language-profiles")
        ? { planning_level: null, language_code: "en" }
        : partialResult,
    );
    render(<PlacementResultPage />);

    expect(await screen.findByRole("heading", { name: "Perfil de competências" })).toBeInTheDocument();
    expect(screen.queryByText(/Nível recomendado para iniciar sua jornada/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Começar minha jornada/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para o dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(screen.queryByText(/seu nível é/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/não entraram no cálculo do nível geral/)).not.toBeInTheDocument();
  });

  it("leva a jornada existente quando o parcial já tem dia de estudo", async () => {
    assessmentPartial({
      planning_level: "A1",
      planning_level_source: "partial_evidence",
      curriculum: plan,
    });
    render(<PlacementResultPage />);

    expect(await screen.findByRole("link", { name: "Começar minha jornada em A1" })).toHaveAttribute(
      "href",
      "/cronograma/dia/day-1",
    );
    expect(screen.queryByText(/seu nível é a1/i)).not.toBeInTheDocument();
    expect(apiMock.mock.calls.some(([path]) => String(path).includes("language-profiles"))).toBe(false);
  });

  it("com overall suficiente mantém o nível global e o perfil por competência", async () => {
    mockRoute(() => ({
      ...result,
      profile_status: "complete",
      overall_estimate_status: "sufficient",
      planning_level: "B1",
      planning_level_source: "sufficient_overall",
      planning_level_reason: "Entrada baseada no nível global sustentado por cobertura suficiente.",
      planning_level_trace: { assessment_proposed_level: "A1" },
      curriculum: {
        id: "plan-global",
        duration_days: 90,
        entry_level: "B1",
        target_level: "B2",
        day_href: "/cronograma/dia/day-global",
      },
      skills: [
        {
          skill: "vocabulary_grammar",
          label: "Vocabulário e gramática",
          estimated_level: "B1",
          level: null,
          score: 6,
          max_score: 8,
          status: "estimated",
        },
        ...result.skills,
      ],
    }));
    render(<PlacementResultPage />);

    expect(await screen.findByRole("heading", { name: "Seu nível estimado" })).toBeInTheDocument();
    expect(screen.getAllByText("B1").length).toBeGreaterThan(0);
    expect(screen.getByText("6 acertos em 8 questões")).toBeInTheDocument();
    expect(screen.getByText("Vocabulário e gramática")).toBeInTheDocument();
    expect(screen.getAllByText("Leitura").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Perfil de competências" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Nível recomendado para iniciar sua jornada/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Começar minha jornada/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Este teste propôs/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continuar caminho" })).toHaveAttribute(
      "href",
      "/cronograma/dia/day-global",
    );
    expect(screen.queryByText(/resposta\(s\) coletada/)).not.toBeInTheDocument();
    expect(screen.queryByText(/na tarefa/)).not.toBeInTheDocument();
  });

  it("mostra erro quando o resultado não carrega", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(new ApiError("Este teste ainda não foi concluído.", 409));
    render(<PlacementResultPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Este teste ainda não foi concluído.",
    );
  });
});
