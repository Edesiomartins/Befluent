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

  it("mostra 'Gerando áudio…' enquanto aguarda o backend, sem bloquear a página", async () => {
    let resolveBlob!: (blob: Blob) => void;
    apiBlobMock.mockReturnValue(new Promise<Blob>((resolve) => (resolveBlob = resolve)));

    render(<AudioPlayer text="Hello" languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));

    expect(await screen.findByText("Gerando áudio…")).toBeInTheDocument();

    resolveBlob(new Blob(["fake-mp3"], { type: "audio/mpeg" }));
    expect(await screen.findByText("Voz do BeFluent")).toBeInTheDocument();
  });

  it("envia a velocidade selecionada no corpo da requisição", async () => {
    apiBlobMock.mockResolvedValue(new Blob(["fake-mp3"], { type: "audio/mpeg" }));

    render(<AudioPlayer text="Hello" languageCode="en" />);
    fireEvent.change(screen.getByLabelText("Velocidade"), { target: { value: "1.25" } });
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));

    await waitFor(() =>
      expect(apiBlobMock).toHaveBeenCalledWith(
        "/api/v1/speech/synthesize",
        expect.objectContaining({ body: expect.objectContaining({ speed: 1.25 }) }),
      ),
    );
  });

  it("libera a URL do áudio anterior ao gerar um novo, sem vazar memória", async () => {
    apiBlobMock.mockResolvedValue(new Blob(["fake-mp3"], { type: "audio/mpeg" }));
    const revoke = vi.fn();
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revoke });

    render(<AudioPlayer text="Hello" languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await screen.findByText("Voz do BeFluent");

    fireEvent.click(screen.getByRole("button", { name: "Pausar áudio" })); // stop
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" })); // gera de novo
    await waitFor(() => expect(apiBlobMock).toHaveBeenCalledTimes(2));

    expect(revoke).toHaveBeenCalledWith("blob:fake-url");
  });

  it("cancela a geração em andamento ao clicar em parar, sem acionar o fallback do navegador", async () => {
    const speak = vi.fn();
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: { cancel: vi.fn(), speak },
    });

    let capturedSignal: AbortSignal | undefined;
    apiBlobMock.mockImplementation(
      (_path: string, options: { signal?: AbortSignal }) =>
        new Promise((_resolve, reject) => {
          capturedSignal = options.signal;
          options.signal?.addEventListener("abort", () => {
            const err = new DOMException("aborted", "AbortError");
            reject(err);
          });
        }),
    );

    render(<AudioPlayer text="Hello" languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await screen.findByText("Gerando áudio…");

    fireEvent.click(screen.getByRole("button", { name: "Pausar áudio" })); // stop cancela o fetch em voo

    await waitFor(() => expect(capturedSignal?.aborted).toBe(true));
    expect(speak).not.toHaveBeenCalled(); // cancelamento não é falha do provedor — sem fallback
    expect(screen.getByRole("button", { name: "Reproduzir áudio" })).toBeInTheDocument();
  });

  it("nenhuma chamada é feita diretamente à OpenRouter — só ao backend do BeFluent", async () => {
    apiBlobMock.mockResolvedValue(new Blob(["fake-mp3"], { type: "audio/mpeg" }));
    render(<AudioPlayer text="Hello" languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));

    await waitFor(() => expect(apiBlobMock).toHaveBeenCalled());
    const [path] = apiBlobMock.mock.calls[0];
    expect(path).toBe("/api/v1/speech/synthesize");
    expect(path).not.toMatch(/openrouter/i);
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
