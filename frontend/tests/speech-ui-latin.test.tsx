import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AudioPlayer } from "@/components/study";

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

describe("AudioPlayer — fallback latim eclesiástico (it-IT)", () => {
  type FakeUtterance = {
    text: string;
    lang: string;
    rate: number;
    voice: { lang: string; name: string } | null;
    onend: (() => void) | null;
    onerror: (() => void) | null;
  };

  let speak: ReturnType<typeof vi.fn>;
  let getVoices: ReturnType<typeof vi.fn>;
  let lastUtterance: FakeUtterance | null;

  beforeEach(async () => {
    apiMock.mockReset();
    apiBlobMock.mockReset();
    const { ApiError } = await import("@/lib/api");
    apiBlobMock.mockRejectedValue(
      new ApiError("idioma sem voz no Piper", 400, "tts_unsupported_language"),
    );

    speak = vi.fn();
    getVoices = vi.fn(() => []);
    lastUtterance = null;

    class FakeUtteranceClass {
      text: string;
      lang = "";
      rate = 1;
      voice: { lang: string; name: string } | null = null;
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(text: string) {
        this.text = text;
        lastUtterance = this;
      }
    }

    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        cancel: vi.fn(),
        speak,
        getVoices,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });
    Object.defineProperty(globalThis, "SpeechSynthesisUtterance", {
      configurable: true,
      value: FakeUtteranceClass,
    });
  });

  it("em la envia ao backend o texto já preparado, não o ortográfico bruto", async () => {
    render(<AudioPlayer text="caelum" languageCode="la" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await waitFor(() => expect(apiBlobMock).toHaveBeenCalled());
    const body = apiBlobMock.mock.calls[0][1].body as { text: string; language_code: string };
    expect(body.language_code).toBe("la");
    expect(body.text.toLowerCase()).toBe("celum");
    expect(body.text.toLowerCase()).not.toBe("caelum");
  });

  it("latim clássico não chama o backend e vai direto à voz do navegador", async () => {
    render(<AudioPlayer text="caelum" languageCode="la-classical" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(apiBlobMock).not.toHaveBeenCalled();
    expect(lastUtterance!.text.toLowerCase()).not.toBe("caelum");
  });

  it("em la usa speechText preparado (não o ortográfico bruto caelum)", async () => {
    render(<AudioPlayer text="caelum" languageCode="la" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(lastUtterance!.text.toLowerCase()).not.toBe("caelum");
    expect(lastUtterance!.text.toLowerCase().startsWith("ce")).toBe(true);
  });

  it("em la define utterance.lang = it-IT", async () => {
    render(<AudioPlayer text="caelum" languageCode="la" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(lastUtterance!.lang).toBe("it-IT");
  });

  it("seleciona voz italiana quando disponível", async () => {
    const italian = { lang: "it-IT", name: "Google italiano" };
    const english = { lang: "en-US", name: "Google US English" };
    getVoices.mockReturnValue([english, italian]);

    render(<AudioPlayer text="caelum" languageCode="la" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(lastUtterance!.voice).toEqual(italian);
  });

  it("sem voz italiana não escolhe voz de outro idioma", async () => {
    getVoices.mockReturnValue([{ lang: "en-US", name: "Google US English" }]);

    render(<AudioPlayer text="caelum" languageCode="la" />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(lastUtterance!.lang).toBe("it-IT");
    expect(lastUtterance!.voice).toBeNull();
  });

  it("inglês/espanhol/francês/japonês/chinês mantêm lang BCP-47 atual no fallback", async () => {
    const { ApiError } = await import("@/lib/api");
    apiBlobMock.mockRejectedValue(new ApiError("falha", 503, "tts_unavailable"));

    const cases: Array<[string, string, string]> = [
      ["en", "Hello", "en-US"],
      ["es-ES", "Hola", "es-ES"],
      ["fr", "Bonjour", "fr-FR"],
      ["ja", "こんにちは", "ja-JP"],
      ["zh-CN", "你好", "zh-CN"],
    ];

    for (const [code, sample, expectedLang] of cases) {
      speak.mockClear();
      lastUtterance = null;
      const { unmount } = render(<AudioPlayer text={sample} languageCode={code} />);
      fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
      await waitFor(() => expect(speak).toHaveBeenCalled());
      expect(lastUtterance!.lang).toBe(expectedLang);
      expect(lastUtterance!.text).toBe(sample);
      unmount();
    }
  });

  it("texto visível / aria permanece a ortografia original em la", async () => {
    render(
      <AudioPlayer variant="compact" label="Ouvir" text="caelum" languageCode="la" />,
    );
    expect(screen.getByRole("button", { name: /Ouvir: caelum/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Ouvir/ }));
    await waitFor(() => expect(speak).toHaveBeenCalled());
    expect(lastUtterance!.text.toLowerCase()).not.toBe("caelum");
  });

  it("em atividade fonética, falha de preparação não reproduz latim bruto", async () => {
    const prep = await import("@/lib/ecclesiastical-latin-speech");
    const spy = vi.spyOn(prep, "prepareEcclesiasticalLatinForSpeech").mockReturnValue("");

    render(<AudioPlayer text="caelum" languageCode="la" phoneticActivity />);
    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));

    await waitFor(() =>
      expect(
        screen.getByText("Áudio de pronúncia indisponível para este item."),
      ).toBeInTheDocument(),
    );
    expect(speak).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("voiceschanged atualiza vozes sem disparar reprodução duplicada", async () => {
    const listeners: Record<string, Array<() => void>> = {};
    const italian = { lang: "it-IT", name: "Microsoft Elsa" };
    getVoices.mockReturnValue([]);

    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        cancel: vi.fn(),
        speak,
        getVoices,
        addEventListener: (event: string, cb: () => void) => {
          listeners[event] = listeners[event] ?? [];
          listeners[event].push(cb);
        },
        removeEventListener: vi.fn(),
      },
    });

    render(<AudioPlayer text="caelum" languageCode="la" />);
    getVoices.mockReturnValue([italian]);
    listeners.voiceschanged?.forEach((cb) => cb());
    expect(speak).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Reproduzir áudio" }));
    await waitFor(() => expect(speak).toHaveBeenCalledTimes(1));
    expect(lastUtterance!.voice).toEqual(italian);
  });
});
