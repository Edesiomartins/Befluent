import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import DashboardPage from "@/app/(app)/dashboard/page";
import DashboardStudyPage from "@/app/(app)/dashboard/estudo/page";
import DashboardPracticePage from "@/app/(app)/dashboard/pratica/page";
import { DashboardSkeleton } from "@/components/dashboard-skeleton";

const apiMock = vi.fn();

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

const dashboardWithPlan = {
  onboarding_completed: true,
  active_language: {
    code: "en",
    name_pt: "Inglês",
    native_name: "English",
    level_estimate: "iniciante",
    goal: "Conversar com confiança",
    minutes_per_day: 20,
    skills: ["Conversação"],
    onboarding_completed: true,
    user_language_id: "ul-1",
  },
  next_activity: {
    title: "Conversação",
    description: "Pratique conversação com foco no seu plano.",
    href: "/learn/conversation",
    cta: "Continuar",
    kind: "practice",
  },
  day_plan: {
    minutes_per_day: 20,
    goal: "Conversar com confiança",
    skills: ["Conversação"],
    items: [
      { label: "20 min de estudo", done: false },
      { label: "Conversar com confiança", done: true },
      { label: "Foco: Conversação", done: false },
    ],
  },
  progress: {
    vocabulary_items: 0,
    study_sessions: 0,
    reviews_due_count: 0,
    streak_days: 0,
  },
  reviews_due_count: 0,
  reviews_due: [],
  recent_activity: [],
};

describe("DashboardSkeleton", () => {
  it("informa o estado de carregamento", () => {
    render(<DashboardSkeleton />);
    expect(screen.getByRole("status", { name: "Carregando painel" })).toBeInTheDocument();
  });
});

describe("DashboardPage", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("mostra o idioma salvo do onboarding", async () => {
    apiMock.mockResolvedValue(dashboardWithPlan);

    render(<DashboardPage />);

    await waitFor(() => expect(apiMock).toHaveBeenCalledWith("/api/v1/dashboard"));
    expect(await screen.findByText("Inglês")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continuar a missão de hoje" })).toHaveAttribute(
      "href",
      "/learn/conversation",
    );
    expect(screen.getByText("Sequência")).toBeInTheDocument();
    expect(screen.getByText("Meta diária")).toBeInTheDocument();
    expect(screen.getByText("dias seguidos")).toBeInTheDocument();
    expect(screen.getByText("Sem revisões vencidas agora")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Idioma e plano" })).toHaveAttribute("href", "/dashboard/estudo");
    expect(screen.queryByText("Prática livre")).not.toBeInTheDocument();
    expect(screen.queryByText("Escolha um idioma para começar.")).not.toBeInTheDocument();
  });

  it("exibe quantidade e próximo item quando há revisões pendentes hoje", async () => {
    apiMock.mockResolvedValue({
      ...dashboardWithPlan,
      reviews_due_count: 2,
      reviews_due: [
        {
          id: "rev-1",
          item_type: "vocabulary",
          reference_id: "v-1",
          payload: { term: "se rendre compte" },
          next_review_at: "2026-10-25T10:00:00Z",
        },
      ],
    });

    render(<DashboardPage />);
    expect(await screen.findByText("2 revisões pendentes hoje")).toBeInTheDocument();
    expect(screen.getByText(/Próximo item:/)).toHaveTextContent("Próximo item: se rendre compte");
  });

  it("mostra plano e prática nas telas secundárias", async () => {
    apiMock.mockResolvedValue(dashboardWithPlan);
    const home = render(<DashboardStudyPage />);
    expect(await screen.findByText(/Objetivo: Conversar com confiança/)).toBeInTheDocument();
    expect(screen.getByText("Plano do dia")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Progresso do plano do dia" })).toHaveAttribute(
      "aria-valuenow",
      "33",
    );
    home.unmount();

    render(<DashboardPracticePage />);
    expect(await screen.findByText("Prática livre")).toBeInTheDocument();
    expect(screen.getByText("Atividade recente")).toBeInTheDocument();
  });

  it("mantém estado vazio apenas sem plano", async () => {
    apiMock.mockResolvedValue({
      onboarding_completed: false,
      active_language: null,
      next_activity: {
        title: "Configurar seu plano",
        description: "Defina idioma, nível e objetivo para começar.",
        href: "/onboarding",
        cta: "Começar onboarding",
        kind: "onboarding",
      },
      day_plan: {
        minutes_per_day: null,
        goal: null,
        skills: [],
        items: [{ label: "Concluir onboarding para montar o plano do dia", done: false }],
      },
      progress: {
        vocabulary_items: 0,
        study_sessions: 0,
        reviews_due_count: 0,
        streak_days: 0,
      },
      reviews_due_count: 0,
      reviews_due: [],
      recent_activity: [],
    });

    render(<DashboardPage />);
    expect(await screen.findByRole("heading", { name: "Bem-vindo ao BeFluent" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Começar onboarding" })).toHaveAttribute("href", "/onboarding");
    expect(screen.queryByText("Prática livre")).not.toBeInTheDocument();
  });

  it("guarda o vazio de plano e revisão nas telas secundárias", async () => {
    apiMock.mockResolvedValue({
      onboarding_completed: false,
      active_language: null,
      next_activity: {
        title: "Configurar seu plano",
        description: "Defina idioma, nível e objetivo para começar.",
        href: "/onboarding",
        cta: "Começar onboarding",
        kind: "onboarding",
      },
      day_plan: {
        minutes_per_day: null,
        goal: null,
        skills: [],
        items: [{ label: "Concluir onboarding para montar o plano do dia", done: false }],
      },
      progress: {
        vocabulary_items: 0,
        study_sessions: 0,
        reviews_due_count: 0,
        streak_days: 0,
      },
      reviews_due_count: 0,
      reviews_due: [],
      recent_activity: [],
    });

    const study = render(<DashboardStudyPage />);
    expect(await screen.findByText("Escolha um idioma para começar.")).toBeInTheDocument();
    expect(screen.getByText("Plano ainda não definido.")).toBeInTheDocument();
    study.unmount();
    render(<DashboardPracticePage />);
    expect(await screen.findByText("Nenhuma revisão pendente por enquanto.")).toBeInTheDocument();
  });

  it("mostra erro real quando a API falha", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(new ApiError("Sessão expirada.", 401, "unauthorized"));
    render(<DashboardPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Sessão expirada.");
  });

  it("permite tentar novamente sem perder o fluxo do painel", async () => {
    let dashboardCalls = 0;
    apiMock.mockImplementation((path: string) => {
      if (path !== "/api/v1/dashboard") return Promise.resolve({ day: null });
      dashboardCalls += 1;
      return dashboardCalls === 1
        ? Promise.reject(new Error("offline"))
        : Promise.resolve(dashboardWithPlan);
    });

    render(<DashboardPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));

    await waitFor(() => expect(dashboardCalls).toBe(2));
    expect(await screen.findByText("Inglês")).toBeInTheDocument();
  });
});

describe("DashboardPage — nível linguístico", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  const levelFromTest = {
    current_level: "B1",
    details: { code: "B1", name_pt: "B1 — Intermediário", short_description: "…", order_index: 3, testable: true },
    source: "placement_test",
    from_test: true,
    assessed_at: "2026-07-20T10:00:00+00:00",
    confidence_score: 72,
    confidence_label: "alta",
    placement_test_id: "test-1",
    skills: [
      { skill: "reading", label: "Leitura", estimated_level: "B2" },
      { skill: "listening", label: "Compreensão auditiva", estimated_level: "B1" },
      { skill: "speaking", label: "Fala", estimated_level: null },
    ],
    recommendations: [],
    needs_placement_test: false,
  };

  it("exibe nível vindo do teste com origem e confiança", async () => {
    apiMock.mockResolvedValue({
      ...dashboardWithPlan,
      active_language: { ...dashboardWithPlan.active_language, level: levelFromTest },
    });

    render(<DashboardStudyPage />);

    expect(await screen.findByText("Teste de nivelamento")).toBeInTheDocument();
    expect(screen.getByText("B1 — Intermediário")).toBeInTheDocument();
    expect(screen.getByText(/confiança alta/)).toBeInTheDocument();
    expect(screen.getByText("Ver resultado completo")).toBeInTheDocument();
  });

  it("mostra competências avaliadas e omite as não avaliadas", async () => {
    apiMock.mockResolvedValue({
      ...dashboardWithPlan,
      active_language: { ...dashboardWithPlan.active_language, level: levelFromTest },
    });

    render(<DashboardStudyPage />);

    expect(await screen.findByText("Leitura")).toBeInTheDocument();
    // "Fala" não foi avaliada e não deve aparecer na lista de competências.
    expect(screen.queryByText("Fala")).not.toBeInTheDocument();
    expect(screen.getByText("B2")).toBeInTheDocument();
  });

  it("sem nível definido convida ao teste em vez de inventar um nível", async () => {
    apiMock.mockResolvedValue({
      ...dashboardWithPlan,
      active_language: {
        ...dashboardWithPlan.active_language,
        level: {
          current_level: null,
          details: null,
          source: "pending",
          from_test: false,
          assessed_at: null,
          confidence_score: null,
          confidence_label: null,
          placement_test_id: null,
          skills: [],
          recommendations: [],
          needs_placement_test: true,
        },
      },
    });

    render(<DashboardStudyPage />);

    expect(await screen.findByText("Nível ainda não definido")).toBeInTheDocument();
    expect(screen.getByText("Fazer teste de nível")).toBeInTheDocument();
  });

  it("nível declarado oferece confirmação pelo teste", async () => {
    apiMock.mockResolvedValue({
      ...dashboardWithPlan,
      active_language: {
        ...dashboardWithPlan.active_language,
        level: {
          ...levelFromTest,
          source: "self_declared",
          from_test: false,
          placement_test_id: null,
          confidence_score: null,
          confidence_label: null,
        },
      },
    });

    render(<DashboardStudyPage />);

    expect(await screen.findByText("Nível informado")).toBeInTheDocument();
    expect(screen.getByText("Confirmar com o teste")).toBeInTheDocument();
    expect(screen.queryByText("Ver resultado completo")).not.toBeInTheDocument();
  });

  it("mostra a missão de hoje do idioma ativo", async () => {
    apiMock.mockImplementation((path: string) => {
      if (String(path).includes("/language-profiles")) {
        return Promise.resolve({
          profiles: [{ language_code: "fr", is_active: true, access_state: "available" }],
        });
      }
      if (String(path).includes("/curriculum/day/today")) {
        return Promise.resolve({
          curriculum: {
            id: "c1",
            duration_days: 90,
            start_date: "2026-09-01",
            entry_level: "B1",
            target_level: "B2",
            status: "active",
            generated_from: "test",
            weeks_total: 13,
            disclaimer: "",
            entry: { code: "B1", name_pt: "Intermediário", short_description: "", order_index: 3, testable: true },
            target: { code: "B2", name_pt: "Intermediário", short_description: "", order_index: 4, testable: true },
            progress: {
              days_total: 90,
              days_completed: 11,
              percent_complete: 12,
              current_day_number: 12,
              overdue_days: 0,
              needs_reschedule: false,
              next_checkpoint_week: null,
            },
          },
          week: {
            id: "w1",
            week_number: 2,
            theme: "Hotel",
            cefr_focus: "B1",
            is_checkpoint: false,
          },
          day: {
            id: "day-12",
            day_number: 12,
            scheduled_date: "2026-09-23",
            status: "in_progress",
            completed_at: null,
            total_minutes: 18,
            blocks_total: 2,
            blocks_completed: 1,
            blocks: [
              {
                id: "b1",
                skill: "vocabulary",
                skill_label: "Vocabulário",
                mode: "vocabulary",
                position: 1,
                estimated_minutes: 8,
                cefr_level: "B1",
                topic: "Fazer check-in em um hotel",
                lesson_ref: null,
                status: "completed",
                score: null,
                phase: "activate",
              },
              {
                id: "b2",
                skill: "listening",
                skill_label: "Listening",
                mode: "listening",
                position: 2,
                estimated_minutes: 10,
                cefr_level: "B1",
                topic: "Recepção",
                lesson_ref: null,
                status: "pending",
                score: null,
                phase: "input",
                is_current: true,
              },
            ],
            learning_objective: {
              id: "o1",
              code: "x",
              title: "Hotel",
              can_do: "check in",
              learner_goal: "Confirmar a reserva na recepção.",
              level: "B1",
              state: "practicing",
              status_label: "Em prática",
              reasons: [],
            },
          },
          overdue_days: [],
        });
      }
      return Promise.resolve({
        ...dashboardWithPlan,
        active_language: {
          ...dashboardWithPlan.active_language,
          code: "fr",
          name_pt: "Francês",
        },
      });
    });

    const view = render(<DashboardPage />);

    expect(await screen.findByRole("heading", { name: "Confirmar a reserva na recepção." })).toBeInTheDocument();
    expect(screen.getByText("Missão de hoje")).toBeInTheDocument();
    expect(screen.getAllByText(/Francês/).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Continuar a missão de hoje" })).toHaveAttribute(
      "href",
      "/cronograma/dia/day-12",
    );
    expect(screen.getByText("Sequência")).toBeInTheDocument();
    expect(screen.getByText("Meta diária")).toBeInTheDocument();
    expect(screen.getByText("Semana 2 · Hotel")).toBeInTheDocument();
    expect(screen.queryByText("Preparar")).not.toBeInTheDocument();
    view.unmount();

    render(<DashboardStudyPage />);
    expect(await screen.findByText("Preparar")).toBeInTheDocument();
    expect(screen.getByText("Compreender")).toBeInTheDocument();
  });

  it("a tela de hoje passa na checagem automática", async () => {
    apiMock.mockResolvedValue(dashboardWithPlan);
    const view = render(<DashboardPage />);
    expect(await screen.findByRole("link", { name: "Continuar a missão de hoje" })).toBeInTheDocument();
    expect(
      (await axe(view.container, { rules: { "color-contrast": { enabled: false } } })).violations,
    ).toEqual([]);
  });
});
