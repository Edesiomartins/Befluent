import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardSkeleton } from "@/components/dashboard-skeleton";

describe("DashboardSkeleton", () => {
  it("informa o estado de carregamento", () => {
    render(<DashboardSkeleton />);
    expect(screen.getByRole("status", { name: "Carregando painel" })).toBeInTheDocument();
  });
});
