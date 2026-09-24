import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LessonContent } from "@/components/lesson-modes";
import { TeachingActivityBody } from "@/components/teaching-activity";
import type { VocabularyLesson } from "@/types/lesson";
import type { SliceSession, TeachingActivity } from "@/types/teaching";

const apiMock = vi.fn();
const apiBlobMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  apiBlob: (...args: unknown[]) => apiBlobMock(...args),
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

vi.mock("@/hooks/use-active-language", () => ({
  useActiveLanguage: () => ({ code: "de", resolved: true }),
}));

function vocabularyLesson(): VocabularyLesson {
  return {
    mode: "vocabulary",
    provider: "mock",
    language_code: "de",
    level: "A1",
    overall_level: "A1",
    skill: "vocabulary_grammar",
    skill_label: "Vocabulário",
    level_source: "placement_test",
    level_is_estimated: true,
    lesson_id: "lesson-1",
    title: "Vocabulário",
    objective: "Praticar palavras.",
    items: [
      {
        term: "können",
        translation: "poder / conseguir",
        example: "Ich kann Deutsch.",
        example_translation: "Eu sei alemão.",
        usage_note: "Verbo modal.",
      },
    ],
  };
}

function session(activity: TeachingActivity | null, cursor = 0): SliceSession {
  return {
    status: "active",
    flow: {
      id: "flow-1",
      phase: "practicing",
      phase_label_pt: "Você está praticando",
      status: "active",
      activity_cursor: cursor,
      remediation_cycles: 0,
    },
    objective: { id: "", code: null, title: null, can_do: null, level: null },
    progress_state: "learning",
    current_activity: activity,
    activities_total: 5,
  };
}

describe("atividade lexical compartilhada", () => {
  beforeEach(() => {
    apiMock.mockReset();
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
        lang = "";
        rate = 1;
        voice = null;
        onend: (() => void) | null = null;
        onerror: (() => void) | null = null;
        constructor(public text: string) {}
      },
    });
  });

  it("apresenta können e a frase com áudios de textos separados", async () => {
    render(
      <TeachingActivityBody
        activity={{
          type: "presentation",
          term: "können",
          translation_pt: "poder / conseguir",
          example_sentence: "Ich kann Deutsch.",
          example_translation_pt: "Eu sei alemão.",
          audio_targets: [
            { audio_target_type: "vocabulary_item", audio_text: "können" },
            { audio_target_type: "example_sentence", audio_text: "Ich kann Deutsch." },
          ],
        }}
        languageCode="de"
        response=""
        onResponse={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "können" })).toBeInTheDocument();
    expect(screen.getByText("poder / conseguir")).toBeInTheDocument();
    expect(screen.getByText("Ich kann Deutsch.")).toBeInTheDocument();
    expect(screen.getByText("Eu sei alemão.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Ouvir expressão können" }));
    fireEvent.click(screen.getByRole("button", { name: "Ouvir frase de exemplo" }));

    await waitFor(() => expect(apiBlobMock).toHaveBeenCalledTimes(2));
    expect(
      apiBlobMock.mock.calls.map((call) => (call[1] as { body: { text: string } }).body.text),
    ).toEqual(["können", "Ich kann Deutsch."]);
  });

  it.each([
    ["recognition", "Escolha o significado", "können", ["poder", "querer"]],
    ["reverse_recognition", "Escolha o termo", "poder", ["können", "wollen"]],
  ])("oferece opções acessíveis em %s", (type, groupLabel, prompt, options) => {
    const onResponse = vi.fn();
    render(
      <TeachingActivityBody
        activity={{
          type,
          vocabulary_item_id: "v-1",
          prompt_pt: groupLabel,
          prompt,
          options,
        }}
        response=""
        onResponse={onResponse}
      />,
    );

    const group = screen.getByRole("radiogroup", { name: groupLabel });
    expect(group).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: options[0] }));
    expect(onResponse).toHaveBeenCalledWith(options[0]);
  });

  it("listening toca somente audio_text e não revela termo antes do feedback", async () => {
    render(
      <TeachingActivityBody
        activity={{
          type: "listening_recognition",
          prompt_pt: "Ouça e escolha o significado.",
          prompt: "können",
          show_text: false,
          audio_text: "können",
          audio_target_type: "vocabulary_item",
          options: ["poder", "querer"],
        }}
        languageCode="de"
        response=""
        onResponse={vi.fn()}
      />,
    );

    expect(screen.queryByText("können")).not.toBeInTheDocument();
    expect(screen.queryByText("poder", { selector: "p" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ouvir expressão" }));
    await waitFor(() =>
      expect(apiBlobMock).toHaveBeenCalledWith(
        "/api/v1/speech/synthesize",
        expect.objectContaining({ body: expect.objectContaining({ text: "können" }) }),
      ),
    );
  });

  it("produção permite digitação e fala, usando o transcript como resposta", async () => {
    class FakeMediaRecorder {
      mimeType = "audio/webm";
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob(["audio"], { type: "audio/webm" }) });
        this.onstop?.();
      }
      static isTypeSupported() {
        return true;
      }
    }
    Object.defineProperty(globalThis, "MediaRecorder", {
      configurable: true,
      value: FakeMediaRecorder,
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: vi.fn() }],
        }),
      },
    });
    apiMock.mockResolvedValueOnce({ text: "können", provider: "mock" });
    const onResponse = vi.fn();

    render(
      <TeachingActivityBody
        activity={{
          type: "lexical_production",
          prompt_pt: "Recupere o termo.",
          prompt: "poder / conseguir",
          response_modes: ["typing", "speech"],
        }}
        languageCode="de"
        response=""
        onResponse={onResponse}
      />,
    );

    expect(screen.getByRole("radiogroup", { name: "Modo de resposta" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "Falar" }));
    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));
    await waitFor(() => expect(onResponse).toHaveBeenCalled());
    expect(onResponse.mock.calls[0][0]).toBe("können");

    const form = apiMock.mock.calls[0][1].body as FormData;
    expect(form.get("language_code")).toBe("de");
    expect(form.has("student_response")).toBe(false);
  });
});

describe("ciclo lexical standalone", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("restaura e responde pela rota da lição com o índice atual", async () => {
    const current = session({
      type: "recognition",
      index: 2,
      prompt_pt: "Escolha o significado.",
      prompt: "können",
      options: ["poder", "querer"],
      vocabulary_item_id: "v-1",
    }, 2);
    apiMock
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce({ ...current, current_activity: null, status: "closed" });

    render(<LessonContent mode="vocabulary" lesson={vocabularyLesson()} />);

    fireEvent.click(await screen.findByRole("radio", { name: "poder" }));
    fireEvent.click(screen.getByRole("button", { name: "Enviar tentativa" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/lessons/lesson-1/vocabulary-cycle/answer",
        {
          method: "POST",
          body: { activity_index: 2, student_response: "poder" },
        },
      ),
    );
    expect(await screen.findByText("Sessão concluída")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continuar estudando" })).toBeInTheDocument();
  });

  it("libera reconhecimento expositivo sem resposta e avança a sessão", async () => {
    const noticing = session({
      type: "recognition",
      index: 1,
      prompt_pt: "Observe o padrão destas frases.",
      examples: ["Je réserve une chambre.", "Je confirme la réservation.", "Je demande la clé."],
    }, 1);
    const next = session({
      type: "multiple_choice",
      index: 2,
      prompt_pt: "Escolha a forma adequada.",
      prompt: "Je ___ une chambre.",
      options: ["réserve", "réserves"],
    }, 2);
    apiMock.mockResolvedValueOnce(noticing).mockResolvedValueOnce(next);

    render(<LessonContent mode="vocabulary" lesson={vocabularyLesson()} />);

    expect(await screen.findByText("Observe o padrão destas frases.")).toBeInTheDocument();
    expect(screen.getByText("Je réserve une chambre.")).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    const continueButton = screen.getByRole("button", { name: "Continuar" });
    expect(continueButton).toBeEnabled();

    fireEvent.click(continueButton);

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/lessons/lesson-1/vocabulary-cycle/answer",
        {
          method: "POST",
          body: { activity_index: 1, student_response: "" },
        },
      ),
    );
    expect(await screen.findByText("Escolha a forma adequada.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar tentativa" })).toBeDisabled();
  });

  it.each(["presentation", "listen", "matching", "conversation_prompt"] as const)(
    "trata %s como continuar, sem exigir resposta",
    async (type) => {
      apiMock.mockResolvedValueOnce(
        session({ type, prompt_pt: "Leia e siga.", examples: ["Exemplo."] }),
      );
      render(<LessonContent mode="vocabulary" lesson={vocabularyLesson()} />);
      expect(await screen.findByRole("button", { name: "Continuar" })).toBeEnabled();
      expect(screen.queryByRole("button", { name: "Enviar tentativa" })).not.toBeInTheDocument();
    },
  );

  it("reconhecimento lexical continua exigindo uma alternativa", async () => {
    apiMock.mockResolvedValueOnce(
      session({
        type: "recognition",
        vocabulary_item_id: "v-1",
        prompt_pt: "Escolha o significado.",
        prompt: "clé",
        options: ["chave", "porta"],
      }),
    );
    render(<LessonContent mode="vocabulary" lesson={vocabularyLesson()} />);
    const send = await screen.findByRole("button", { name: "Enviar tentativa" });
    expect(send).toBeDisabled();
    fireEvent.click(screen.getByRole("radio", { name: "chave" }));
    expect(send).toBeEnabled();
  });

  it("inicia quando ainda não há ciclo e mostra estado sem itens devidos", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock
      .mockRejectedValueOnce(new ApiError("não iniciado", 404, "vocabulary_cycle_not_found"))
      .mockResolvedValueOnce({
        status: "no_vocabulary_due",
        lesson_id: "lesson-1",
        flow: null,
        current_activity: null,
        activities_total: 0,
      });

    render(<LessonContent mode="vocabulary" lesson={vocabularyLesson()} />);

    expect(await screen.findByText("Vocabulário em dia")).toBeInTheDocument();
    expect(apiMock).toHaveBeenCalledWith(
      "/api/v1/lessons/lesson-1/vocabulary-cycle/start",
      { method: "POST", body: {} },
    );
  });

  it("preserva o card legado quando o backend não oferece o ciclo", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(
      new ApiError("rota indisponível", 404, "not_found"),
    );

    render(<LessonContent mode="vocabulary" lesson={vocabularyLesson()} />);

    expect(await screen.findByRole("heading", { name: "können" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
