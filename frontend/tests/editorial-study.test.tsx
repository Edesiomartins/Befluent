import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NativeLanguageProvider } from "@/components/native-language-context";
import { TeachingActivityBody } from "@/components/teaching-activity";

describe("experiência editorial de estudo", () => {
  it("mantém o apoio opcional recolhido até o aluno pedir ajuda", () => {
    render(
      <NativeLanguageProvider code="pt-BR">
      <TeachingActivityBody
        activity={{
          type: "open_response",
          prompt_pt: "Responda com uma frase completa.",
          prompt: "Tell us about your routine.",
          scaffold_pt: "Comece com “I usually…”.",
        }}
        response=""
        onResponse={vi.fn()}
      />
      </NativeLanguageProvider>,
    );

    const disclosure = screen.getByText("Ver ajuda").closest("details");
    expect(disclosure).not.toHaveAttribute("open");
    expect(screen.getByRole("textbox", { name: "Sua resposta" })).toBeInTheDocument();
  });
});
