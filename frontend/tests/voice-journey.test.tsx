import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LessonContent } from "@/components/lesson-modes";
import { TeachingActivityBody } from "@/components/teaching-activity";
import type { ConversationLesson } from "@/types/lesson";

const apiMock = vi.fn();

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status = 400, code?: string) {
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

vi.mock("@/hooks/use-active-language", () => ({
  useActiveLanguage: () => ({ code: "fr", resolved: true }),
}));

function voiceLesson(situation: string): ConversationLesson {
  return {
    mode: "voice",
    provider: "mock",
    language_code: "fr",
    level: "B1",
    overall_level: "B1",
    skill: "speaking",
    skill_label: "Conversação",
    level_source: "placement_test",
    level_is_estimated: false,
    lesson_id: "lesson-voice",
    study_session_id: "session-1",
    title: "Conversação",
    objective: "Praticar a missão.",
    situation,
    opening: "Bonjour.",
    opening_translation: "Bom dia.",
    suggested_replies: [],
    target_expressions: [],
  };
}

function installRecorder(transcript: string) {
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
  apiMock.mockImplementation((path: string) => {
    if (path === "/api/v1/speech/transcribe") {
      return Promise.resolve({ text: transcript, provider: "mock" });
    }
    if (path === "/api/v1/conversations") return Promise.resolve({ id: "conv-1" });
    if (path === "/api/v1/conversations/conv-1/messages") {
      return Promise.resolve({ reply: "Vous avez une réservation ?" });
    }
    if (path === "/api/v1/conversations/conv-1/complete") {
      return Promise.resolve({ id: "conv-1", status: "completed" });
    }
    if (path === "/api/v1/lessons/lesson-voice/complete") {
      return Promise.resolve({ lesson_id: "lesson-voice", status: "completed" });
    }
    return Promise.resolve({});
  });
}

async function speak() {
  fireEvent.click(await screen.findByRole("button", { name: "Iniciar gravação" }));
  fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));
  await waitFor(() =>
    expect(apiMock).toHaveBeenCalledWith(
      "/api/v1/conversations",
      expect.objectContaining({ method: "POST" }),
    ),
  );
}

describe("Journey + voz", () => {
  beforeEach(() => {
    apiMock.mockReset();
    installRecorder("Bonjour, j'ai une réservation.");
  });

  it("usa o cenário da missão quando a situação da lição é genérica", async () => {
    render(
      <LessonContent
        mode="voice"
        lesson={voiceLesson("Conversa livre")}
        missionScenario="Fazer check-in em um hotel"
        coachLanguageCode="fr"
      />,
    );

    expect(await screen.findByText("Fazer check-in em um hotel")).toBeInTheDocument();
    await speak();
    expect(apiMock).toHaveBeenCalledWith("/api/v1/conversations", {
      method: "POST",
      body: expect.objectContaining({
        topic: "Fazer check-in em um hotel",
        language_code: "fr",
        study_session_id: "session-1",
      }),
    });
  });

  it("prática livre continua usando a situação da lição", async () => {
    render(
      <LessonContent
        mode="voice"
        lesson={voiceLesson("Apresentar-se a alguém que você acabou de conhecer")}
      />,
    );

    expect(
      await screen.findByText("Apresentar-se a alguém que você acabou de conhecer"),
    ).toBeInTheDocument();
    await speak();
    expect(apiMock).toHaveBeenCalledWith("/api/v1/conversations", {
      method: "POST",
      body: expect.objectContaining({
        topic: "Apresentar-se a alguém que você acabou de conhecer",
      }),
    });
  });

  it("encerra a conversa e a lição, e só então marca a prática como encerrada", async () => {
    render(<LessonContent mode="voice" lesson={voiceLesson("Na recepção")} />);
    await speak();
    fireEvent.click(screen.getByRole("button", { name: "Encerrar prática" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/conversations/conv-1/complete", {
        method: "POST",
        body: {},
      }),
    );
    expect(apiMock).toHaveBeenCalledWith("/api/v1/lessons/lesson-voice/complete", {
      method: "POST",
      body: {},
    });
    expect(await screen.findByRole("button", { name: "Encerrada" })).toBeDisabled();
  });

  it("não marca a prática como encerrada se o complete da conversa falhar", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/speech/transcribe") {
        return Promise.resolve({ text: "Bonjour", provider: "mock" });
      }
      if (path === "/api/v1/conversations") return Promise.resolve({ id: "conv-1" });
      if (path === "/api/v1/conversations/conv-1/messages") {
        return Promise.resolve({ reply: "Bonjour." });
      }
      if (path === "/api/v1/conversations/conv-1/complete") {
        return Promise.reject(new Error("falha ao encerrar"));
      }
      return Promise.resolve({});
    });

    render(<LessonContent mode="voice" lesson={voiceLesson("Na recepção")} />);
    await speak();
    fireEvent.click(screen.getByRole("button", { name: "Encerrar prática" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/não foi possível encerrar/i);
    expect(screen.getByRole("button", { name: "Encerrar prática" })).toBeEnabled();
    expect(apiMock).not.toHaveBeenCalledWith(
      "/api/v1/lessons/lesson-voice/complete",
      expect.anything(),
    );
  });
});

describe("atividades passivas e ativas", () => {
  it("conversation_prompt não mostra campo de resposta", () => {
    render(
      <TeachingActivityBody
        activity={{
          type: "conversation_prompt",
          prompt_pt: "Você chegou ao hotel e precisa confirmar a reserva.",
          prompt: "Confirmar a reserva",
        }}
        response=""
        onResponse={vi.fn()}
      />,
    );
    expect(screen.getByText(/chegou ao hotel/i)).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Sua resposta" })).not.toBeInTheDocument();
  });

  it.each(["presentation", "listen", "matching", "recognition"] as const)(
    "%s passivo não mostra campo obrigatório",
    (type) => {
      render(
        <TeachingActivityBody
          activity={{
            type,
            prompt_pt: "Leia e continue.",
            examples: ["Frase."],
            pairs: type === "matching" ? [{ term: "clé", hint_pt: "chave" }] : undefined,
          }}
          response=""
          onResponse={vi.fn()}
        />,
      );
      expect(screen.queryByRole("textbox", { name: "Sua resposta" })).not.toBeInTheDocument();
    },
  );

  it("fill_gap ativo oferece um campo de resposta", () => {
    render(
      <TeachingActivityBody
        activity={{ type: "fill_gap", prompt_pt: "Complete.", prompt: "Je ___ ." }}
        response=""
        onResponse={vi.fn()}
      />,
    );
    expect(screen.getByRole("textbox", { name: "Sua resposta" })).toBeInTheDocument();
  });
});
