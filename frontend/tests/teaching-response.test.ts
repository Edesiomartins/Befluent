import { describe, expect, it } from "vitest";
import { activityIsAcknowledgement } from "@/lib/teaching-response";

describe("activityIsAcknowledgement", () => {
  it.each(["presentation", "listen", "matching", "conversation_prompt"])(
    "aceita %s sem resposta",
    (type) => {
      expect(activityIsAcknowledgement({ type })).toBe(true);
    },
  );

  it("trata recognition sem item como exposição", () => {
    expect(activityIsAcknowledgement({ type: "recognition" })).toBe(true);
  });

  it("exige resposta em recognition lexical e nas escolhas objetivas", () => {
    expect(
      activityIsAcknowledgement({ type: "recognition", vocabulary_item_id: "v-1" }),
    ).toBe(false);
    expect(activityIsAcknowledgement({ type: "multiple_choice" })).toBe(false);
    expect(activityIsAcknowledgement({ type: "reverse_recognition" })).toBe(false);
    expect(activityIsAcknowledgement({ type: "lexical_production" })).toBe(false);
  });
});
