import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ObjectiveSlicePage from "@/app/(app)/learn/objetivo/page";

const { apiMock, MockApiError } = vi.hoisted(() => {
  class MockApiError extends Error {
    status: number;
    constructor(message: string, status = 400) {
      super(message);
      this.name = "ApiError";
      this.status = status;
    }
  }
  return { apiMock: vi.fn(), MockApiError };
});

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: MockApiError,
}));

const sessionPayload = {
  flow: {
    id: "flow-1",
    phase: "activating",
    phase_label_pt: "Você está aprendendo",
    status: "active",
    activity_cursor: 0,
    remediation_cycles: 0,
  },
  objective: {
    id: "obj-1",
    code: "EN-A1-CAN-001",
    title: "Apresentar-se",
    can_do: "Apresentar-se com informações básicas.",
    level: "A1",
  },
  progress_state: "learning",
  current_activity: {
    type: "recognition",
    prompt_pt: "Bem-vindo ao objetivo.",
    title_pt: "Apresentar-se",
    can_do: "Apresentar-se com informações básicas.",
  },
  activities_total: 8,
  remediation: null,
};

describe("Teaching Engine V2 slice UI", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("inicia o objetivo e mostra estado pedagógico", async () => {
    apiMock.mockImplementation(async (path: string) => {
      if (path.includes("/active")) {
        throw new MockApiError("Não há fluxo ativo", 404);
      }
      return sessionPayload;
    });

    render(<ObjectiveSlicePage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /começar objetivo/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /começar objetivo/i }));

    await waitFor(() => {
      expect(screen.getByText("Você está aprendendo")).toBeInTheDocument();
    });
    expect(screen.getByText(/EN-A1-CAN-001/i)).toBeInTheDocument();
    expect(apiMock).toHaveBeenCalledWith(
      "/api/v1/teaching/slice/en-a1-can-001/start",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("restaura flow ativo do backend no refresh", async () => {
    apiMock.mockResolvedValueOnce({
      ...sessionPayload,
      flow: {
        ...sessionPayload.flow,
        phase: "practicing",
        phase_label_pt: "Praticando",
        activity_cursor: 3,
      },
    });

    render(<ObjectiveSlicePage />);

    await waitFor(() => {
      expect(screen.getByText("Praticando")).toBeInTheDocument();
    });
    expect(apiMock).toHaveBeenCalledWith("/api/v1/teaching/slice/en-a1-can-001/active");
    expect(screen.queryByRole("button", { name: /começar objetivo/i })).not.toBeInTheDocument();
  });
});
