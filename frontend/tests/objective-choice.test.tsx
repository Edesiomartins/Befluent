import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ObjectiveChoice } from "@/components/objective-choice";

const apiMock = vi.fn();

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status: number, code?: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  }
  return {
    api: (...args: unknown[]) => apiMock(...args),
    ApiError,
  };
});

describe("ObjectiveChoice — tentativa única (backend)", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("permite trocar seleção antes do envio", async () => {
    apiMock.mockResolvedValueOnce({ attempts: [] });
    render(
      <ObjectiveChoice
        lessonId="lesson-1"
        surface="grammar"
        kind="exercise"
        question={{
          prompt: "____ is your name?",
          options: ["What", "Where", "Who"],
          answer: "What",
          rationale: "'What' pergunta pela informação.",
          option_rationales: {
            Where: "'Where' pergunta por lugar.",
          },
        }}
      />,
    );

    await waitFor(() => expect(apiMock).toHaveBeenCalled());
    fireEvent.click(screen.getByLabelText("Where"));
    fireEvent.click(screen.getByLabelText("Who"));
    expect(screen.getByLabelText("Who")).toBeChecked();
    expect(screen.getByRole("button", { name: /enviar resposta/i })).toBeEnabled();
  });

  it("bloqueia troca após envio e mostra feedback do servidor", async () => {
    const onEvaluated = vi.fn();
    apiMock
      .mockResolvedValueOnce({ attempts: [] })
      .mockResolvedValueOnce({
        attempt_id: "a1",
        activity_key: "grammar:exercise:0",
        attempt_number: 1,
        submitted: true,
        correct: false,
        selected_answer: "Where",
        correct_answer: "What",
        feedback: {
          is_correct: false,
          selected: "Where",
          correct_option: "What",
          why_selected: "'Where' pergunta por lugar, não por nome.",
          why_correct: "'What' pergunta pela informação pedida (o nome).",
        },
        retry: { available: false, strategy: "fallback_continue" },
      });

    render(
      <ObjectiveChoice
        lessonId="lesson-2"
        surface="grammar"
        kind="exercise"
        question={{
          prompt: "____ is your name?",
          options: ["What", "Where", "Who"],
          answer: "What",
        }}
        onEvaluated={onEvaluated}
      />,
    );

    await waitFor(() => expect(apiMock).toHaveBeenCalled());
    fireEvent.click(screen.getByLabelText("Where"));
    fireEvent.click(screen.getByRole("button", { name: /enviar resposta/i }));

    await waitFor(() => {
      expect(screen.getByText(/resposta incorreta/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/where' pergunta por lugar/i)).toBeInTheDocument();
    expect(screen.getByText(/^Resposta correta:/i)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Where/i })).toBeDisabled();
    expect(screen.getByRole("radio", { name: /What/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /resposta enviada/i })).toBeDisabled();

    fireEvent.click(screen.getByRole("radio", { name: /What/i }));
    expect(screen.getByRole("radio", { name: /Where/i })).toBeChecked();
    expect(onEvaluated).toHaveBeenCalledTimes(1);
    expect(apiMock).toHaveBeenCalledWith(
      "/api/v1/lessons/lesson-2/objective-answers",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          activity_key: "grammar:exercise:0",
          selected_answer: "Where",
          request_retry: false,
        }),
      }),
    );
  });

  it("restaura bloqueio do backend após remount (refresh)", async () => {
    apiMock.mockResolvedValue({
      attempts: [
        {
          attempt_id: "a1",
          activity_key: "grammar:exercise:0",
          attempt_number: 1,
          submitted: true,
          correct: true,
          selected_answer: "What",
          correct_answer: "What",
          feedback: {
            is_correct: true,
            selected: "What",
            correct_option: "What",
            why_correct: "Correto.",
          },
          retry: { available: false },
        },
      ],
    });

    const question = {
      prompt: "____ is your name?",
      options: ["What", "Where", "Who"],
      answer: "What",
      rationale: "Correto.",
    };
    render(
      <ObjectiveChoice
        lessonId="lesson-3"
        surface="grammar"
        kind="exercise"
        question={question}
      />,
    );

    await waitFor(() => {
      expect(screen.getByRole("radio", { name: /What/i })).toBeDisabled();
    });
    expect(screen.getByRole("status")).toHaveTextContent(/correto/i);
  });

  it("trata 409 restaurando a tentativa sem desbloquear", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock
      .mockResolvedValueOnce({ attempts: [] })
      .mockRejectedValueOnce(new ApiError("already", 409, "attempt_already_submitted"))
      .mockResolvedValueOnce({
        attempts: [
          {
            attempt_id: "a1",
            activity_key: "grammar:exercise:0",
            attempt_number: 1,
            submitted: true,
            correct: false,
            selected_answer: "Who",
            correct_answer: "What",
            feedback: {
              is_correct: false,
              selected: "Who",
              correct_option: "What",
              why_correct: "Use What.",
            },
          },
        ],
      });

    render(
      <ObjectiveChoice
        lessonId="lesson-4"
        surface="grammar"
        kind="exercise"
        question={{
          prompt: "____ is your name?",
          options: ["What", "Where", "Who"],
          answer: "What",
        }}
      />,
    );

    await waitFor(() => expect(apiMock).toHaveBeenCalled());
    fireEvent.click(screen.getByLabelText("Who"));
    fireEvent.click(screen.getByRole("button", { name: /enviar resposta/i }));

    await waitFor(() => {
      expect(screen.getByRole("radio", { name: /Who/i })).toBeDisabled();
    });
    expect(screen.getByRole("radio", { name: /Who/i })).toBeChecked();
    expect(screen.getByText(/resposta incorreta/i)).toBeInTheDocument();
  });

  it("ao clicar Nova tentativa, troca a questão pela variante do backend", async () => {
    apiMock
      .mockResolvedValueOnce({ attempts: [] })
      .mockResolvedValueOnce({
        attempt_id: "a1",
        activity_key: "reading:question:0",
        attempt_number: 1,
        submitted: true,
        correct: false,
        selected_answer: "Porque é mais caro",
        correct_answer: "Porque evita engarrafamentos",
        feedback: {
          is_correct: false,
          selected: "Porque é mais caro",
          correct_option: "Porque evita engarrafamentos",
          why_correct: "O texto liga velocidade à ausência de engarrafamentos.",
        },
        retry: {
          available: true,
          strategy: "lesson_sibling",
          activity: {
            prompt: "Qual vantagem o texto destaca para o ciclista na cidade?",
            options: ["Contornar o trânsito", "Gastar mais combustível", "Ser obrigatório"],
            is_retry_variant: true,
          },
        },
      });

    render(
      <ObjectiveChoice
        lessonId="lesson-retry-1"
        surface="reading"
        kind="question"
        question={{
          prompt: "Segundo o texto, por que a bicicleta pode ser mais rápida na cidade?",
          options: [
            "Porque evita engarrafamentos",
            "Porque é mais caro",
            "Porque consome mais gasolina",
          ],
          answer: "Porque evita engarrafamentos",
        }}
      />,
    );

    await waitFor(() => expect(apiMock).toHaveBeenCalled());
    fireEvent.click(screen.getByLabelText("Porque é mais caro"));
    fireEvent.click(screen.getByRole("button", { name: /enviar resposta/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /nova tentativa/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /nova tentativa/i }));

    expect(
      screen.getByText("Qual vantagem o texto destaca para o ciclista na cidade?"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "Segundo o texto, por que a bicicleta pode ser mais rápida na cidade?",
      ),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Contornar o trânsito")).toBeEnabled();
    expect(screen.queryByRole("button", { name: /nova tentativa/i })).not.toBeInTheDocument();
  });

  it("não mostra Nova tentativa quando retry.available=false", async () => {
    apiMock
      .mockResolvedValueOnce({ attempts: [] })
      .mockResolvedValueOnce({
        attempt_id: "a1",
        activity_key: "reading:question:0",
        attempt_number: 1,
        submitted: true,
        correct: false,
        selected_answer: "B",
        correct_answer: "A",
        feedback: {
          is_correct: false,
          selected: "B",
          correct_option: "A",
          why_correct: "A é a forma adequada.",
        },
        retry: {
          available: false,
          strategy: "fallback_continue",
          message:
            "Continue o percurso; este ponto ficará marcado para revisão futura.",
        },
      });

    render(
      <ObjectiveChoice
        lessonId="lesson-retry-2"
        surface="reading"
        kind="question"
        question={{
          prompt: "Pergunta única",
          options: ["A", "B"],
          answer: "A",
        }}
      />,
    );

    await waitFor(() => expect(apiMock).toHaveBeenCalled());
    fireEvent.click(screen.getByLabelText("B"));
    fireEvent.click(screen.getByRole("button", { name: /enviar resposta/i }));

    await waitFor(() => {
      expect(screen.getByText(/resposta incorreta/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /nova tentativa/i })).not.toBeInTheDocument();
    expect(
      screen.getByText(/continue o percurso; este ponto ficará marcado/i),
    ).toBeInTheDocument();
  });

  it("restore mantém a última tentativa sem ressuscitar questão já usada", async () => {
    apiMock.mockResolvedValue({
      attempts: [
        {
          attempt_id: "a2",
          activity_key: "reading:question:0",
          attempt_number: 2,
          submitted: true,
          correct: false,
          selected_answer: "Opção errada B",
          correct_answer: "Resposta B",
          feedback: {
            is_correct: false,
            selected: "Opção errada B",
            correct_option: "Resposta B",
            why_correct: "Explicação B.",
          },
          question_snapshot: {
            prompt: "Variante B já apresentada",
            options: ["Resposta B", "Opção errada B"],
          },
          retry: {
            available: false,
            strategy: "fallback_continue",
            message: "Continue o percurso; este ponto ficará marcado para revisão futura.",
          },
        },
        {
          attempt_id: "a1",
          activity_key: "reading:question:0",
          attempt_number: 1,
          submitted: true,
          correct: false,
          selected_answer: "Opção errada A",
          correct_answer: "Resposta A",
          feedback: {
            is_correct: false,
            selected: "Opção errada A",
            correct_option: "Resposta A",
            why_correct: "Explicação A.",
          },
          question_snapshot: {
            prompt: "Questão A original",
            options: ["Resposta A", "Opção errada A"],
          },
        },
      ],
    });

    render(
      <ObjectiveChoice
        lessonId="lesson-retry-3"
        surface="reading"
        kind="question"
        question={{
          prompt: "Questão A original",
          options: ["Resposta A", "Opção errada A"],
          answer: "Resposta A",
        }}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/resposta incorreta/i)).toBeInTheDocument();
    });
    // Restaura a tentativa mais recente (nº 2), não a questão A.
    expect(screen.getByText("Variante B já apresentada")).toBeInTheDocument();
    expect(screen.queryByText("Questão A original")).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Opção errada B/i })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Opção errada B/i })).toBeDisabled();
    expect(screen.queryByRole("button", { name: /nova tentativa/i })).not.toBeInTheDocument();
  });
});
