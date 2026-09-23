import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AchievementCelebration, LanguageProgressPanel } from "@/components/language-progress-panel";
import { NoticingWhy } from "@/components/noticing-why";
import { SessionProgress } from "@/components/session-progress";

function mockMotion(reduced: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: reduced && query.includes("prefers-reduced-motion"),
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

describe("progresso visível", () => {
  beforeEach(() => {
    mockMotion(false);
  });

  it("mostra o progresso real da sessão sem número inventado", () => {
    render(
      <SessionProgress
        completed={3}
        total={5}
        percent={60}
        currentLabel="Reconhecimento"
        nextLabel="Escuta"
        justCompleted
      />,
    );
    expect(screen.getByText("3 de 5 atividades")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.getByText("Próxima: Escuta")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Progresso da sessão" })).toHaveAttribute("aria-valuenow", "60");
    expect(screen.getByText("Concluída")).toBeInTheDocument();
  });

  it("omite a barra quando a sessão não tem atividades", () => {
    const { container } = render(<SessionProgress completed={0} total={0} percent={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("mostra habilidades recebidas e não inventa progresso até o próximo CEFR", () => {
    render(
      <LanguageProgressPanel
        progress={{
          cefr: { current: "A1", next: "A2", progress_to_next_percent: null },
          milestone: { code: "A1-4", index: 4, level: "A1" },
          skills: [{ skill: "reading", label: "Leitura", percent: 70 }],
          next_milestone: { code: "A1-5", hint: "Consolide os objetivos deste nível." },
          latest_achievement: { title: "Você avançou para A1-4." },
        }}
      />,
    );
    expect(screen.getByText("A1")).toBeInTheDocument();
    expect(screen.getByText("A2")).toBeInTheDocument();
    expect(screen.getByText("A1-4")).toBeInTheDocument();
    expect(screen.getByText("Leitura")).toBeInTheDocument();
    expect(screen.getByText("70%")).toBeInTheDocument();
    expect(screen.getByText("Você avançou para A1-4.")).toBeInTheDocument();
    expect(screen.queryByText(/Progresso para/)).not.toBeInTheDocument();
    expect(screen.queryByText("Listening")).not.toBeInTheDocument();
  });

  it("respeita prefers-reduced-motion e mantém o texto", () => {
    mockMotion(true);
    render(
      <AchievementCelebration
        kind="cefr"
        title="A2"
        detail="Você alcançou o nível A2."
        onClose={() => undefined}
      />,
    );
    expect(screen.getByRole("dialog", { name: "A2" })).toBeInTheDocument();
    expect(screen.getByText("Você alcançou o nível A2.")).toBeInTheDocument();
    expect(screen.queryByTestId("confetti")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
  });

  it("explica a forma só quando o conteúdo já traz o motivo", () => {
    render(<NoticingWhy why="O verbo be fica antes do complemento." examples={["My name is Ana.", "I'm from Brazil."]} />);
    expect(screen.queryByText("O verbo be fica antes do complemento.")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Por que esta forma?" }));
    expect(screen.getByText("O verbo be fica antes do complemento.")).toBeInTheDocument();
    expect(screen.getByText("My name is Ana.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Voltar à atividade" }));
    expect(screen.queryByText("O verbo be fica antes do complemento.")).not.toBeInTheDocument();
  });
});
