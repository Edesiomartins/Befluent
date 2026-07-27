import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OnboardingPage from "@/app/(app)/onboarding/page";

const replace = vi.fn();
const refresh = vi.fn();
const apiMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh, push: vi.fn() }),
}));

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

describe("OnboardingPage", () => {
  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
    apiMock.mockReset();
  });

  it("envia payload correto e redireciona após sucesso", async () => {
    apiMock.mockResolvedValue({
      completed: true,
      language_code: "en",
      perceived_level: "iniciante",
      goal: "Conversar com confiança",
      minutes_per_day: 20,
      skills: ["Conversação", "Compreensão auditiva"],
    });

    render(<OnboardingPage />);
    fireEvent.click(screen.getByRole("button", { name: "Criar meu plano" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/onboarding/complete", {
        method: "POST",
        body: {
          language_code: "en",
          perceived_level: "iniciante",
          goal: "Conversar com confiança",
          minutes_per_day: 20,
          skills: ["Conversação", "Compreensão auditiva"],
        },
      }),
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Plano criado com sucesso. Abrindo seu painel…",
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"), {
      timeout: 2000,
    });
    expect(refresh).toHaveBeenCalled();
  });

  it("mostra erro da API e não redireciona", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(
      new ApiError("Idioma não encontrado.", 404, "language_not_found"),
    );

    render(<OnboardingPage />);
    fireEvent.click(screen.getByRole("button", { name: "Criar meu plano" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Idioma não encontrado.");
    expect(replace).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("impede envio duplo enquanto salva", async () => {
    let resolveRequest: (value: unknown) => void = () => undefined;
    apiMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        }),
    );

    render(<OnboardingPage />);
    const button = screen.getByRole("button", { name: "Criar meu plano" });
    fireEvent.click(button);
    fireEvent.click(button);

    await waitFor(() => expect(apiMock).toHaveBeenCalledTimes(1));
    resolveRequest({ completed: true });
  });
});
