import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { FeedbackSheet } from "@/components/feedback-sheet";
import type { AnswerFeedback } from "@/types/teaching";

const axeOptions = { rules: { "color-contrast": { enabled: false } } };

const wrong: AnswerFeedback = {
  is_correct: false,
  selected: "Rome",
  correct_option: "Ada",
  why_selected: "Rome não é a pessoa.",
  why_correct: "Ada chegou.",
};

const right: AnswerFeedback = {
  is_correct: true,
  selected: "Ada",
  correct_option: "Ada",
  why_correct: "O sujeito chegou.",
};

describe("painel de feedback", () => {
  it("mostra correção e explicação no painel vermelho e anuncia o resultado", () => {
    render(
      <FeedbackSheet feedback={wrong} canRetry onContinue={vi.fn()} onRetry={vi.fn()} />,
    );
    const dialog = screen.getByRole("dialog", { name: "Resposta incorreta" });
    expect(dialog.className).toContain("bg-danger/10");
    expect(dialog).toHaveTextContent("Resposta correta:");
    expect(dialog).toHaveTextContent("Ada chegou.");
    expect(dialog.querySelector("[aria-live='assertive']")).not.toBeNull();
    expect(document.activeElement).toHaveTextContent("Resposta incorreta");
  });

  it("oferece continuar e tentar de novo sem sair da atividade", () => {
    const onContinue = vi.fn();
    const onRetry = vi.fn();
    render(
      <FeedbackSheet feedback={wrong} canRetry onContinue={onContinue} onRetry={onRetry} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    fireEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(onContinue).toHaveBeenCalledOnce();
  });

  it("esconde tentar novamente quando a sessão já avançou e usa o painel verde no acerto", () => {
    render(
      <FeedbackSheet feedback={right} canRetry={false} onContinue={vi.fn()} onRetry={vi.fn()} />,
    );
    expect(screen.getByRole("dialog").className).toContain("bg-success/10");
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continuar" })).toBeInTheDocument();
  });

  it("passa na checagem automática", async () => {
    const view = render(
      <FeedbackSheet feedback={wrong} canRetry onContinue={vi.fn()} onRetry={vi.fn()} />,
    );
    expect((await axe(view.container, axeOptions)).violations).toEqual([]);
  });
});
