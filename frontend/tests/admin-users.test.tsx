import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminUsersPage from "@/app/(app)/admin/usuarios/page";
import { ApiError } from "@/lib/api";

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

const ME = { id: "admin-1", name: "Edesio", email: "prof.edesio@gmail.com", is_admin: true };
const USERS = {
  users: [
    {
      id: "admin-1",
      name: "Edesio",
      email: "prof.edesio@gmail.com",
      is_active: true,
      created_at: "2026-09-01T12:00:00+00:00",
      languages: [{ code: "la", name_pt: "Latim Eclesiástico", source: "admin", status: "active" }],
    },
    {
      id: "student-1",
      name: "Ana Costa",
      email: "ana@example.com",
      is_active: true,
      created_at: "2026-09-20T12:00:00+00:00",
      languages: [{ code: "fr", name_pt: "Francês", source: "legacy", status: "active" }],
    },
  ],
};
const CATALOG = [
  { code: "fr", name_pt: "Francês" },
  { code: "it", name_pt: "Italiano" },
];

function mockOk() {
  apiMock.mockImplementation((path: string) => {
    if (path === "/api/v1/auth/me") return Promise.resolve(ME);
    if (path === "/api/v1/admin/users") return Promise.resolve(USERS);
    if (path === "/api/v1/languages") return Promise.resolve(CATALOG);
    return Promise.resolve({});
  });
}

describe("administração de usuários", () => {
  beforeEach(() => {
    apiMock.mockReset();
    mockOk();
  });

  it("nega o acesso com a mensagem da API", async () => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/auth/me") return Promise.resolve({ ...ME, is_admin: false });
      if (path === "/api/v1/admin/users") {
        return Promise.reject(new ApiError("Acesso não autorizado.", 403, "admin_forbidden"));
      }
      return Promise.resolve(CATALOG);
    });
    render(<AdminUsersPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Acesso não autorizado.");
    expect(screen.queryByRole("button", { name: /Desativar/ })).not.toBeInTheDocument();
  });

  it("filtra por nome e e-mail", async () => {
    render(<AdminUsersPage />);
    expect(await screen.findByRole("heading", { name: "Ana Costa" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar usuário" }), {
      target: { value: "ana@" },
    });
    expect(screen.getByRole("heading", { name: "Ana Costa" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Edesio" })).not.toBeInTheDocument();
  });

  it("não oferece desativar nem apagar a própria conta", async () => {
    render(<AdminUsersPage />);
    const own = await screen.findByRole("article", { name: "prof.edesio@gmail.com" });
    expect(within(own).queryByRole("button", { name: /Desativar/ })).not.toBeInTheDocument();
    expect(within(own).queryByRole("button", { name: /Apagar/ })).not.toBeInTheDocument();
    const student = screen.getByRole("article", { name: "ana@example.com" });
    expect(within(student).getByRole("button", { name: "Desativar ana@example.com" })).toBeInTheDocument();
  });

  it("só apaga quando o e-mail digitado é o da conta", async () => {
    render(<AdminUsersPage />);
    const student = await screen.findByRole("article", { name: "ana@example.com" });
    fireEvent.click(within(student).getByRole("button", { name: "Apagar ana@example.com" }));
    const confirm = screen.getByRole("button", { name: "Apagar conta de ana@example.com" });
    expect(confirm).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox", { name: "E-mail para confirmar a exclusão" }), {
      target: { value: "ANA@example.com" },
    });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    await waitFor(() => expect(apiMock).toHaveBeenCalledWith(
      "/api/v1/admin/users/student-1",
      expect.objectContaining({
        method: "DELETE",
        body: { confirm_email: "ANA@example.com" },
      }),
    ));
  });

  it("avisa que tirar o idioma ainda não bloqueia o estudo", async () => {
    render(<AdminUsersPage />);
    const student = await screen.findByRole("article", { name: "ana@example.com" });
    expect(within(student).getByText(/estudo continua aberto/i)).toBeInTheDocument();
    fireEvent.click(within(student).getByRole("button", { name: "Tirar Francês de ana@example.com" }));
    await waitFor(() => expect(apiMock).toHaveBeenCalledWith(
      "/api/v1/admin/users/student-1/languages/fr/revoke",
      expect.objectContaining({ method: "POST" }),
    ));
  });
});
