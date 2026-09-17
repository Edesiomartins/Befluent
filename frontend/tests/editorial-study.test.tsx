import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TeachingActivityBody } from "@/components/teaching-activity";

describe("experiência editorial de estudo", () => {
  it("mantém o apoio opcional recolhido até o aluno pedir ajuda", () => {
    render(
      <TeachingActivityBody
        activity={{
          type: "open_response",
          prompt_pt: "Responda com uma frase completa.",
          prompt: "Tell us about your routine.",
          scaffold_pt: "Comece com “I usually…”.",
        }}
        response=""
        onResponse={vi.fn()}
      />,
    );

    const disclosure = screen.getByText("Ver ajuda").closest("details");
    expect(disclosure).not.toHaveAttribute("open");
    expect(screen.getByRole("textbox", { name: "Sua resposta" })).toBeInTheDocument();
  });
});
