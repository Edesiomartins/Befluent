import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useLesson } from "@/hooks/use-lesson";

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

describe("useLesson", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("não solicita lição enquanto o idioma ainda é nulo", async () => {
    const { result, rerender } = renderHook(
      ({ language }: { language: string | null }) => useLesson("voice", language),
      { initialProps: { language: null as string | null } },
    );

    expect(result.current.status).toBe("loading");
    expect(apiMock).not.toHaveBeenCalled();

    apiMock.mockResolvedValue({
      mode: "voice",
      language_code: "fr",
      title: "Conversação · FR",
      objective: "Praticar",
      level: "A2",
      level_source: "placement_test",
      level_is_estimated: true,
      provider: "mock",
    });
    rerender({ language: "fr" });

    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(apiMock).toHaveBeenCalledTimes(1);
    expect(apiMock).toHaveBeenCalledWith("/api/v1/lessons/generate", {
      method: "POST",
      body: { language_code: "fr", mode: "voice" },
    });
  });

  it("ignora resposta antiga de inglês quando o idioma já mudou para francês", async () => {
    let resolveEnglish: (value: unknown) => void = () => undefined;
    let resolveFrench: (value: unknown) => void = () => undefined;

    apiMock.mockImplementation((_path: string, options?: { body?: { language_code?: string } }) => {
      const code = options?.body?.language_code;
      if (code === "en") {
        return new Promise((resolve) => {
          resolveEnglish = resolve;
        });
      }
      return new Promise((resolve) => {
        resolveFrench = resolve;
      });
    });

    const { result, rerender } = renderHook(
      ({ language }: { language: string | null }) => useLesson("voice", language),
      { initialProps: { language: "en" as string | null } },
    );

    await waitFor(() => expect(apiMock).toHaveBeenCalledTimes(1));

    rerender({ language: "fr" });
    await waitFor(() => expect(apiMock).toHaveBeenCalledTimes(2));

    await act(async () => {
      resolveFrench({
        mode: "voice",
        language_code: "fr",
        title: "Bonjour",
        objective: "Parler",
        level: "A2",
        level_source: "placement_test",
        level_is_estimated: true,
        provider: "mock",
      });
    });
    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(result.current.lesson?.language_code).toBe("fr");

    await act(async () => {
      resolveEnglish({
        mode: "voice",
        language_code: "en",
        title: "Hello",
        objective: "Speak",
        level: "A2",
        level_source: "placement_test",
        level_is_estimated: true,
        provider: "mock",
      });
    });

    expect(result.current.lesson?.language_code).toBe("fr");
    expect(result.current.lesson?.title).toBe("Bonjour");
  });

  it("aceita inglês quando esse é o idioma resolvido", async () => {
    apiMock.mockResolvedValue({
      mode: "grammar",
      language_code: "en",
      title: "Grammar",
      objective: "Practice",
      level: "A1",
      level_source: "pending",
      level_is_estimated: false,
      provider: "mock",
    });

    const { result } = renderHook(() => useLesson("grammar", "en"));
    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(apiMock).toHaveBeenCalledWith("/api/v1/lessons/generate", {
      method: "POST",
      body: { language_code: "en", mode: "grammar" },
    });
  });
});
