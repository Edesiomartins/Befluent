import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProgressPage from "@/app/(app)/progress/page";

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

describe("ProgressPage", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("mostra dados reais da API e não estatísticas inventadas", async () => {
    apiMock.mockResolvedValue({
      vocabulary_items: 3,
      study_sessions: 2,
      streak_days: 1,
      total_minutes: 35,
      minutes_today: 12,
      total_minutes_label: "35min",
      daily_activity: {
        period_start: "2026-09-11",
        period_end: "2026-09-17",
        timezone: "America/Sao_Paulo",
        total_minutes: 35,
        days: [
          { date: "2026-09-11", minutes: 0 },
          { date: "2026-09-12", minutes: 8 },
          { date: "2026-09-13", minutes: null },
          { date: "2026-09-14", minutes: 15 },
          { date: "2026-09-15", minutes: 0 },
          { date: "2026-09-16", minutes: 12 },
          { date: "2026-09-17", minutes: 0 },
        ],
      },
      recent_activity: [
        {
          id: "s1",
          status: "completed",
          summary: "Sessão concluída.",
          started_at: new Date().toISOString(),
          ended_at: new Date().toISOString(),
          minutes: 12,
        },
      ],
      active_language: {
        code: "en",
        name_pt: "Inglês",
        native_name: "English",
        level_estimate: "iniciante",
        current_level: "A1",
        goal: "Conversar com confiança",
        skills: ["Conversação"],
      },
    });

    render(<ProgressPage />);
    await waitFor(() => expect(apiMock).toHaveBeenCalledWith("/api/v1/progress"));
    expect(await screen.findByText("35min")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Dias seguidos").nextElementSibling).toHaveTextContent("1");
    expect(screen.getByText("Conversar com confiança")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Minutos por dia" })).toBeInTheDocument();
    expect(screen.getByText("11 a 17 de setembro de 2026")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Minutos estudados por dia" })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /13 de setembro de 2026 Sem dado/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /11 de setembro de 2026 0 min/ })).toBeInTheDocument();
    expect(screen.getByText("35 min no período")).toBeInTheDocument();
    expect(screen.getByText("Ver dados")).toBeInTheDocument();
    expect(screen.queryByText("18h 42min")).not.toBeInTheDocument();
    expect(screen.queryByText("386")).not.toBeInTheDocument();
  });

  it("mostra estado vazio sem sessões", async () => {
    apiMock.mockResolvedValue({
      vocabulary_items: 0,
      study_sessions: 0,
      streak_days: 0,
      total_minutes: 0,
      minutes_today: 0,
      total_minutes_label: "0min",
      daily_activity: {
        period_start: "2026-09-11",
        period_end: "2026-09-17",
        timezone: "America/Sao_Paulo",
        total_minutes: 0,
        days: [],
      },
      recent_activity: [],
      active_language: null,
    });
    render(<ProgressPage />);
    expect(await screen.findByText("Nenhuma sessão registrada.")).toBeInTheDocument();
    expect(screen.getByText("Ainda não há dados diários neste período.")).toBeInTheDocument();
  });

  it("não transforma histórico diário ausente em sete dias zerados", async () => {
    apiMock.mockResolvedValue({
      vocabulary_items: 0,
      study_sessions: 0,
      streak_days: 0,
      total_minutes: 0,
      minutes_today: 0,
      total_minutes_label: "0min",
      recent_activity: [],
      active_language: null,
    });

    render(<ProgressPage />);

    expect(await screen.findByText("Histórico diário indisponível.")).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Minutos estudados por dia" })).not.toBeInTheDocument();
  });

  it("permite tentar novamente após uma falha", async () => {
    apiMock
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({
        vocabulary_items: 0,
        study_sessions: 0,
        streak_days: 0,
        total_minutes: 0,
        minutes_today: 0,
        total_minutes_label: "0min",
        recent_activity: [],
        active_language: null,
      });

    render(<ProgressPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Tentar novamente" }));

    await waitFor(() => expect(apiMock).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Nenhuma sessão registrada.")).toBeInTheDocument();
  });

  it("troca o período e atualiza a série sem inferir dados da atividade recente", async () => {
    const base = {
      vocabulary_items: 0,
      study_sessions: 2,
      streak_days: 0,
      total_minutes: 40,
      minutes_today: 0,
      total_minutes_label: "40min",
      recent_activity: [],
      active_language: { code: "en", name_pt: "Inglês", native_name: "English", level_estimate: null, current_level: null, goal: null, skills: [] },
    };
    apiMock.mockImplementation((path: string) => Promise.resolve({
      ...base,
      daily_activity: path.endsWith("days=30")
        ? { period_start: "2026-08-19", period_end: "2026-09-17", timezone: "America/Sao_Paulo", total_minutes: 40, days: [{ date: "2026-08-20", minutes: 25 }, { date: "2026-09-17", minutes: 15 }] }
        : { period_start: "2026-09-11", period_end: "2026-09-17", timezone: "America/Sao_Paulo", total_minutes: 15, days: [{ date: "2026-09-17", minutes: 15 }] },
    }));

    render(<ProgressPage />);
    expect(await screen.findByText("15 min no período")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "30 dias" }));

    expect(await screen.findByText("40 min no período")).toBeInTheDocument();
    expect(apiMock).toHaveBeenLastCalledWith("/api/v1/progress?days=30");
    expect(screen.getByRole("row", { name: /20 de agosto de 2026 25 min/ })).toBeInTheDocument();
  });
});
