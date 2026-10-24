import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
});
