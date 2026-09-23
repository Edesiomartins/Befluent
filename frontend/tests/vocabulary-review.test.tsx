import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StudyModePage from "@/app/(app)/learn/[mode]/page";

const apiMock = vi.fn();
const apiBlobMock = vi.fn();
const notFound = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }),
  useParams: () => ({ mode: "review" }),
  notFound: () => notFound(),
}));

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

const profiles = { profiles: [{ language_code: "de", is_active: true }] };

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
});

describe("revisão lexical V2", () => {
  it("mostra termo, áudio separado e exemplo só depois de revelar", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path.startsWith("/api/v1/language-profiles")) return Promise.resolve(profiles);
      if (path.startsWith("/api/v1/reviews/due")) {
        return Promise.resolve([
          {
            id: "review-1",
            item_type: "vocabulary",
            reference_id: "item-1",
            next_review_at: "2026-09-23T12:00:00Z",
            payload: {
              term: "können",
              translation_pt: "poder / conseguir",
              example: "Ich kann Deutsch.",
              example_translation_pt: "Eu sei alemão.",
              review_mode: "lexical_v2",
              audio_targets: [
                { audio_target_type: "vocabulary_item", audio_text: "können" },
                { audio_target_type: "example_sentence", audio_text: "Ich kann Deutsch." },
              ],
            },
          },
        ]);
      }
      return Promise.resolve({});
    });

    render(<StudyModePage />);

    expect(await screen.findByText("können")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ouvir expressão können" })).toBeInTheDocument();
    expect(screen.queryByText("poder / conseguir")).not.toBeInTheDocument();
    expect(screen.queryByText("Ich kann Deutsch.")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Ver resposta" }));

    expect(screen.getByText("poder / conseguir")).toBeInTheDocument();
    expect(screen.getByText(/Ich kann Deutsch\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ouvir frase de exemplo" })).toBeInTheDocument();
  });

  it("conteúdo legado sem exemplo continua funcionando", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path.startsWith("/api/v1/language-profiles")) return Promise.resolve(profiles);
      if (path.startsWith("/api/v1/reviews/due")) {
        return Promise.resolve([
          {
            id: "legacy-1",
            item_type: "vocabulary",
            reference_id: "item-legacy",
            next_review_at: "2026-09-23T12:00:00Z",
            payload: { term: "house", review_mode: "legacy" },
          },
        ]);
      }
      return Promise.resolve({});
    });

    render(<StudyModePage />);

    expect(await screen.findByText("house")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ouvir frase/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ver resposta" }));
    expect(screen.getByText(/Revise este item|casa/i)).toBeInTheDocument();
    expect(screen.queryByText(/é uma forma de/)).not.toBeInTheDocument();
  });

  it("avalia com as classificações atuais", async () => {
    apiMock.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.startsWith("/api/v1/language-profiles")) return Promise.resolve(profiles);
      if (path.startsWith("/api/v1/reviews/due")) {
        return Promise.resolve([
          {
            id: "review-legacy",
            item_type: "vocabulary",
            reference_id: "item-2",
            next_review_at: "2026-09-23T12:00:00Z",
            payload: { term: "apple", translation_pt: "maçã", review_mode: "legacy" },
          },
        ]);
      }
      if (path === "/api/v1/reviews/review-legacy/answer" && options?.method === "POST") {
        return Promise.resolve({ id: "review-legacy", rating: "good" });
      }
      return Promise.resolve({});
    });

    render(<StudyModePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Ver resposta" }));
    fireEvent.click(screen.getByRole("button", { name: "Bom" }));

    await waitFor(() => {
      expect(apiMock).toHaveBeenCalledWith("/api/v1/reviews/review-legacy/answer", {
        method: "POST",
        body: { rating: "good" },
      });
    });
    expect(await screen.findByText(/Revisão concluída/)).toBeInTheDocument();
  });
});
