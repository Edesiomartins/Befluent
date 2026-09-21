import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LessonContent } from "@/components/lesson-modes";
import type { GrammarLesson } from "@/types/lesson";

const apiMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status = 400) {
      super(message);
      this.status = status;
    }
  },
}));

const lesson: GrammarLesson = {
  mode: "grammar",
  provider: "mock",
  language_code: "en",
  level: "A1",
  overall_level: "A1",
  skill: "vocabulary_grammar",
  skill_label: "Gramática",
  level_source: "placement_test",
  level_is_estimated: true,
  lesson_id: "les-grammar",
  title: "Perguntas simples",
  objective: "Fazer perguntas básicas.",
  explanation: "Monte perguntas curtas.",
  patterns: ["Pergunta de identidade"],
  examples: [{ sentence: "What is your name?", translation: "Qual é o seu nome?" }],
  exercises: [
    {
      prompt: "____ is your name?",
      options: ["What", "Where"],
      answer: "What",
      rationale: "What pergunta o nome.",
    },
    {
      prompt: "Where ____ you from?",
      options: ["are", "is"],
      answer: "are",
      rationale: "Are concorda com you.",
    },
  ],
};

describe("Gramática — sequência antes da compreensão", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("não conclui a lição depois da primeira atividade", async () => {
    const onPracticeReady = vi.fn();
    apiMock.mockImplementation((path: string) => {
      if (String(path).includes("objective-attempts")) return Promise.resolve({ attempts: [] });
      if (String(path).includes("objective-answers")) {
        return Promise.resolve({
          submitted: true,
          correct: true,
          selected_answer: "What",
          correct_answer: "What",
          feedback: { is_correct: true, selected: "What", correct_option: "What", why_correct: "Certo." },
          retry: { available: false },
        });
      }
      return Promise.resolve({});
    });

    render(<LessonContent mode="grammar" lesson={lesson} onPracticeReady={onPracticeReady} />);

    expect(await screen.findByText("Atividade 1 de 2")).toBeInTheDocument();
    await waitFor(() => expect(onPracticeReady).toHaveBeenCalledWith(false));

    fireEvent.click(screen.getByLabelText("What"));
    fireEvent.click(screen.getByRole("button", { name: /enviar resposta/i }));

    expect(await screen.findByRole("button", { name: "Próxima atividade" })).toBeInTheDocument();
    expect(apiMock).not.toHaveBeenCalledWith(
      "/api/v1/lessons/les-grammar/complete",
      expect.anything(),
    );
    expect(onPracticeReady).not.toHaveBeenCalledWith(true);
  });
});
