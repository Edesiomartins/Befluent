import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LanguagesPage from "@/app/(app)/languages/page";

const apiMock = vi.fn();
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), refresh: vi.fn() }),
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

function catalogHandlers(overrides?: {
  mine?: unknown[];
  activate?: (code: string) => unknown;
}) {
  return (path: string, options?: { method?: string; body?: { code?: string } }) => {
    if (path === "/api/v1/languages") {
      return Promise.resolve([
        {
          id: "1",
          code: "en",
          name_pt: "Inglês",
          native_name: "English",
          access_state: "available",
        },
        {
          id: "2",
          code: "fr",
          name_pt: "Francês",
          native_name: "Français",
          access_state: "available",
        },
        {
          id: "3",
          code: "de",
          name_pt: "Alemão",
          native_name: "Deutsch",
          access_state: "locked",
        },
      ]);
    }
    if (path === "/api/v1/languages/mine") {
      return Promise.resolve(
        overrides?.mine ?? [
          {
            id: "1",
            code: "en",
            name_pt: "Inglês",
            native_name: "English",
            access_state: "available",
            user_language_id: "ul1",
            active: true,
            level_estimate: "iniciante",
            current_level: "A1",
            onboarding_completed: true,
          },
        ],
      );
    }
    if (path === "/api/v1/languages/activate" && options?.method === "POST") {
      const code = options.body?.code ?? "fr";
      if (overrides?.activate) {
        return Promise.resolve(overrides.activate(code));
      }
      return Promise.resolve({
        code,
        active: true,
        user_language_id: "ul-new",
        onboarding_completed: true,
      });
    }
    return Promise.resolve({});
  };
}

describe("LanguagesPage", () => {
  beforeEach(() => {
    apiMock.mockReset();
    replace.mockReset();
  });

  it("carrega catálogo e idiomas do usuário sem dados inventados", async () => {
    apiMock.mockImplementation(catalogHandlers());

    render(<LanguagesPage />);
    expect(await screen.findByText("Inglês")).toBeInTheDocument();
    expect(screen.getByText("Francês")).toBeInTheDocument();
    expect(screen.getByText(/Nível A1/)).toBeInTheDocument();
    expect(screen.queryByText(/37%/)).not.toBeInTheDocument();
    expect(screen.getByText("Ativo")).toBeInTheDocument();
    expect(screen.getAllByText("Disponível").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Voltar para Hoje" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
  });

  it("idioma com onboarding concluído redireciona para o dashboard", async () => {
    const changed = vi.fn();
    window.addEventListener("befluent:language-changed", changed);
    apiMock.mockImplementation(
      catalogHandlers({
        activate: (code) => ({
          code,
          active: true,
          user_language_id: "ul-fr",
          onboarding_completed: true,
        }),
      }),
    );

    render(<LanguagesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Estudar este idioma" }));

    await waitFor(() => expect(changed).toHaveBeenCalledTimes(1));
    expect(apiMock).toHaveBeenCalledWith("/api/v1/languages/activate", {
      method: "POST",
      body: { code: "fr" },
    });
    expect(replace).toHaveBeenCalledWith("/dashboard");
    expect(
      apiMock.mock.calls.filter(([path]) => path === "/api/v1/languages/mine"),
    ).toHaveLength(1);
    window.removeEventListener("befluent:language-changed", changed);
  });

  it("idioma sem onboarding redireciona para o onboarding", async () => {
    const changed = vi.fn();
    window.addEventListener("befluent:language-changed", changed);
    apiMock.mockImplementation(
      catalogHandlers({
        activate: (code) => ({
          code,
          active: true,
          user_language_id: "ul-it",
          onboarding_completed: false,
        }),
      }),
    );

    render(<LanguagesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Estudar este idioma" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/onboarding"));
    expect(changed).toHaveBeenCalledTimes(1);
    window.removeEventListener("befluent:language-changed", changed);
  });

  it("ativa idioma via API correta e mostra erro real", async () => {
    const { ApiError } = await import("@/lib/api");
    const changed = vi.fn();
    window.addEventListener("befluent:language-changed", changed);
    apiMock.mockImplementation((path: string, options?: { method?: string }) => {
      if (path === "/api/v1/languages") {
        return Promise.resolve([
          { id: "1", code: "en", name_pt: "Inglês", native_name: "English", access_state: "available" },
          { id: "2", code: "fr", name_pt: "Francês", native_name: "Français", access_state: "available" },
        ]);
      }
      if (path === "/api/v1/languages/mine") {
        return Promise.resolve([
          {
            id: "1",
            code: "en",
            name_pt: "Inglês",
            native_name: "English",
            access_state: "available",
            user_language_id: "ul1",
            active: true,
            level_estimate: null,
            current_level: null,
            onboarding_completed: true,
          },
        ]);
      }
      if (path === "/api/v1/languages/activate" && options?.method === "POST") {
        return Promise.reject(new ApiError("Idioma não encontrado.", 404, "language_not_found"));
      }
      return Promise.resolve({});
    });

    render(<LanguagesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Estudar este idioma" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Idioma não encontrado.");
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/languages/activate", {
        method: "POST",
        body: { code: "fr" },
      }),
    );
    expect(changed).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Idiomas" })).toBeInTheDocument();
    window.removeEventListener("befluent:language-changed", changed);
  });

  it("idioma bloqueado não chama activate nem redireciona", async () => {
    const changed = vi.fn();
    window.addEventListener("befluent:language-changed", changed);
    apiMock.mockImplementation(catalogHandlers());

    render(<LanguagesPage />);
    const locked = await screen.findByRole("button", { name: "Idioma bloqueado" });
    expect(locked).toBeDisabled();
    fireEvent.click(locked);

    expect(apiMock).not.toHaveBeenCalledWith(
      "/api/v1/languages/activate",
      expect.anything(),
    );
    expect(changed).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByText("Bloqueado")).toBeInTheDocument();
    window.removeEventListener("befluent:language-changed", changed);
  });
});
