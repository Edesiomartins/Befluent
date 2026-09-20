import { describe, expect, it } from "vitest";
import { prepareClassicalLatinForSpeech } from "@/lib/classical-latin-speech";

describe("prepareClassicalLatinForSpeech", () => {
  it("caelum não vira aproximação eclesiástica 'celum'", () => {
    const prepared = prepareClassicalLatinForSpeech("caelum");
    expect(prepared.toLowerCase()).not.toBe("celum");
    // aproximação clássica: c duro (k) + ditongo ae
    expect(prepared.toLowerCase()).toMatch(/k/);
  });

  it("via aproxima v consonantal com w", () => {
    const prepared = prepareClassicalLatinForSpeech("via");
    expect(prepared.toLowerCase()).toMatch(/w/);
  });

  it("preserva pontuação e não esvazia texto", () => {
    expect(prepareClassicalLatinForSpeech("Ave, Caesar.")).toMatch(/,/);
    expect(prepareClassicalLatinForSpeech("Ave, Caesar.").trim().length).toBeGreaterThan(0);
  });

  it("não aplica regras eclesiásticas de soft-c", () => {
    const prepared = prepareClassicalLatinForSpeech("Cicero");
    expect(prepared.toLowerCase()).not.toMatch(/^ch/);
  });
});
