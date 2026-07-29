import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthGuard } from "@/components/auth-guard";

const replace = vi.fn();
const refresh = vi.fn();
const apiMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh }),
  usePathname: () => "/dashboard",
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

describe("AuthGuard", () => {
  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
    apiMock.mockReset();
  });

  it("redireciona para login em 401", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(new ApiError("Não autenticado", 401, "unauthorized"));
    render(
      <AuthGuard>
        <p>área privada</p>
      </AuthGuard>,
    );
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/login?retorno=%2Fdashboard"),
    );
    expect(screen.queryByText("área privada")).not.toBeInTheDocument();
  });

  it("não libera o app quando o backend falha", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(new ApiError("Serviço indisponível", 503, "unavailable"));
    render(
      <AuthGuard>
        <p>área privada</p>
      </AuthGuard>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Serviço indisponível");
    expect(screen.queryByText("área privada")).not.toBeInTheDocument();
    expect(screen.queryByText(/dados de demonstração/i)).not.toBeInTheDocument();
  });

  it("libera children quando autenticado e onboarding concluído", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/auth/me") return Promise.resolve({ id: "1" });
      if (path === "/api/v1/onboarding/status") return Promise.resolve({ completed: true });
      return Promise.resolve({});
    });
    render(
      <AuthGuard>
        <p>área privada</p>
      </AuthGuard>,
    );
    expect(await screen.findByText("área privada")).toBeInTheDocument();
  });
});
