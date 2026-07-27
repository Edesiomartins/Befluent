import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Button, EmptyState, ErrorState } from "@/components/ui";

describe("componentes de interface", () => {
  it("desabilita o botão durante o carregamento", () => {
    render(<Button loading>Salvar</Button>);
    expect(screen.getByRole("button", { name: "Salvar" })).toBeDisabled();
  });

  it("renderiza uma orientação para estado vazio", () => {
    render(<EmptyState title="Nada pendente" description="Sua fila está em dia." />);
    expect(screen.getByText("Nada pendente")).toBeInTheDocument();
    expect(screen.getByText("Sua fila está em dia.")).toBeInTheDocument();
  });

  it("permite tentar novamente após um erro", () => {
    const retry = vi.fn();
    render(<ErrorState retry={retry} />);
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
