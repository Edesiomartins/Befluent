import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BilingualText } from "@/components/bilingual-text";
import { LessonObjective } from "@/components/lesson-objective";

vi.mock("@/components/study", () => ({
  AudioPlayer: ({ text }: { text: string }) => <p>audio:{text}</p>,
}));

const SPAN = "opinion, raison et concession";
const SUPPORT = "Praticar opinião, motivo e ressalva em uma situação realista.";

describe("contrato de idioma na tela", () => {
  it("separa o objetivo misturado e manda ao áudio só o trecho em francês", () => {
    render(
      <LessonObjective
        objective={SUPPORT}
        objectiveTarget={SPAN}
        targetLanguage="fr"
        nativeLanguage="pt-BR"
      />,
    );

    expect(screen.getByText(SPAN)).toHaveAttribute("lang", "fr");
    expect(screen.getByText(SUPPORT)).toHaveAttribute("lang", "pt-BR");
    expect(screen.getByText(`audio:${SPAN}`)).toBeInTheDocument();
    expect(screen.queryByText(/audio:.*Praticar/)).not.toBeInTheDocument();
    expect(screen.getByText(`audio:${SPAN}`).textContent).not.toContain("opinião");
  });

  it("não gera áudio para uma instrução que só está em português", () => {
    render(
      <LessonObjective
        objective={SUPPORT}
        targetLanguage="fr"
        nativeLanguage="pt-BR"
      />,
    );

    expect(screen.getByText(SUPPORT)).toHaveAttribute("lang", "pt-BR");
    expect(screen.queryByText(/audio:/)).not.toBeInTheDocument();
  });

  it("marca o enunciado e o apoio com lang e não lê a tradução", () => {
    render(
      <BilingualText
        target="selon moi"
        native="na minha opinião"
        targetLang="fr"
        nativeLang="pt-BR"
        audio={<p>audio:selon moi</p>}
      />,
    );

    expect(screen.getByText("selon moi")).toHaveAttribute("lang", "fr");
    expect(screen.getByText("na minha opinião")).toHaveAttribute("lang", "pt-BR");
    expect(screen.getByText("audio:selon moi").textContent).not.toContain("opinião");
  });
});
