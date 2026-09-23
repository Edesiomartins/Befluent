import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LanguageAccessBadge, languageAccessLabel } from "@/components/language-access";

describe("LanguageAccessBadge", () => {
  it("documenta a semântica dos estados de acesso", () => {
    expect(languageAccessLabel("available")).toBe("Disponível");
    expect(languageAccessLabel("entitled")).toBe("Liberado");
    expect(languageAccessLabel("locked")).toBe("Bloqueado");
  });

  it("mostra bloqueio sem mencionar preço ou checkout", () => {
    render(<LanguageAccessBadge state="locked" />);

    expect(screen.getByText("Bloqueado")).toBeInTheDocument();
    expect(screen.queryByText(/preço|checkout|assinatura/i)).not.toBeInTheDocument();
  });
});
