import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AudioPlayer, Chat, Recorder } from "@/components/study";

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

describe("AudioPlayer (Kokoro-82M com fallback local)", () => {
  beforeEach(() => {
    apiMock.mockReset();
    apiBlobMock.mockReset();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:fake-url"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "play", {
      configurable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "pause", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("toca o áudio do backend (Kokoro) quando a síntese funciona", async () => {
    apiBlobMock.mockResolvedValue(new Blob(["fake-mp3"], { type: "audio/mpeg" }));

    render(<AudioPlayer text="Hello" languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));

    await waitFor(() =>
      expect(apiBlobMock).toHaveBeenCalledWith(
        "/api/v1/speech/synthesize",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ text: "Hello", language_code: "en" }),
        }),
      ),
    );
    expect(await screen.findByText("Voz do BeFluent")).toBeInTheDocument();
    expect(apiMock).not.toHaveBeenCalled();
  });

  it("cai para SpeechSynthesis do navegador quando o backend de TTS falha", async () => {
    const { ApiError } = await import("@/lib/api");
    apiBlobMock.mockRejectedValue(
      new ApiError("O serviço de síntese de voz está temporariamente indisponível.", 503, "tts_unavailable"),
    );
    const speak = vi.fn();
    class FakeUtterance {
      text: string;
      lang = "";
      rate = 1;
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(text: string) {
        this.text = text;
      }
    }
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: { cancel: vi.fn(), speak },
    });
    Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
      configurable: true,
      value: FakeUtterance,
    });

    render(<AudioPlayer text="Hello" languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));

    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(await screen.findByText("Voz do navegador")).toBeInTheDocument();
  });

  it("avisa quando backend falha e o navegador não oferece SpeechSynthesis", async () => {
    const { ApiError } = await import("@/lib/api");
    apiBlobMock.mockRejectedValue(new ApiError("indisponível", 503, "tts_unavailable"));
    Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
      configurable: true,
      value: undefined,
    });

    render(<AudioPlayer text="Bonjour" languageCode="fr" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/não oferece leitura em voz alta/i);
  });
});

describe("Recorder / STT", () => {
  beforeEach(() => {
    apiMock.mockReset();
    class FakeMediaRecorder {
      mimeType = "audio/webm";
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      constructor(_stream: unknown, _options?: { mimeType?: string }) {}
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
      writable: true,
      value: FakeMediaRecorder,
    });
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: vi.fn() }],
        }),
      },
    });
  });

  it("não mostra banner de mock quando o provider é groq", async () => {
    const onTranscript = vi.fn();
    apiMock.mockResolvedValue({
      text: "hello there",
      provider: "groq",
      model: "whisper-large-v3-turbo",
    });

    render(<Recorder onTranscript={onTranscript} languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));

    await waitFor(() => expect(onTranscript).toHaveBeenCalledWith("hello there", expect.any(Object)));
    expect(screen.queryByText(/modo mock/i)).not.toBeInTheDocument();
  });

  it("mostra aviso quando o provider é mock", async () => {
    apiMock.mockResolvedValue({
      text: "[mock] Transcrição simulada",
      provider: "mock",
      model: null,
    });

    render(<Recorder languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));

    expect(await screen.findByText(/modo mock/i)).toBeInTheDocument();
  });

  it("mostra erro e retry sem inventar transcript quando STT falha", async () => {
    const { ApiError } = await import("@/lib/api");
    const onTranscript = vi.fn();
    apiMock.mockRejectedValue(
      new ApiError(
        "O serviço de reconhecimento de fala está temporariamente indisponível.",
        503,
        "stt_unavailable",
      ),
    );

    render(<Recorder onTranscript={onTranscript} languageCode="ja" />);
    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/indisponível/i);
    expect(screen.getByRole("button", { name: "Tentar gravar de novo" })).toBeInTheDocument();
    expect(onTranscript).not.toHaveBeenCalled();
  });
});

describe("Chat / conversação", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("não trata resposta openrouter como mock", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/conversations") return Promise.resolve({ id: "c1" });
      if (path === "/api/v1/conversations/c1/messages") {
        return Promise.resolve({
          reply: "Nice to meet you.",
          provider: "openrouter",
          model: "nvidia/nemotron-3-ultra-550b-a55b:free",
          corrections: [],
          corrections_available: true,
        });
      }
      return Promise.resolve({});
    });

    render(<Chat languageCode="en" opening="Hello!" />);
    await waitFor(() => expect(apiMock).toHaveBeenCalled());
    fireEvent.change(screen.getByPlaceholderText("Escreva sua resposta…"), {
      target: { value: "Hi" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByText("Nice to meet you.")).toBeInTheDocument();
    expect(screen.queryByText(/modo local \(mock/i)).not.toBeInTheDocument();
  });

  it("mostra indisponibilidade sem inventar fala do tutor", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/conversations") return Promise.resolve({ id: "c1" });
      if (path === "/api/v1/conversations/c1/messages") {
        return Promise.reject(
          new ApiError("O serviço de IA está temporariamente indisponível.", 503, "ai_unavailable"),
        );
      }
      return Promise.resolve({});
    });

    render(<Chat languageCode="en" opening="Hello!" />);
    await waitFor(() => expect(apiMock).toHaveBeenCalled());
    fireEvent.change(screen.getByPlaceholderText("Escreva sua resposta…"), {
      target: { value: "Hi" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/indisponível/i);
    expect(screen.getByText(/Serviço de IA temporariamente indisponível/i)).toBeInTheDocument();
    expect(screen.queryByText("Hi")).toBeInTheDocument(); // mensagem do aluno permanece
  });
});
