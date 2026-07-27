import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LoginPage from "@/app/(auth)/login/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("Login", () => {
  it("renderiza os campos e a ação de entrada", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: "Entre na sua conta" })).toBeInTheDocument();
    expect(screen.getAllByText("BeFluent").length).toBeGreaterThan(0);
    expect(screen.queryByText(/Fluentia/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Criar conta" })).toHaveAttribute("href", "/register");
  });
});
