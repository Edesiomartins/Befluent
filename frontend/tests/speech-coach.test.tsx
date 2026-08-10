import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SpeechCoach } from "@/components/speech-coach";

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

vi.mock("@/components/study", () => ({
  AudioPlayer: ({ text }: { text: string }) => (
    <button type="button" aria-label={`Reproduzir ${text}`}>
      TTS {text}
    </button>
  ),
  Recorder: ({
    onTranscript,
  }: {
    onTranscript?: (text: string, meta?: { provider?: string }) => void;
  }) => (
    <button
      type="button"
      aria-label="Iniciar gravação"
      onClick={() => onTranscript?.("I strongly disagree with argument.", { provider: "mock" })}
    >
      GRAVAR
    </button>
  ),
}));

describe("SpeechCoach", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("mostra frase-alvo, TTS e chama speech-coach após STT", async () => {
    apiMock.mockResolvedValue({
      status: "needs_practice",
      is_phonetic_score: false,
      pedagogical_error: true,
      success: false,
      transcript: "I strongly disagree with argument.",
      normalized_target: "i strongly disagree with that argument",
      normalized_transcript: "i strongly disagree with argument",
      alignment_sequence: [
        { role: "match", token: "i" },
        { role: "match", token: "strongly" },
        { role: "match", token: "disagree" },
        { role: "match", token: "with" },
        { role: "miss", token: "that" },
        { role: "match", token: "argument" },
      ],
      feedback: {
        summary_pt: "Não consegui identificar «that» com clareza na sua fala.",
        points: [
          {
            kind: "missed",
            label_pt: "Não consegui identificar «that» com clareza na sua fala.",
            token: "that",
          },
        ],
        metric_name: "speech_correspondence",
        metric_label_pt: "Correspondência da fala (tokens reconhecidos)",
        coverage: 0.83,
      },
      repair: {
        action: "retry_full",
        label_pt: "Ouça a frase de novo e tente a frase completa.",
        level: 1,
        allow_continue: false,
        practice_chunk: null,
      },
      practice_chunk: "with that argument",
      attempt_number: 1,
      te_evidence: null,
    });

    render(
      <SpeechCoach
        targetText="I strongly disagree with that argument."
        languageCode="en"
      />,
    );

    expect(screen.getByText(/frase para falar/i)).toBeInTheDocument();
    expect(screen.getByText(/ouvir frase/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /reproduzir i strongly disagree with that argument/i,
      }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /iniciar gravação/i }));

    await waitFor(() => {
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/teaching/speech-coach",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            target_text: "I strongly disagree with that argument.",
            transcript: "I strongly disagree with argument.",
            mode: "repetition",
          }),
        }),
      );
    });

    expect(await screen.findByText(/o befluent entendeu/i)).toBeInTheDocument();
    expect(screen.getAllByText(/não consegui identificar/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/não identificado/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/pronúncia \d+%/i)).not.toBeInTheDocument();
    expect(screen.getByText(/não é nota de pronúncia/i)).toBeInTheDocument();
  });

  it("oferece praticar trecho quando repair pede chunk", async () => {
    apiMock.mockResolvedValue({
      status: "needs_practice",
      is_phonetic_score: false,
      pedagogical_error: true,
      success: false,
      transcript: "I disagree",
      normalized_target: "i strongly disagree",
      normalized_transcript: "i disagree",
      alignment_sequence: [
        { role: "match", token: "i" },
        { role: "miss", token: "strongly" },
        { role: "match", token: "disagree" },
      ],
      feedback: {
        summary_pt: "Trecho pouco claro.",
        points: [{ kind: "missed", label_pt: "Faltou strongly.", token: "strongly" }],
        metric_name: "speech_correspondence",
        metric_label_pt: "Correspondência da fala",
        coverage: 0.5,
      },
      repair: {
        action: "practice_chunk",
        label_pt: "Vamos isolar um trecho.",
        level: 2,
        allow_continue: false,
        practice_chunk: "i strongly disagree",
      },
      practice_chunk: "i strongly disagree",
      attempt_number: 2,
    });

    render(<SpeechCoach targetText="I strongly disagree" languageCode="en" />);
    fireEvent.click(screen.getByRole("button", { name: /iniciar gravação/i }));

    expect(await screen.findByText(/trecho para praticar/i)).toBeInTheDocument();
    expect(screen.getByText(/ouvir trecho/i)).toBeInTheDocument();
    expect(screen.getByText(/repetir trecho/i)).toBeInTheDocument();
  });
});
