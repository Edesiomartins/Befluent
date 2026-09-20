import { describe, expect, it } from "vitest";
import { prepareEcclesiasticalLatinForSpeech } from "@/lib/ecclesiastical-latin-speech";

/**
 * RED → GREEN: preparação fonética só para speechSynthesis (latim eclesiástico).
 * O texto pedagógico exibido NÃO passa por esta função no UI.
 */
describe("prepareEcclesiasticalLatinForSpeech", () => {
  it("não devolve caelum bruto (precisa forma falável para voz italiana)", () => {
    const speech = prepareEcclesiasticalLatinForSpeech("caelum");
    expect(speech.toLowerCase()).not.toBe("caelum");
  });

  it("prepara caelum para início /tʃ/ via ortografia italiana (ce…)", () => {
    const speech = prepareEcclesiasticalLatinForSpeech("caelum");
    expect(speech.toLowerCase().startsWith("ce")).toBe(true);
  });

  it.each([
    ["caelum", "celum"],
    ["caeli", "celi"],
    ["caelis", "celis"],
    ["caelo", "celo"],
    ["ecclesia", "ekklezia"],
    ["Cecilia", "Cecilia"],
    ["regina", "regina"],
    ["angelus", "angelus"],
    ["gratia", "grazia"],
    ["oratio", "orazio"],
    ["iustitia", "iustitsia"],
    ["incarnatio", "incarnatsio"],
    ["regnum", "regno"],
    ["sanctus", "sanctus"],
    ["credo", "credo"],
  ] as const)("léxico: %s → %s", (input, expected) => {
    expect(prepareEcclesiasticalLatinForSpeech(input)).toBe(expected);
  });

  it("preserva c duro em sanctus e credo", () => {
    expect(prepareEcclesiasticalLatinForSpeech("sanctus")).toBe("sanctus");
    expect(prepareEcclesiasticalLatinForSpeech("credo")).toBe("credo");
    expect(prepareEcclesiasticalLatinForSpeech("sanctus").toLowerCase().startsWith("ce")).toBe(
      false,
    );
    expect(prepareEcclesiasticalLatinForSpeech("credo").toLowerCase().startsWith("ce")).toBe(
      false,
    );
  });

  it("preserva pontuação e espaços", () => {
    expect(prepareEcclesiasticalLatinForSpeech("caelum.")).toBe("celum.");
    expect(prepareEcclesiasticalLatinForSpeech("Ave Maria, gratia plena.")).toBe(
      "Ave Maria, grazia plena.",
    );
  });

  it("respeita capitalização sem quebrar a transformação", () => {
    expect(prepareEcclesiasticalLatinForSpeech("Caelum")).toBe("Celum");
    expect(prepareEcclesiasticalLatinForSpeech("CAELUM")).toBe("CELUM");
  });

  it("não corrompe palavras desconhecidas com regras excessivas (gloria mantém g duro)", () => {
    expect(prepareEcclesiasticalLatinForSpeech("gloria")).toBe("gloria");
  });

  it("aplica regra segura cae→ce em palavra fora do léxico", () => {
    expect(prepareEcclesiasticalLatinForSpeech("caelestis").toLowerCase()).toBe("celestis");
  });

  it("string vazia permanece vazia", () => {
    expect(prepareEcclesiasticalLatinForSpeech("")).toBe("");
    expect(prepareEcclesiasticalLatinForSpeech("   ")).toBe("   ");
  });
});
