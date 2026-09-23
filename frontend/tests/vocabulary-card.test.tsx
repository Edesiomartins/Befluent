import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LessonContent } from "@/components/lesson-modes";
import type { VocabularyLesson } from "@/types/lesson";

const apiMock = vi.fn();
const apiBlobMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  apiBlob: (...args: unknown[]) => apiBlobMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status = 503, code?: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

function lesson(
  item: VocabularyLesson["items"][number],
  languageCode = "de",
): VocabularyLesson {
  return {
    mode: "vocabulary",
    provider: "mock",
    language_code: languageCode,
    level: "A1",
    overall_level: "A1",
    skill: "vocabulary_grammar",
    skill_label: "Vocabulário",
    level_source: "placement_test",
    level_is_estimated: true,
    lesson_id: "les-vocab",
    title: "Vocabulário",
    objective: "Expressões do dia.",
    items: [item],
  };
}

const base = {
  translation: "poder / conseguir",
  example_translation: "Eu sei alemão.",
  usage_note: "Verbo modal.",
};

describe("card de vocabulário", () => {
  beforeEach(() => {
    apiMock.mockReset();
    apiMock.mockResolvedValue({ profiles: [] });
    apiBlobMock.mockReset();
    apiBlobMock.mockResolvedValue(new Blob(["wav"], { type: "audio/wav" }));
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        cancel: vi.fn(),
        speak: vi.fn(),
        getVoices: () => [],
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });
    Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
      configurable: true,
      value: class {
        text = "";
        lang = "";
        rate = 1;
        voice = null;
        onend: (() => void) | null = null;
        onerror: (() => void) | null = null;
        constructor(text: string) {
          this.text = text;
        }
      },
    });
  });

  it("toca a expressão e a frase em controles separados e mostra a forma declarada", async () => {
    render(
      <LessonContent
        mode="vocabulary"
        enableVocabularyCycle={false}
        lesson={lesson({
          ...base,
          term: "können",
          example: "Ich kann Deutsch.",
          example_form: "kann",
          form_note: "“kann” é uma forma de “können” usada com ich.",
        })}
      />,
    );

    expect(screen.getByRole("heading", { name: "können" })).toBeInTheDocument();
    expect(screen.getByText(/^kann$/)).toBeInTheDocument();
    expect(screen.getByText(/uma forma de “können”/)).toBeInTheDocument();
    expect(screen.getByText("“Ich kann Deutsch.”")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Ouvir expressão können" }));
    fireEvent.click(screen.getByRole("button", { name: "Ouvir frase de exemplo" }));

    await waitFor(() => expect(apiBlobMock).toHaveBeenCalledTimes(2));
    const texts = apiBlobMock.mock.calls.map(
      (call) => (call[1] as { body: { text: string } }).body.text,
    );
    expect(texts).toEqual(["können", "Ich kann Deutsch."]);
  });

  it("não mostra forma usada quando ela é igual à expressão", () => {
    render(
      <LessonContent
        mode="vocabulary"
        enableVocabularyCycle={false}
        lesson={lesson(
          {
            term: "water",
            translation: "água",
            example: "Can I have some water, please?",
            example_translation: "Pode me trazer água, por favor?",
            usage_note: "Incontável.",
            example_form: "water",
            form_note: "igual ao termo",
          },
          "en",
        )}
      />,
    );

    expect(screen.queryByText("Na frase")).not.toBeInTheDocument();
    expect(screen.queryByText("igual ao termo")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ouvir expressão water" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ouvir frase de exemplo" })).toBeInTheDocument();
  });

  it("item sem metadado de forma não inventa explicação", () => {
    render(
      <LessonContent
        mode="vocabulary"
        enableVocabularyCycle={false}
        lesson={lesson({
          ...base,
          term: "können",
          example: "Ich kann Deutsch.",
        })}
      />,
    );

    expect(screen.queryByText("Na frase")).not.toBeInTheDocument();
    expect(screen.queryByText(/^kann$/)).not.toBeInTheDocument();
    expect(screen.getByText("“Ich kann Deutsch.”")).toBeInTheDocument();
  });

  it("conteúdo antigo sem os campos novos continua no card", () => {
    const oldItem = {
      term: "thank you",
      translation: "obrigado",
      example: "Thank you for your help.",
      example_translation: "Obrigado pela sua ajuda.",
      usage_note: "Não muda com o gênero.",
    };
    render(
      <LessonContent
        mode="vocabulary"
        enableVocabularyCycle={false}
        lesson={lesson(oldItem, "en")}
      />,
    );

    expect(screen.getByRole("heading", { name: "thank you" })).toBeInTheDocument();
    expect(screen.getByText("“Thank you for your help.”")).toBeInTheDocument();
    expect(screen.queryByText("Na frase")).not.toBeInTheDocument();
  });

  it("falha de um áudio não desativa o outro", async () => {
    const { ApiError } = await import("@/lib/api");
    apiBlobMock.mockImplementation(async (_path: string, options: { body: { text: string } }) => {
      if (options.body.text === "können") {
        throw new ApiError("tts indisponível", 503, "tts_unavailable");
      }
      return new Blob(["wav"], { type: "audio/wav" });
    });

    render(
      <LessonContent
        mode="vocabulary"
        enableVocabularyCycle={false}
        lesson={lesson({
          ...base,
          term: "können",
          example: "Ich kann Deutsch.",
          example_form: "kann",
          form_note: "“kann” é uma forma de “können” usada com ich.",
        })}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Ouvir expressão können" }));
    await waitFor(() =>
      expect(apiBlobMock).toHaveBeenCalledWith(
        "/api/v1/speech/synthesize",
        expect.objectContaining({
          body: expect.objectContaining({ text: "können" }),
        }),
      ),
    );

    expect(screen.getByRole("button", { name: "Ouvir frase de exemplo" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Ouvir frase de exemplo" }));
    await waitFor(() =>
      expect(apiBlobMock).toHaveBeenCalledWith(
        "/api/v1/speech/synthesize",
        expect.objectContaining({
          body: expect.objectContaining({ text: "Ich kann Deutsch." }),
        }),
      ),
    );
    expect(screen.getByRole("heading", { name: "können" })).toBeInTheDocument();
  });

  it("espanhol com forma declarada no banco usa o mesmo card", () => {
    render(
      <LessonContent
        mode="vocabulary"
        enableVocabularyCycle={false}
        lesson={lesson(
          {
            term: "soler",
            translation: "costumar",
            example: "Suelo desayunar a las ocho.",
            example_translation: "Costumo tomar café da manhã às oito.",
            usage_note: "Verbo muito usado.",
            example_form: "suelo",
            form_note: "“suelo” é uma forma de “soler” usada com yo.",
          },
          "es-ES",
        )}
      />,
    );

    expect(screen.getByText(/^suelo$/)).toBeInTheDocument();
    expect(screen.getByText(/forma de “soler”/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ouvir expressão soler" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ouvir frase de exemplo" })).toBeInTheDocument();
  });
});
