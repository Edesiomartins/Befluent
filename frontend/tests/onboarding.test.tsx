import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OnboardingPage from "@/app/(app)/onboarding/page";

const replace = vi.fn();
const refresh = vi.fn();
const push = vi.fn();
const apiMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh, push }),
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

/** O padrão é "Quero fazer o teste"; escolhe outra opção quando necessário. */
function selectChoice(label: string) {
  fireEvent.click(screen.getByRole("radio", { name: new RegExp(label) }));
}

describe("OnboardingPage — decisão de nível", () => {
  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
    push.mockReset();
    apiMock.mockReset();
  });

  it("oferece as quatro opções de nível", () => {
    render(<OnboardingPage />);
    expect(screen.getByText("Você já sabe qual é o seu nível?")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Sou iniciante absoluto/ })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Quero fazer o teste de nível/ })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Prefiro informar meu nível/ })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Fazer o teste depois/ })).toBeInTheDocument();
  });

  it("iniciante absoluto envia PRE_A1 e vai ao cronograma", async () => {
    apiMock.mockResolvedValue({ completed: true });

    render(<OnboardingPage />);
    selectChoice("Sou iniciante absoluto");
    fireEvent.click(screen.getByRole("button", { name: "Criar meu plano" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/onboarding/complete", {
        method: "POST",
        body: {
          language_code: "en",
          level_choice: "beginner",
          cefr_level: null,
          goal: "Conversar com confiança",
          minutes_per_day: 20,
          skills: ["Conversação", "Compreensão auditiva"],
        },
      }),
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/cronograma"), { timeout: 2000 });
  });

  it("nível declarado exibe seletor CEFR e envia o código escolhido", async () => {
    apiMock.mockResolvedValue({ completed: true });

    render(<OnboardingPage />);
    selectChoice("Prefiro informar meu nível");

    const select = screen.getByLabelText(/Qual é o seu nível/);
    fireEvent.change(select, { target: { value: "B1" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar meu plano" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/onboarding/complete",
        expect.objectContaining({
          body: expect.objectContaining({ level_choice: "self_declared", cefr_level: "B1" }),
        }),
      ),
    );
  });

  it("escolher o teste cria a sessão e navega para o teste", async () => {
    apiMock
      .mockResolvedValueOnce({ completed: true, should_take_test: true })
      .mockResolvedValueOnce({ id: "test-123" });

    render(<OnboardingPage />);
    fireEvent.click(screen.getByRole("button", { name: "Criar plano e iniciar teste" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/placement-tests", {
        method: "POST",
        body: { language_code: "en", declared_beginner: false },
      }),
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/placement-test/test-123"));
  });

  it("fazer depois conclui sem nível confirmado", async () => {
    apiMock.mockResolvedValue({ completed: true });

    render(<OnboardingPage />);
    selectChoice("Fazer o teste depois");
    fireEvent.click(screen.getByRole("button", { name: "Criar meu plano" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/onboarding/complete",
        expect.objectContaining({
          body: expect.objectContaining({ level_choice: "later", cefr_level: null }),
        }),
      ),
    );
    expect(apiMock).toHaveBeenCalledTimes(1);
  });

  it("mostra erro real da API e não redireciona", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(new ApiError("Idioma não encontrado.", 404, "language_not_found"));

    render(<OnboardingPage />);
    selectChoice("Fazer o teste depois");
    fireEvent.click(screen.getByRole("button", { name: "Criar meu plano" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Idioma não encontrado.");
    expect(replace).not.toHaveBeenCalled();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("falha ao criar o teste não redireciona silenciosamente ao dashboard", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock
      .mockResolvedValueOnce({ completed: true })
      .mockRejectedValueOnce(new ApiError("Falha ao criar teste.", 500));

    render(<OnboardingPage />);
    fireEvent.click(screen.getByRole("button", { name: "Criar plano e iniciar teste" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Falha ao criar teste.");
    expect(replace).not.toHaveBeenCalledWith("/dashboard");
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
    selectChoice("Fazer o teste depois");
    const button = screen.getByRole("button", { name: "Criar meu plano" });
    fireEvent.click(button);
    fireEvent.click(button);

    await waitFor(() => expect(apiMock).toHaveBeenCalledTimes(1));
    resolveRequest({ completed: true });
  });
});
