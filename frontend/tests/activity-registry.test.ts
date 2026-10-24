import { describe, expect, it } from "vitest";
import {
  FAMILY_BY_TYPE,
  hasDedicatedRenderer,
  resolveInteractionFamily,
} from "@/lib/activity-registry";

describe("registro de famílias de interação", () => {
  it("dá um renderizador próprio a cada tipo oficial", () => {
    for (const [type, family] of Object.entries(FAMILY_BY_TYPE)) {
      expect(resolveInteractionFamily({ type })).toBe(family);
      expect(hasDedicatedRenderer(family)).toBe(true);
    }
  });

  it("prefere a família explícita quando ela tem renderizador", () => {
    expect(
      resolveInteractionFamily({ type: "fill_gap", interaction_family: "tap_order" }),
    ).toBe("tap_order");
  });

  it("não trata família desconhecida como texto livre", () => {
    expect(resolveInteractionFamily({ type: "fill_gap", interaction_family: "unknown" })).toBe(
      "unknown",
    );
    expect(resolveInteractionFamily({ interaction_family: "invented" })).toBe("unknown");
    expect(hasDedicatedRenderer("unknown")).toBe(false);
    expect(hasDedicatedRenderer("unspecified")).toBe(false);
  });

  it("deixa o legado sem família e sem tipo conhecido como unspecified", () => {
    expect(resolveInteractionFamily({ type: "open_response" })).toBe("unspecified");
    expect(resolveInteractionFamily({})).toBe("unspecified");
  });
});
