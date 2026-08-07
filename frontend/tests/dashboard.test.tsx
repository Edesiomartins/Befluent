import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPage from "@/app/(app)/dashboard/page";
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
    expect(screen.getByText(/Objetivo: Conversar com confiança/)).toBeInTheDocument();
    expect(screen.getByText("Próxima atividade")).toBeInTheDocument();
    expect(screen.getByText("Plano do dia")).toBeInTheDocument();
    expect(screen.getByText("Prática livre")).toBeInTheDocument();
    expect(screen.getByText("Atividade recente")).toBeInTheDocument();
    expect(screen.queryByText("Escolha um idioma para começar.")).not.toBeInTheDocument();
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
    expect(await screen.findByText("Escolha um idioma para começar.")).toBeInTheDocument();
    expect(screen.getByText("Nenhuma revisão pendente por enquanto.")).toBeInTheDocument();
    expect(screen.getByText("Plano ainda não definido.")).toBeInTheDocument();
  });

  it("mostra erro real quando a API falha", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(new ApiError("Sessão expirada.", 401, "unauthorized"));
    render(<DashboardPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Sessão expirada.");
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

    render(<DashboardPage />);

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

    render(<DashboardPage />);

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

    render(<DashboardPage />);

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

    render(<DashboardPage />);

    expect(await screen.findByText("Nível informado")).toBeInTheDocument();
    expect(screen.getByText("Confirmar com o teste")).toBeInTheDocument();
    expect(screen.queryByText("Ver resultado completo")).not.toBeInTheDocument();
  });
});
