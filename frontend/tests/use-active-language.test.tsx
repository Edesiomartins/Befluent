import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useActiveLanguage } from "@/hooks/use-active-language";

const apiMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
}));

describe("useActiveLanguage", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("mantem perfil bloqueado explicito sem cair para ingles", async () => {
    apiMock.mockResolvedValue({
      profiles: [{ language_code: "fr", is_active: true, access_state: "locked" }],
    });

    const { result } = renderHook(() => useActiveLanguage());

    await waitFor(() => expect(result.current.resolved).toBe(true));
    expect(result.current.code).toBe("fr");
    expect(result.current.accessState).toBe("locked");
  });
});
