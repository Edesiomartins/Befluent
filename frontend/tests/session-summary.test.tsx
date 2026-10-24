import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import { SessionSummary } from "@/components/activities/session-summary";

describe("resumo da sessão", () => {
  it("repete o estado do backend e não inventa domínio", () => {
    render(
      <SessionSummary
        total={8}
        completed={8}
        masteryState="needs_review"
        areas={[{ key: "vocabulary", label: "Vocabulário", completed: 2, total: 3 }]}
      />,
    );
    expect(screen.getByRole("heading", { name: "Sessão concluída" })).toBeInTheDocument();
    expect(screen.getByText("Estado: Precisa de revisão")).toBeInTheDocument();
    expect(screen.queryByText(/Dominado/)).not.toBeInTheDocument();
    expect(screen.getByText("Vocabulário")).toBeInTheDocument();
  });

  it("mostra domínio só quando o backend marcou mastered", () => {
    render(<SessionSummary total={4} completed={4} masteryState="mastered" />);
    expect(screen.getByText("Estado: Dominado")).toBeInTheDocument();
  });

  it("celebra acertos, palavras dominadas e minutos sem animar quando o movimento é reduzido", async () => {
    const view = render(
      <SessionSummary correct={7} masteredWords={3} minutes={12} masteryState="needs_review" />,
    );
    expect(screen.getByText("Acertos")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("Palavras dominadas")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Minutos")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.queryByText(/Dominado/)).not.toBeInTheDocument();
    const title = screen.getByRole("heading", { name: "Sessão concluída" });
    expect(title.className).toContain("motion-safe:animate-[session-rise_480ms_ease-out]");
    expect(title.className).toContain("motion-reduce:animate-none");
    expect(
      (await axe(view.container, { rules: { "color-contrast": { enabled: false } } })).violations,
    ).toEqual([]);
  });
});
