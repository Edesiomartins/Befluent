import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import { JourneyTrail } from "@/components/journey-trail";

const axeOptions = { rules: { "color-contrast": { enabled: false } } };

const steps = [
  { id: "1", title: "Semana 1", detail: "Casa", state: "done" as const },
  { id: "2", title: "Semana 2", detail: "Rua", state: "current" as const, href: "/cronograma/dia/day-2" },
  { id: "3", title: "Semana 3", detail: "Trabalho", state: "locked" as const },
];

describe("trilha do cronograma", () => {
  it("distingue concluída, atual e bloqueada e anda com o teclado", () => {
    render(<JourneyTrail steps={steps} />);
    expect(screen.getByRole("list", { name: "Trilha do cronograma" })).toBeInTheDocument();
    expect(screen.getByText("Concluída")).toBeInTheDocument();
    const current = screen.getByRole("link", { name: /Semana 2/ });
    expect(current).toHaveAttribute("aria-current", "step");
    expect(current).toHaveAttribute("href", "/cronograma/dia/day-2");
    const locked = screen.getByRole("button", { name: /Semana 3/ });
    expect(locked).toHaveAttribute("aria-disabled", "true");
    expect(locked).toHaveTextContent("Bloqueada");

    current.focus();
    fireEvent.keyDown(screen.getByRole("list", { name: "Trilha do cronograma" }), { key: "ArrowDown" });
    expect(locked).toHaveFocus();
    fireEvent.keyDown(screen.getByRole("list", { name: "Trilha do cronograma" }), { key: "ArrowUp" });
    expect(current).toHaveFocus();
  });

  it("passa na checagem automática", async () => {
    const view = render(<JourneyTrail steps={steps} />);
    expect((await axe(view.container, axeOptions)).violations).toEqual([]);
  });
});
