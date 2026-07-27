import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RegisterPage from "@/app/(auth)/register/page";

const replace = vi.fn();
const apiMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh: vi.fn() }),
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

describe("RegisterPage", () => {
  beforeEach(() => {
    replace.mockReset();
    apiMock.mockReset();
  });

  it("renderiza os campos de cadastro", () => {
    render(<RegisterPage />);
    expect(screen.getByRole("heading", { name: "Cadastre-se no Fluentia" })).toBeInTheDocument();
    expect(screen.getByLabelText("Nome")).toBeInTheDocument();
    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirmar senha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar conta" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/login");
  });

  it("valida confirmação de senha antes do envio", async () => {
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Maria" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "maria@exemplo.com" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-forte-1" } });
    fireEvent.change(screen.getByLabelText("Confirmar senha"), { target: { value: "outra-senha" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("As senhas não coincidem.");
    expect(apiMock).not.toHaveBeenCalled();
  });

  it("envia payload correto e redireciona após sucesso", async () => {
    apiMock.mockResolvedValue({
      message: "Conta criada com sucesso.",
      user: { id: "1", email: "maria@exemplo.com", name: "Maria" },
    });
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Maria" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "maria@exemplo.com" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-forte-1" } });
    fireEvent.change(screen.getByLabelText("Confirmar senha"), {
      target: { value: "senha-forte-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }));

    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/auth/register", {
        method: "POST",
        body: {
          name: "Maria",
          email: "maria@exemplo.com",
          password: "senha-forte-1",
          password_confirmation: "senha-forte-1",
        },
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Conta criada com sucesso");
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?cadastro=ok"), {
      timeout: 2000,
    });
  });

  it("mostra erro do backend", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockRejectedValue(new ApiError("Já existe uma conta com este e-mail.", 409, "email_taken"));
    render(<RegisterPage />);
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Maria" } });
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "maria@exemplo.com" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-forte-1" } });
    fireEvent.change(screen.getByLabelText("Confirmar senha"), {
      target: { value: "senha-forte-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Criar conta" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Já existe uma conta com este e-mail.",
    );
  });
});
