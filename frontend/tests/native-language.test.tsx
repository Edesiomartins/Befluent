import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OnboardingPage from "@/app/(app)/onboarding/page";
import ProfilePage from "@/app/(app)/profile/page";
import { NativeLanguageGate } from "@/components/native-language-gate";
import { resetNativeLanguageMemory } from "@/lib/native-language";

const replace = vi.fn();
const refresh = vi.fn();
const apiMock = vi.fn();
let pathname = "/dashboard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh, push: vi.fn() }),
  usePathname: () => pathname,
  useSearchParams: () => ({ get: () => null }),
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

const languageCatalog = [
  { code: "en", native_name: "English" },
  { code: "es-ES", native_name: "Español" },
  { code: "fr", native_name: "Français" },
  { code: "de", native_name: "Deutsch" },
];

const meWithoutNative = {
  native_language: null,
  native_language_required: true,
  native_language_options: ["pt-BR", "en", "es-ES", "fr", "de"],
};

describe("língua nativa", () => {
  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
    apiMock.mockReset();
    pathname = "/dashboard";
    resetNativeLanguageMemory();
  });

  it("pede a língua nativa no onboarding quando o contrato já a declara vazia", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/auth/me") return Promise.resolve(meWithoutNative);
      if (path === "/api/v1/languages") return Promise.resolve(languageCatalog);
      return Promise.resolve({ curriculum_day_href: "/cronograma" });
    });

    render(<OnboardingPage />);

    expect(await screen.findByRole("heading", { name: "Qual é sua língua nativa?" })).toBeInTheDocument();
    expect(screen.getByText(/apenas para explicações e traduções de apoio/i)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Português (Brasil)" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "pt-BR" })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Língua nativa"), { target: { value: "pt-BR" } });
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByRole("heading", { name: "Qual idioma você quer estudar?" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    fireEvent.click(screen.getByRole("radio", { name: /Fazer o teste depois/ }));
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByText("Português (Brasil)")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Criar meu plano" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/onboarding/complete", {
        method: "POST",
        body: expect.objectContaining({
          language_code: "en",
          native_language: "pt-BR",
        }),
      }),
    );
  });

  it("pede a escolha a um usuário legado antes da jornada e libera perfil e admin", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/auth/me") return Promise.resolve(meWithoutNative);
      if (path === "/api/v1/languages") return Promise.resolve(languageCatalog);
      return Promise.resolve({});
    });

    const { rerender } = render(
      <NativeLanguageGate>
        <p>missão do dia</p>
      </NativeLanguageGate>,
    );
    expect(await screen.findByRole("heading", { name: "Qual é sua língua nativa?" })).toBeInTheDocument();
    expect(screen.queryByText("missão do dia")).not.toBeInTheDocument();

    pathname = "/profile";
    rerender(
      <NativeLanguageGate>
        <p>página de perfil</p>
      </NativeLanguageGate>,
    );
    expect(await screen.findByText("página de perfil")).toBeInTheDocument();

    pathname = "/admin";
    rerender(
      <NativeLanguageGate>
        <p>administração</p>
      </NativeLanguageGate>,
    );
    expect(await screen.findByText("administração")).toBeInTheDocument();
  });

  it("não bloqueia a jornada enquanto o backend não declara native_language", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/auth/me") return Promise.resolve({ id: "1" });
      return Promise.resolve({});
    });
    render(
      <NativeLanguageGate>
        <p>missão do dia</p>
      </NativeLanguageGate>,
    );
    expect(await screen.findByText("missão do dia")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Qual é sua língua nativa?" })).not.toBeInTheDocument();
  });

  it("atualiza a língua nativa no perfil pelo nome humano", async () => {
    apiMock.mockImplementation((path: string, options?: { method?: string; body?: unknown }) => {
      if (path === "/api/v1/profile" && options?.method === "PATCH") {
        return Promise.resolve({ id: "1", email: "ana@example.com", name: "Ana" });
      }
      if (path === "/api/v1/profile") return Promise.resolve({ id: "1", email: "ana@example.com", name: "Ana" });
      if (path === "/api/v1/dashboard") return Promise.resolve({ progress: {}, active_language: null });
      if (path === "/api/v1/auth/me") {
        return Promise.resolve({
          native_language: "en",
          native_language_required: false,
          native_language_options: ["pt-BR", "en", "es-ES", "fr", "de"],
          is_admin: false,
        });
      }
      if (path === "/api/v1/languages") return Promise.resolve(languageCatalog);
      return Promise.resolve({});
    });

    render(<ProfilePage />);
    const select = await screen.findByLabelText("Qual é sua língua nativa?");
    expect(select).toHaveValue("en");
    expect(screen.getByRole("option", { name: "English" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Deutsch" })).toBeInTheDocument();
    fireEvent.change(select, { target: { value: "de" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar perfil" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/profile", {
        method: "PATCH",
        body: { name: "Ana", native_language: "de" },
      }),
    );
  });
});
