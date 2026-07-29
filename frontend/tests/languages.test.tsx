import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LanguagesPage from "@/app/(app)/languages/page";

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

describe("LanguagesPage", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("carrega catálogo e idiomas do usuário sem dados inventados", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/languages") {
        return Promise.resolve([
          { id: "1", code: "en", name_pt: "Inglês", native_name: "English" },
          { id: "2", code: "fr", name_pt: "Francês", native_name: "Français" },
        ]);
      }
      if (path === "/api/v1/languages/mine") {
        return Promise.resolve([
          {
            id: "1",
            code: "en",
            name_pt: "Inglês",
            native_name: "English",
            user_language_id: "ul1",
            active: true,
            level_estimate: "iniciante",
            current_level: "A1",
            onboarding_completed: true,
          },
        ]);
      }
      return Promise.resolve({});
    });

    render(<LanguagesPage />);
    expect(await screen.findByText("Inglês")).toBeInTheDocument();
    expect(screen.getByText("Francês")).toBeInTheDocument();
    expect(screen.getByText(/Nível A1/)).toBeInTheDocument();
    expect(screen.queryByText(/37%/)).not.toBeInTheDocument();
    expect(screen.getByText("Ativo")).toBeInTheDocument();
  });

  it("ativa idioma via API correta e mostra erro real", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockImplementation((path: string, options?: { method?: string }) => {
      if (path === "/api/v1/languages") {
        return Promise.resolve([
          { id: "1", code: "en", name_pt: "Inglês", native_name: "English" },
          { id: "2", code: "fr", name_pt: "Francês", native_name: "Français" },
        ]);
      }
      if (path === "/api/v1/languages/mine") {
        return Promise.resolve([
          {
            id: "1",
            code: "en",
            name_pt: "Inglês",
            native_name: "English",
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
  });
});
