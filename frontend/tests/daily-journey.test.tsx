import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CurriculumDayPage from "@/app/(app)/cronograma/dia/[id]/page";

const apiMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }),
  useParams: () => ({ id: "day-fr" }),
  usePathname: () => "/cronograma/dia/day-fr",
  notFound: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status = 400) {
      super(message);
      this.name = "ApiError";
      this.status = status;
    }
  },
}));

const week = {
  id: "w-1",
  week_number: 2,
  theme: "Se déplacer",
  cefr_focus: "B1",
  is_checkpoint: false,
};

const curriculum = {
  id: "cur-1",
  duration_days: 90,
  start_date: "2026-10-01",
  entry_level: "A2",
  target_level: "B1",
  status: "active",
  generated_from: "placement",
  weeks_total: 13,
  disclaimer: "",
  progress: {
    days_total: 90,
    days_completed: 1,
    percent_complete: 1,
    current_day_number: 2,
    overdue_days: 0,
    needs_reschedule: false,
  },
};

function day(extra: Record<string, unknown> = {}) {
  return {
    id: "day-fr",
    day_number: 2,
    scheduled_date: "2026-10-02",
    status: "in_progress",
    completed_at: null,
    total_minutes: 20,
    blocks_total: 2,
    blocks_completed: 1,
    blocks: [
      {
        id: "b-1",
        skill: "listening",
        skill_label: "Listening",
        mode: "listening",
        position: 1,
        estimated_minutes: 10,
        cefr_level: "B1",
        topic: "Gare",
        lesson_ref: null,
        status: "completed",
        score: null,
        phase: "input",
      },
    ],
    learning_objective: {
      id: "obj-1",
      code: "FR-B1",
      title: "Informação",
      can_do: "Pedir uma informação.",
      learner_goal: "Pedir uma informação na estação",
      level: "B1",
      state: "practicing",
      status_label: "Em prática",
      reasons: [],
    },
    ...extra,
  };
}

describe("jornada diária", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("mostra o objetivo do dia e o progresso", async () => {
    apiMock.mockImplementation((path: string) => {
      if (String(path).includes("/curriculum/day/")) {
        return Promise.resolve({ curriculum, week, day: day() });
      }
      return Promise.resolve({ profiles: [] });
    });
    render(<CurriculumDayPage />);
    expect(await screen.findByRole("heading", { name: "Pedir uma informação na estação" })).toBeInTheDocument();
    expect(screen.getByText("Objetivo:", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/Ao terminar, você será capaz de pedir uma informação na estação/)).toBeInTheDocument();
    expect(screen.getByText(/1 de 2 blocos/)).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Progresso da missão" })).toHaveAttribute(
      "aria-valuenow",
      "1",
    );
  });

  it("mostra o estado vazio quando o dia não tem blocos", async () => {
    apiMock.mockImplementation((path: string) => {
      if (String(path).includes("/curriculum/day/")) {
        return Promise.resolve({
          curriculum,
          week,
          day: day({
            blocks: [],
            blocks_total: 0,
            blocks_completed: 0,
            learning_objective: null,
          }),
        });
      }
      return Promise.resolve({ profiles: [] });
    });
    render(<CurriculumDayPage />);
    expect(await screen.findByText("Este dia ainda não tem atividades.")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar", { name: "Progresso da missão" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Missão concluída" })).not.toBeInTheDocument();
  });

  it("mostra erro recuperável quando o dia não carrega", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockImplementation((path: string) => {
      if (String(path).includes("/curriculum/day/")) {
        return Promise.reject(new ApiError("Não foi possível carregar este dia de estudo.", 500));
      }
      return Promise.resolve({ profiles: [] });
    });
    render(<CurriculumDayPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível carregar este dia de estudo.",
    );
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});
