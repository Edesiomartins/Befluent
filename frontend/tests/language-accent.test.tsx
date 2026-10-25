import fs from "node:fs";
import path from "node:path";
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

function mixHex(foreground: string, background: string, weight: number) {
  const parts = [1, 3, 5].map((start) => {
    const fg = parseInt(foreground.slice(start, start + 2), 16);
    const bg = parseInt(background.slice(start, start + 2), 16);
    return Math.round(fg * weight + bg * (1 - weight))
      .toString(16)
      .padStart(2, "0");
  });
  return `#${parts.join("")}`;
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

  it("usa --language-accent no brilho do .command-panel mantendo contraste AA no fundo escuro", () => {
    const css = fs.readFileSync(path.resolve(process.cwd(), "app/globals.css"), "utf8");
    const block = css.match(/\.command-panel\s*\{[^}]+\}/)?.[0] ?? "";
    expect(block).toContain("var(--language-accent)");
    expect(block).not.toContain("rgba(37, 99, 235");

    for (const code of LANGUAGE_CODES) {
      const glowSurface = mixHex(LANGUAGE_ACCENTS[code].ink, "#111c33", 0.26);
      expect(contrast("#f8fafc", glowSurface)).toBeGreaterThanOrEqual(4.5);
      expect(contrast("#cbd5e1", glowSurface)).toBeGreaterThanOrEqual(4.5);
    }
  });
});
