import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Header, MobileNav, Sidebar, AppShell } from "@/components/shell";

const state = vi.hoisted(() => ({ path: "/dashboard", api: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname: () => state.path, useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/api", () => ({ api: (...args: unknown[]) => state.api(...args), clearCsrfToken: vi.fn() }));

describe("estrutura editorial", () => {
  beforeEach(() => {
    state.path = "/dashboard";
    state.api.mockReset().mockResolvedValue([{ code: "fr", name_pt: "Francês", active: true }]);
  });
  it("oferece os mesmos quatro destinos principais no desktop e celular", () => {
    render(<><Sidebar /><MobileNav /></>);
    for (const name of ["Navegação principal", "Navegação móvel"]) {
      const nav = within(screen.getByRole("navigation", { name }));
      expect(nav.getAllByRole("link").map((link) => link.textContent)).toEqual(["Hoje", "Meu plano", "Praticar", "Progresso"]);
      expect(nav.getByRole("link", { name: "Hoje" })).toHaveAttribute("aria-current", "page");
    }
  });
  it("mostra idioma real e recarrega o contexto após uma troca", async () => {
    render(<Header />);
    expect(await screen.findByRole("link", { name: /Francês.*Trocar idioma/ })).toHaveAttribute("href", "/languages");
    state.api.mockResolvedValue([{ code: "ja", name_pt: "Japonês", active: true }]);
    await act(async () => window.dispatchEvent(new Event("befluent:language-changed")));
    expect(await screen.findByRole("link", { name: /Japonês.*Trocar idioma/ })).toBeInTheDocument();
    expect(screen.queryByText("Francês")).not.toBeInTheDocument();
  });
  it("não inventa idioma quando a consulta falha", async () => {
    state.api.mockRejectedValue(new Error("offline"));
    render(<Header />);
    expect(await screen.findByRole("link", { name: /Escolher idioma/ })).toBeInTheDocument();
    expect(screen.queryByText("Inglês")).not.toBeInTheDocument();
  });
  it("devolve o foco ao fechar o menu com Escape", async () => {
    render(<Header />);
    await screen.findByText("Francês");
    const trigger = screen.getByRole("button", { name: "Abrir menu" });
    trigger.focus();
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Menu" });
    expect(dialog.contains(document.activeElement)).toBe(true);
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
  it("retira navegação e tutor durante a sessão preservando a saída para o plano", () => {
    state.path = "/cronograma/dia/day-1";
    render(<AppShell tutor={<span>Tutor flutuante</span>}><h1>Sua escrita</h1></AppShell>);
    expect(screen.getByRole("heading", { name: "Sua escrita" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Voltar ao plano/ })).toHaveAttribute("href", "/cronograma");
    expect(screen.queryByRole("navigation", { name: "Navegação principal" })).not.toBeInTheDocument();
    expect(screen.queryByText("Tutor flutuante")).not.toBeInTheDocument();
  });
  it("retorna ao catálogo quando a sessão é de prática livre", () => {
    state.path = "/learn/writing";
    render(<AppShell><h1>Sua escrita</h1></AppShell>);
    expect(screen.getByRole("link", { name: /Voltar à prática/ })).toHaveAttribute("href", "/learn");
  });
  it("fecha o menu móvel quando a janela passa para desktop", async () => {
    render(<Header />);
    await screen.findByText("Francês");
    fireEvent.click(screen.getByRole("button", { name: "Abrir menu" }));
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent(window, new Event("resize"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.body.style.overflow).not.toBe("hidden");
  });
  it("mantém a navegação no seletor de objetivo", async () => {
    state.path = "/learn/objetivo";
    render(<AppShell><h1>Objetivo</h1></AppShell>);
    expect(screen.getByRole("navigation", { name: "Navegação principal" })).toBeInTheDocument();
    await screen.findByText("Francês");
  });

  it("na tela de idiomas remove sidebar, mobile nav e seletor do header", () => {
    state.path = "/languages";
    render(
      <AppShell tutor={<span>Tutor flutuante</span>}>
        <h1>Idiomas</h1>
      </AppShell>,
    );
    expect(screen.getByRole("heading", { name: "Idiomas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "BeFluent — Hoje" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("link", { name: "Seu perfil" })).toHaveAttribute("href", "/profile");
    expect(screen.queryByRole("navigation", { name: "Navegação principal" })).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Navegação móvel" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Trocar idioma/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Tutor flutuante")).not.toBeInTheDocument();
  });

  it("demais páginas continuam com o AppShell completo", async () => {
    state.path = "/dashboard";
    render(<AppShell tutor={<span>Tutor flutuante</span>}><h1>Hoje</h1></AppShell>);
    expect(screen.getByRole("navigation", { name: "Navegação principal" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Navegação móvel" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /Francês.*Trocar idioma/ })).toBeInTheDocument();
    expect(screen.getByText("Tutor flutuante")).toBeInTheDocument();
  });
});
