import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { KokoroVoiceLab } from "@/components/kokoro-voice-lab";

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

const VOICES_RESPONSE = {
  model: "hexgrad/kokoro-82m",
  languages: [
    {
      code: "en-US",
      name: "English — US",
      voices: [
        { id: "af_heart", name: "Heart", gender: "female" },
        { id: "af_bella", name: "Bella", gender: "female" },
      ],
    },
    {
      code: "es-ES",
      name: "Spanish",
      voices: [{ id: "ef_dora", name: "Dora", gender: "female" }],
    },
  ],
};

const DEFAULT_TEXT = "Hello! How are you doing today?";

function generateResult(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    model: "hexgrad/kokoro-82m",
    language: "en-US",
    voice: "af_heart",
    audio_base64: btoa("fake-audio-bytes"),
    content_type: "audio/mpeg",
    latency_ms: 410,
    audio_size_bytes: 86016,
    ...overrides,
  };
}

/** Renderiza e espera o carregamento assíncrono (fetch de vozes + o
 * `useEffect` de idioma que aplica o preset inicial) terminar de assentar,
 * em vez de só esperar o cabeçalho aparecer — o cabeçalho é estático e
 * aparece antes desse efeito rodar, o que causaria cliques em cima de um
 * estado ainda incompleto. */
async function renderReady() {
  render(<KokoroVoiceLab />);
  await screen.findByText("Kokoro Voice Lab");
  await waitFor(() => expect(screen.getByLabelText("Texto")).toHaveValue(DEFAULT_TEXT));
}

describe("KokoroVoiceLab", () => {
  beforeEach(() => {
    apiMock.mockReset();
    Object.defineProperty(globalThis.URL, "createObjectURL", { writable: true, value: vi.fn(() => "blob:mock-url") });
    Object.defineProperty(globalThis.URL, "revokeObjectURL", { writable: true, value: vi.fn() });
    Object.defineProperty(globalThis.navigator, "clipboard", {
      writable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("carrega idiomas e filtra vozes pelo idioma selecionado", async () => {
    apiMock.mockResolvedValueOnce(VOICES_RESPONSE);
    await renderReady();

    const voiceSelect = screen.getByLabelText("Voz") as HTMLSelectElement;
    const options = within(voiceSelect).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(["Heart (af_heart)", "Bella (af_bella)"]);
    expect(options.some((o) => o.textContent?.includes("Dora"))).toBe(false);
  });

  it("trocar idioma limpa a voz e mostra só vozes compatíveis", async () => {
    apiMock.mockResolvedValueOnce(VOICES_RESPONSE);
    await renderReady();

    fireEvent.change(screen.getByLabelText("Idioma"), { target: { value: "es-ES" } });

    await waitFor(() => {
      const voiceSelect = screen.getByLabelText("Voz") as HTMLSelectElement;
      const options = within(voiceSelect).getAllByRole("option");
      expect(options.map((o) => o.textContent)).toEqual(["Dora (ef_dora)"]);
    });
  });

  it("preenche o texto ao escolher um preset", async () => {
    apiMock.mockResolvedValueOnce(VOICES_RESPONSE);
    await renderReady();

    fireEvent.click(screen.getByRole("button", { name: "Pergunta" }));
    expect(screen.getByLabelText("Texto")).toHaveValue("Could you tell me where the nearest train station is?");
  });

  it("gera individualmente e mostra player, latência e tamanho", async () => {
    apiMock.mockResolvedValueOnce(VOICES_RESPONSE);
    await renderReady();

    apiMock.mockResolvedValueOnce(generateResult());
    const [gerar] = screen.getAllByRole("button", { name: "Gerar" });
    fireEvent.click(gerar);

    expect((await screen.findAllByText("410 ms")).length).toBeGreaterThan(0);
    expect(document.querySelector("audio")).toBeTruthy();
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/tts-lab/kokoro/generate",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ language: "en-US", voice: "af_heart" }),
        }),
      ),
    );
  });

  it("comparar todas as vozes gera cada voz de forma independente; erro em uma não trava as demais", async () => {
    apiMock.mockResolvedValueOnce(VOICES_RESPONSE);
    await renderReady();

    const { ApiError } = await import("@/lib/api");
    apiMock
      .mockRejectedValueOnce(new ApiError("Provedor indisponível", 503, "tts_lab_unavailable"))
      .mockResolvedValueOnce(generateResult({ voice: "af_bella" }));

    fireEvent.click(screen.getByRole("button", { name: "Comparar todas as vozes" }));

    expect(await screen.findByText(/Provedor indisponível/)).toBeInTheDocument();
    expect((await screen.findAllByText("410 ms")).length).toBeGreaterThan(0);
    expect(apiMock).toHaveBeenCalledTimes(3); // voices + 2 generate calls (af_heart, af_bella)
  });

  it("registra avaliação manual (clareza é o campo principal) sem chamar o backend", async () => {
    apiMock.mockResolvedValueOnce(VOICES_RESPONSE);
    await renderReady();
    const callsBefore = apiMock.mock.calls.length;

    const select = screen.getByLabelText("Clareza — af_heart");
    fireEvent.change(select, { target: { value: "5" } });
    expect(select).toHaveValue("5");
    expect(apiMock).toHaveBeenCalledTimes(callsBefore); // nenhuma chamada extra
  });

  it("marca e desmarca a voz preferida da sessão", async () => {
    apiMock.mockResolvedValueOnce(VOICES_RESPONSE);
    await renderReady();

    const marcar = screen.getAllByRole("button", { name: "☆ Minha preferida" })[0];
    fireEvent.click(marcar);
    expect(screen.getByRole("button", { name: "⭐ Preferida" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "⭐ Preferida" }));
    expect(screen.queryByRole("button", { name: "⭐ Preferida" })).not.toBeInTheDocument();
  });

  it("modo teste cego esconde identidade das vozes até revelar", async () => {
    apiMock.mockResolvedValueOnce(VOICES_RESPONSE);
    await renderReady();

    fireEvent.click(screen.getByLabelText("Modo teste cego"));

    expect(screen.queryByText(/Voice ID:/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/^Voz [A-Z]$/).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Revelar vozes" }));
    expect(screen.getAllByText(/Voice ID:/).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Heart (af_heart)" })).toBeInTheDocument();
  });

  it("mostra estado de carregamento antes das vozes chegarem", () => {
    apiMock.mockReturnValueOnce(new Promise(() => {}));
    render(<KokoroVoiceLab />);
    expect(screen.getByText("Carregando vozes…")).toBeInTheDocument();
  });
});
