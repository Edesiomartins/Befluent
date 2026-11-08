import { describe, expect, it, vi } from "vitest";
import { claimConversation, turnStillCurrent, type StartGate } from "@/lib/conversation-gate";

describe("abertura de conversa", () => {
  it("duas chamadas concorrentes abrem uma só conversa", async () => {
    const gate: StartGate = { id: null, pending: null };
    const start = vi.fn(async () => "conv-1");
    const [first, second] = await Promise.all([
      claimConversation(gate, start),
      claimConversation(gate, start),
    ]);
    expect(first).toBe("conv-1");
    expect(second).toBe("conv-1");
    expect(start).toHaveBeenCalledOnce();
  });

  it("descarta a resposta quando a conversa ativa já mudou", () => {
    expect(turnStillCurrent("conv-1", "conv-1")).toBe(true);
    expect(turnStillCurrent("conv-1", "conv-2")).toBe(false);
    expect(turnStillCurrent("conv-1", null)).toBe(false);
  });
});
