import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { FocusFrame, FocusSessionProvider, useFocusSession } from "@/components/focus-session";
import { AppShell } from "@/components/shell";

const axeOptions = { rules: { "color-contrast": { enabled: false } } };

vi.mock("next/navigation", () => ({
  usePathname: () => "/learn/vocabulary",
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/lib/api", () => ({ api: vi.fn().mockResolvedValue([]), clearCsrfToken: vi.fn() }));

function Activator() {
  const { setActive } = useFocusSession();
  return (
    <button type="button" onClick={() => setActive(true)}>
      Entrar na sessão
    </button>
  );
}

describe("modo foco da sessão", () => {
  it("centraliza a atividade, mede o progresso e confirma a saída", async () => {
    const onAction = vi.fn();
    const view = render(
      <FocusFrame value={2} max={12} label="Progresso da sessão" actionLabel="Verificar" onAction={onAction}>
        <p>Je suis d accord.</p>
      </FocusFrame>,
    );
    expect(screen.getByRole("progressbar", { name: "Progresso da sessão" })).toHaveAttribute("aria-valuenow", "2");
    expect(screen.getByText("Je suis d accord.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Verificar" }));
    expect(onAction).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    const dialog = screen.getByRole("dialog", { name: "Sair desta sessão?" });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continuar estudando" })).toHaveFocus();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    expect(screen.getByRole("link", { name: "Sair" })).toHaveAttribute("href", "/dashboard");
    expect((await axe(view.container, axeOptions)).violations).toEqual([]);
  });

  it("esconde menu e cabeçalho enquanto a sessão está em foco", () => {
    render(
      <FocusSessionProvider>
        <AppShell>
          <Activator />
          <h1>Atividade</h1>
        </AppShell>
      </FocusSessionProvider>,
    );
    expect(screen.getByRole("link", { name: /Voltar à prática/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Entrar na sessão" }));
    expect(screen.queryByRole("link", { name: /Voltar à prática/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Navegação principal" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Atividade" })).toBeInTheDocument();
  });
});
