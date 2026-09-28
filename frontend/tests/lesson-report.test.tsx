import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LessonReportPage from "@/app/(app)/boletim/[lessonId]/page";

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

vi.mock("next/navigation", () => ({
  useParams: () => ({ lessonId: "lesson-1" }),
}));

function report(overrides: Record<string, unknown> = {}) {
  return {
    lesson: {
      id: "lesson-1",
      title: "Vocabulário de viagem",
      objective: "Usar palavras de viagem",
      status: "completed",
    },
    entries: [
      {
        id: "a1",
        activity_type: "multiple_choice",
        prompt: "Qual alternativa completa a frase?",
        student_response: "work",
        correct_answer: "hello",
        result: "incorrect",
        why_selected: "“work” não cumpre a função de saudação.",
        why_correct: "“hello” é a saudação neutra em inglês.",
        remember: "Saudação abre a conversa.",
        term: "hello",
        attempt_number: 1,
        answered_at: "2026-09-25T12:00:00+00:00",
      },
      {
        id: "a2",
        activity_type: "recognition",
        prompt: "Qual é a tradução de “goodbye”?",
        student_response: "tchau",
        correct_answer: "tchau",
        result: "correct",
        why_selected: "",
        why_correct: "",
        remember: "",
        term: "goodbye",
        attempt_number: 1,
        answered_at: "2026-09-25T12:01:00+00:00",
      },
    ],
    summary: { total: 2, incorrect: 1, correct: 1 },
    disclaimer:
      "O boletim mostra a correção como ela foi apresentada na hora da resposta.",
    ...overrides,
  };
}

describe("Boletim da lição", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("mostra o erro com a resposta certa e o porquê", async () => {
    apiMock.mockResolvedValue(report());

    render(<LessonReportPage />);

    expect(await screen.findByText("Vocabulário de viagem")).toBeInTheDocument();
    expect(screen.getByText("work")).toBeInTheDocument();
    expect(screen.getByText(/“hello” é a saudação neutra/)).toBeInTheDocument();
    expect(apiMock).toHaveBeenCalledWith("/api/v1/lessons/lesson-1/report");
  });

  it("declara que a correção é a do momento da resposta", async () => {
    apiMock.mockResolvedValue(report());

    render(<LessonReportPage />);

    expect(
      await screen.findByText(/como ela foi apresentada na hora da resposta/),
    ).toBeInTheDocument();
  });

  it("boletim vazio não inventa correção", async () => {
    apiMock.mockResolvedValue(
      report({ entries: [], summary: { total: 0, incorrect: 0, correct: 0 } }),
    );

    render(<LessonReportPage />);

    expect(await screen.findByText(/nenhuma resposta registrada/i)).toBeInTheDocument();
  });
});
