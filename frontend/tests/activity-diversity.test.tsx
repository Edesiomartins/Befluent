import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TeachingActivityBody } from "@/components/teaching-activity";
import { FAMILY_BY_TYPE, hasDedicatedRenderer } from "@/lib/activity-registry";

const sequence = [
  { type: "presentation", term: "bonjour" },
  { type: "multiple_choice", prompt: "Qui ?", options: ["Ada"] },
  { type: "listening_recognition", audio_text: "oui", options: ["sim"], show_text: false },
  { type: "word_order", tokens: ["Je", "suis"] },
  { type: "fill_gap", prompt: "Je ___ ." },
  { type: "guided_production", prompt: "Répondez." },
  { type: "repeat", prompt: "Bonjour.", audio_text: "Bonjour." },
  { type: "conversation_prompt", scenario_target: "À la gare." },
  { type: "transfer_question", prompt_target: "Demandez le quai." },
];

describe("variedade visual da sessão", () => {
  it("cada tipo oficial tem renderizador próprio", () => {
    for (const family of Object.values(FAMILY_BY_TYPE)) {
      expect(hasDedicatedRenderer(family)).toBe(true);
    }
    expect(hasDedicatedRenderer("unspecified")).toBe(false);
  });

  it("a sequência pedagógica não cai na mesma interação", () => {
    const seen = new Set<string>();
    const { rerender } = render(
      <TeachingActivityBody activity={sequence[0]} response="" onResponse={vi.fn()} />,
    );
    for (const activity of sequence) {
      rerender(<TeachingActivityBody activity={activity} response="" onResponse={vi.fn()} />);
      seen.add(document.querySelector("[data-interaction-family]")?.getAttribute("data-interaction-family") ?? "");
    }
    expect(seen.size).toBe(sequence.length);
    expect(seen.has("unspecified")).toBe(false);
    expect(seen.has("")).toBe(false);
  });
});
