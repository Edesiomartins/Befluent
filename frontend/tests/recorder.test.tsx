import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Recorder } from "@/components/study";

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

describe("Recorder", () => {
  beforeEach(() => {
    apiMock.mockReset();
    class FakeMediaRecorder {
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob(["audio"], { type: "audio/webm" }) });
        this.onstop?.();
      }
    }
    Object.defineProperty(globalThis, "MediaRecorder", {
      writable: true,
      value: FakeMediaRecorder,
    });
    Object.defineProperty(navigator, "mediaDevices", {
      writable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: vi.fn() }],
        }),
      },
    });
  });

  it("não inventa transcript quando a API falha", async () => {
    const { ApiError } = await import("@/lib/api");
    const onTranscript = vi.fn();
    apiMock.mockRejectedValue(new ApiError("Falha STT", 500, "stt_error"));

    render(<Recorder onTranscript={onTranscript} languageCode="ja" />);
    fireEvent.click(screen.getByRole("button", { name: "Iniciar gravação" }));
    fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Falha STT");
    expect(onTranscript).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/speech/transcribe",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    const form = apiMock.mock.calls[0][1].body as FormData;
    expect(form.get("language_code")).toBe("ja");
  });
});
