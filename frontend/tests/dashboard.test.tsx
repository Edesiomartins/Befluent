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
    expect(screen.getByText(/Nível: Iniciante/)).toBeInTheDocument();
    expect(screen.getByText(/Objetivo: Conversar com confiança/)).toBeInTheDocument();
    expect(screen.getByText("Onboarding concluído")).toBeInTheDocument();
    expect(screen.getByText("Próxima atividade")).toBeInTheDocument();
    expect(screen.getByText("Plano do dia")).toBeInTheDocument();
    expect(screen.getByText("Pratique agora")).toBeInTheDocument();
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
