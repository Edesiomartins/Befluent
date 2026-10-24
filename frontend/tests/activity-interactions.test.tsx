import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TeachingActivityBody } from "@/components/teaching-activity";
import { NativeLanguageProvider } from "@/components/native-language-context";

function renderActivity(
  activity: Parameters<typeof TeachingActivityBody>[0]["activity"],
  nativeLanguage: string | null = null,
) {
  const onResponse = vi.fn();
  render(
    <NativeLanguageProvider code={nativeLanguage}>
      <TeachingActivityBody activity={activity} response="" onResponse={onResponse} />
    </NativeLanguageProvider>,
  );
  return onResponse;
}

describe("componentes de interação", () => {
  it("ordena por toque, desfaz e recomeça sem campo livre", () => {
    const onResponse = renderActivity({
      type: "word_order",
      prompt_native: "Monte a frase.",
      tokens: ["Je", "ne", "suis", "pas"],
    });
    expect(screen.queryByRole("textbox", { name: "Sua resposta" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "suis" }));
    expect(onResponse).toHaveBeenLastCalledWith("suis");
    fireEvent.click(screen.getByRole("button", { name: "Desfazer" }));
    expect(onResponse).toHaveBeenLastCalledWith("");
    fireEvent.click(screen.getByRole("button", { name: "Je" }));
    fireEvent.click(screen.getByRole("button", { name: "Recomeçar" }));
    expect(onResponse).toHaveBeenLastCalledWith("");
    expect(screen.getByText("Monte a frase.")).toBeInTheDocument();
  });

  it("desfaz a palavra focada com backspace", () => {
    const onResponse = renderActivity({
      type: "word_order",
      tokens: ["Je", "suis"],
    });
    fireEvent.click(screen.getByRole("button", { name: "Je" }));
    fireEvent.keyDown(screen.getByLabelText("Frase em construção"), { key: "Backspace" });
    expect(onResponse).toHaveBeenLastCalledWith("");
  });

  it("não revela os pares de matching e associa esquerda depois direita", () => {
    const onResponse = renderActivity({
      type: "matching",
      pairs: [
        { term: "clé", hint_pt: "chave" },
        { term: "porte", hint_pt: "porta" },
      ],
    });
    expect(screen.queryByText("clé chave")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "clé" }));
    fireEvent.click(screen.getByRole("button", { name: "porta" }));
    expect(onResponse).toHaveBeenCalledWith("clé = porta");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("encaixa a lacuna na frase", () => {
    const onResponse = renderActivity({
      type: "fill_gap",
      prompt_pt: "Complete.",
      prompt: "Je ___ demain.",
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Sua resposta" }), {
      target: { value: "pars" },
    });
    expect(onResponse).toHaveBeenCalledWith("pars");
    expect(screen.getByText(/Je/)).toBeInTheDocument();
  });

  it("ditado oferece áudio e não mostra o transcript", () => {
    renderActivity({
      type: "dictation",
      audio_text: "Je ne suis pas d'accord.",
      show_text: false,
      prompt_native: "Escreva o que ouvir.",
    });
    expect(screen.getByRole("button", { name: "Ouvir o ditado" })).toBeInTheDocument();
    expect(screen.queryByText("Je ne suis pas d'accord.")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Sua resposta" })).toBeInTheDocument();
  });

  it("escuta não mostra o texto do áudio", () => {
    renderActivity({
      type: "listening_recognition",
      audio_text: "Bonjour Marie",
      prompt: "Bonjour Marie",
      options: ["oi", "tchau"],
      show_text: false,
    });
    expect(screen.getByRole("button", { name: "Ouvir expressão" })).toBeInTheDocument();
    expect(screen.queryByText("Bonjour Marie")).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "oi" })).toBeInTheDocument();
  });

  it("não mostra apoio em português quando a língua nativa é outra", () => {
    renderActivity(
      {
        type: "presentation",
        term: "bonjour",
        prompt_pt: "Conheça a expressão.",
        prompt_native: "Aprende la expresión.",
        translation_pt: "bom dia",
        translation: "buenos días",
      },
      "es",
    );
    expect(screen.getByText("Aprende la expresión.")).toBeInTheDocument();
    expect(screen.getByText("buenos días")).toBeInTheDocument();
    expect(screen.queryByText("Conheça a expressão.")).not.toBeInTheDocument();
    expect(screen.queryByText("bom dia")).not.toBeInTheDocument();
  });

  it("família desconhecida não abre textarea", () => {
    renderActivity({ type: "fill_gap", interaction_family: "unknown", prompt: "Je ___ ." });
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("não abre como texto livre");
  });

  it("desafio e conversa usam famílias próprias", () => {
    const { unmount } = render(
      <TeachingActivityBody
        activity={{
          type: "transfer_question",
          prompt_target: "Demandez le quai.",
          prompt_native: "Agora pergunte a plataforma.",
        }}
        response=""
        onResponse={vi.fn()}
      />,
    );
    expect(screen.getByText("Desafio")).toBeInTheDocument();
    expect(screen.getByText("Demandez le quai.")).toBeInTheDocument();
    unmount();
    render(
      <TeachingActivityBody
        activity={{
          type: "conversation_prompt",
          scenario_target: "À la gare.",
          can_do: "demander un renseignement",
          prompt_pt: "Você chegou ao hotel.",
        }}
        response=""
        onResponse={vi.fn()}
      />,
    );
    expect(screen.getByText(/À la gare/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
