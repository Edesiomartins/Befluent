import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Button, EmptyState, ErrorState } from "@/components/ui";
import { ApiError } from "@/lib/api";

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

  describe("cooldown de IA indisponível", () => {
    afterEach(() => {
      vi.useRealTimers();
    });

    it("desabilita o retry com contagem regressiva e reabilita ao fim do cooldown", () => {
      vi.useFakeTimers();
      const retry = vi.fn();
      const error = new ApiError(
        "O serviço de IA está temporariamente indisponível.",
        503,
        "ai_unavailable",
        true,
      );
      render(<ErrorState retry={retry} error={error} />);

      const waitingButton = screen.getByRole("button", { name: /Tentar novamente em 30s/ });
      expect(waitingButton).toBeDisabled();

      act(() => {
        vi.advanceTimersByTime(30000);
      });

      const readyButton = screen.getByRole("button", { name: "Tentar novamente" });
      expect(readyButton).not.toBeDisabled();
      fireEvent.click(readyButton);
      expect(retry).toHaveBeenCalledOnce();
    });

    it("não aplica cooldown para erros que não são de IA", () => {
      const retry = vi.fn();
      const error = new ApiError("Não foi possível salvar.", 500, "internal_error", true);
      render(<ErrorState retry={retry} error={error} />);
      expect(screen.getByRole("button", { name: "Tentar novamente" })).not.toBeDisabled();
    });
  });
});
