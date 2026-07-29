import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SettingsPage from "@/app/(app)/settings/page";

const apiMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status = 400, code?: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

describe("SettingsPage", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("carrega preferências e salva via PATCH", async () => {
    apiMock.mockImplementation((path: string, options?: { method?: string; body?: unknown }) => {
      if (path === "/api/v1/settings" && !options?.method) {
        return Promise.resolve({
          tts_speed: 1.25,
          ui_prefs: {
            translation: true,
            autoplay: false,
            save_audio: false,
            analytics: true,
            correction_mode: "end",
          },
          default_language_id: null,
        });
      }
      if (path === "/api/v1/settings" && options?.method === "PATCH") {
        return Promise.resolve({
          tts_speed: 1.25,
          ui_prefs: options.body,
          default_language_id: null,
        });
      }
      return Promise.resolve({});
    });

    render(<SettingsPage />);
    expect(await screen.findByDisplayValue("1,25× — mais rápida")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith("/api/v1/settings", {
        method: "PATCH",
        body: {
          tts_speed: 1.25,
          ui_prefs: {
            translation: true,
            autoplay: false,
            save_audio: false,
            analytics: true,
            correction_mode: "end",
          },
        },
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Preferências salvas.");
  });

  it("mostra erro da API e não finge sucesso", async () => {
    const { ApiError } = await import("@/lib/api");
    apiMock.mockImplementation((path: string, options?: { method?: string }) => {
      if (path === "/api/v1/settings" && !options?.method) {
        return Promise.resolve({
          tts_speed: 1,
          ui_prefs: {},
          default_language_id: null,
        });
      }
      return Promise.reject(new ApiError("Falha ao salvar.", 500, "server_error"));
    });

    render(<SettingsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Falha ao salvar.");
    expect(screen.queryByText("Preferências salvas.")).not.toBeInTheDocument();
  });
});
