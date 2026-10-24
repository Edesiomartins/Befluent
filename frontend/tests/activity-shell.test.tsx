import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActivityEmpty, ActivityShell } from "@/components/activities/activity-shell";

describe("activity shell", () => {
  it("mostra fase pedagógica, progresso e objetivo sem repetir o enum", () => {
    render(
      <ActivityShell
        phase="practicing"
        phaseLabel="Você está praticando"
        languageLabel="Francês"
        level="B1"
        area="Conversação"
        step={3}
        total={10}
        objective="Pedir uma informação."
      >
        <p>Atividade</p>
      </ActivityShell>,
    );
    expect(screen.getByText("Prática")).toBeInTheDocument();
    expect(screen.queryByText("Você está praticando")).not.toBeInTheDocument();
    expect(screen.queryByText("practicing")).not.toBeInTheDocument();
    expect(screen.getByText("3 / 10")).toBeInTheDocument();
    expect(screen.getByText("Francês · B1 · Conversação")).toBeInTheDocument();
    expect(screen.getByText("Pedir uma informação.")).toBeInTheDocument();
  });

  it("declara o estado vazio", () => {
    render(<ActivityEmpty />);
    expect(screen.getByRole("status")).toHaveTextContent("Nenhuma atividade neste momento.");
  });
});
