import { render, screen, waitFor } from "@testing-library/react";
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
    expect(screen.getByText(/1 dia\(s\) seguidos/)).toBeInTheDocument();
    expect(screen.getByText("Conversar com confiança")).toBeInTheDocument();
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
      recent_activity: [],
      active_language: null,
    });
    render(<ProgressPage />);
    expect(await screen.findByText("Nenhuma sessão registrada.")).toBeInTheDocument();
  });
});
