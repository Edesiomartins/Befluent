import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { LanguageAccent } from "@/components/language-accent";
import { LANGUAGE_ACCENTS, LANGUAGE_CODES, accentFor } from "@/lib/language-accent";

vi.mock("@/hooks/use-active-language", () => ({
  useActiveLanguage: () => ({ code: "fr", resolved: true, accessState: "available" }),
}));

function channel(hex: string, start: number) {
  return parseInt(hex.slice(start, start + 2), 16) / 255;
}

function luminance(hex: string) {
  const values = [1, 3, 5].map((start) => {
    const color = channel(hex, start);
    return color <= 0.03928 ? color / 12.92 : ((color + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
}

function contrast(ink: string, paper: string) {
  const lighter = Math.max(luminance(ink), luminance(paper));
  const darker = Math.min(luminance(ink), luminance(paper));
  return (lighter + 0.05) / (darker + 0.05);
}

describe("acento do idioma alvo", () => {
  it("dá uma tinta própria a cada idioma e passa contraste AA no branco", () => {
    const inks = new Set<string>();
    for (const code of LANGUAGE_CODES) {
      const accent = LANGUAGE_ACCENTS[code];
      inks.add(accent.ink);
      expect(contrast(accent.ink, "#ffffff")).toBeGreaterThanOrEqual(4.5);
      expect(contrast(accent.ink, accent.soft)).toBeGreaterThanOrEqual(4.5);
    }
    expect(inks.size).toBe(LANGUAGE_CODES.length);
    expect(accentFor("pt")).toEqual(LANGUAGE_ACCENTS.en);
    for (const ink of ["#2563eb", "#15803d", "#dc2626", "#9a3412"]) {
      expect(contrast(ink, "#ffffff")).toBeGreaterThanOrEqual(4.5);
      expect(contrast("#ffffff", ink)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("aplica o token do francês e anuncia a amostra", async () => {
    render(
      <>
        <LanguageAccent />
        <p style={{ color: "var(--language-accent)" }}>Francês</p>
      </>,
    );
    expect(document.documentElement.dataset.targetLanguage).toBe("fr");
    expect(document.documentElement.style.getPropertyValue("--language-accent")).toBe(
      LANGUAGE_ACCENTS.fr.ink,
    );
    const view = screen.getByText("Francês");
    expect(
      (await axe(view.parentElement ?? document.body, { rules: { "color-contrast": { enabled: false } } }))
        .violations,
    ).toEqual([]);
  });
});
