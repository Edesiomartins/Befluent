import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import TTSLabPage from "@/app/(app)/admin/tts-lab/page";

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

const EMPTY_KOKORO_VOICES = { model: "hexgrad/kokoro-82m", languages: [] };

/** A página agora dispara duas chamadas GET no mount (modelos genéricos +
 * vozes do Kokoro Voice Lab), em uma ordem que não é garantida pelo React.
 * `mockApi` resolve/rejeita por path em vez de depender da ordem das
 * chamadas, e ainda permite empilhar `.mockResolvedValueOnce`/
 * `.mockRejectedValueOnce` por cima para as chamadas de geração feitas
 * depois do mount (essas continuam consumidas em fila, na ordem de clique). */
function mockApi(handlers: Record<string, unknown>) {
  apiMock.mockImplementation((path: string) => {
    if (!(path in handlers)) return Promise.reject(new Error(`unmocked path: ${path}`));
    return Promise.resolve(handlers[path]);
  });
}

const MODELS = {
  models: [
    {
      id: "hexgrad/kokoro-82m",
      display_name: "Kokoro 82M",
      provider: "hexgrad",
      supports_speed: true,
      supports_voice: true,
      supported_formats: ["mp3"],
      default_voice: "af_heart",
      free: false,
    },
    {
      id: "deepgram/flux-tts:free",
      display_name: "Deepgram Flux",
      provider: "deepgram",
      supports_speed: false,
      supports_voice: false,
      supported_formats: ["mp3"],
      default_voice: null,
      free: true,
    },
  ],
};

function generateResult(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    model: "hexgrad/kokoro-82m",
    audio_base64: btoa("fake-audio-bytes"),
    content_type: "audio/mpeg",
    latency_ms: 620,
    audio_size_bytes: 86016,
    free_model: false,
    cost_available: false,
    estimated_cost: null,
    ...overrides,
  };
}

describe("TTSLabPage", () => {
  beforeEach(() => {
    apiMock.mockReset();
    Object.defineProperty(globalThis.URL, "createObjectURL", {
      writable: true,
      value: vi.fn(() => "blob:mock-url"),
    });
    Object.defineProperty(globalThis.URL, "revokeObjectURL", {
      writable: true,
      value: vi.fn(),
    });
  });

  it("carrega e lista os modelos configurados", async () => {
    mockApi({ "/api/v1/tts-lab/models": MODELS, "/api/v1/tts-lab/kokoro/voices": EMPTY_KOKORO_VOICES });
    render(<TTSLabPage />);

    expect(screen.getByText("TTS Lab")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Kokoro 82M" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Deepgram Flux" })).toBeInTheDocument();
  });

  it("preenche o texto ao escolher um preset", async () => {
    mockApi({ "/api/v1/tts-lab/models": MODELS, "/api/v1/tts-lab/kokoro/voices": EMPTY_KOKORO_VOICES });
    render(<TTSLabPage />);
    await screen.findByRole("heading", { name: "Kokoro 82M" });

    fireEvent.click(screen.getByRole("button", { name: "Direções" }));
    expect(screen.getByLabelText("Texto para teste")).toHaveValue(
      "Could you tell me where the nearest train station is?",
    );
  });

  it("gera individualmente e mostra player, latência e tamanho", async () => {
    mockApi({ "/api/v1/tts-lab/models": MODELS, "/api/v1/tts-lab/kokoro/voices": EMPTY_KOKORO_VOICES });
    render(<TTSLabPage />);
    await screen.findByRole("heading", { name: "Kokoro 82M" });

    apiMock.mockResolvedValueOnce(generateResult());
    const [gerarKokoro] = screen.getAllByRole("button", { name: "Gerar" });
    fireEvent.click(gerarKokoro);

    expect((await screen.findAllByText("620 ms")).length).toBeGreaterThan(0);
    expect(screen.getByText("84 KB")).toBeInTheDocument();
    expect(document.querySelector("audio")).toBeTruthy();
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/tts-lab/generate",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ model: "hexgrad/kokoro-82m" }),
        }),
      ),
    );
  });

  it("erro em um modelo não interrompe os demais ao gerar em todos", async () => {
    mockApi({ "/api/v1/tts-lab/models": MODELS, "/api/v1/tts-lab/kokoro/voices": EMPTY_KOKORO_VOICES });
    render(<TTSLabPage />);
    await screen.findByRole("heading", { name: "Kokoro 82M" });

    const { ApiError } = await import("@/lib/api");
    apiMock
      .mockRejectedValueOnce(new ApiError("Provedor indisponível", 503, "tts_lab_unavailable"))
      .mockResolvedValueOnce(generateResult({ model: "deepgram/flux-tts:free" }));

    fireEvent.click(screen.getByRole("button", { name: "Gerar em todos" }));

    expect(await screen.findByText(/Provedor indisponível/)).toBeInTheDocument();
    expect((await screen.findAllByText("620 ms")).length).toBeGreaterThan(0);
    expect(apiMock).toHaveBeenCalledTimes(4); // models + kokoro voices + 2 generate calls
  });

  it("registra avaliação manual sem persistir no backend", async () => {
    mockApi({ "/api/v1/tts-lab/models": MODELS, "/api/v1/tts-lab/kokoro/voices": EMPTY_KOKORO_VOICES });
    render(<TTSLabPage />);
    await screen.findByRole("heading", { name: "Kokoro 82M" });

    const select = screen.getByLabelText("naturalidade — Kokoro 82M");
    fireEvent.change(select, { target: { value: "4" } });
    expect(select).toHaveValue("4");
    expect(apiMock).toHaveBeenCalledTimes(2); // chamadas iniciais de /models e /kokoro/voices
  });

  it("mostra mensagem de acesso restrito em 403", async () => {
    const { ApiError } = await import("@/lib/api");
    mockApi({
      "/api/v1/tts-lab/models": Promise.reject(new ApiError("Acesso não autorizado", 403, "tts_lab_forbidden")),
      "/api/v1/tts-lab/kokoro/voices": EMPTY_KOKORO_VOICES,
    });
    render(<TTSLabPage />);

    expect(await screen.findByText("Acesso restrito")).toBeInTheDocument();
  });
});
