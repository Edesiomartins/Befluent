import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProfilePage from "@/app/(app)/profile/page";

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

const profile = { id: "1", email: "prof.edesio@gmail.com", name: "Edesio" };
const dashboard = { progress: { study_sessions: 1, total_minutes_label: "10min" }, active_language: null };

function mockSession(isAdmin: boolean) {
  apiMock.mockImplementation((path: string) => {
    if (path === "/api/v1/profile") return Promise.resolve(profile);
    if (path === "/api/v1/dashboard") return Promise.resolve(dashboard);
    if (path === "/api/v1/auth/me") return Promise.resolve({ is_admin: isAdmin });
    return Promise.resolve({});
  });
}

describe("botão de administração no perfil", () => {
  beforeEach(() => apiMock.mockReset());

  it("mostra Administrar na conta do administrador", async () => {
    mockSession(true);
    render(<ProfilePage />);
    expect(await screen.findByRole("link", { name: "Administrar" })).toHaveAttribute("href", "/admin");
  });

  it("não mostra Administrar para as outras contas", async () => {
    mockSession(false);
    render(<ProfilePage />);
    expect(await screen.findByRole("heading", { name: "Edesio" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Administrar" })).not.toBeInTheDocument();
  });
});
