import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { PlacementSpeaking } from "@/components/placement-speaking";

const apiMock = vi.fn();
const trackStop = vi.fn();
const getUserMedia = vi.fn();
vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: class extends Error {},
}));

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.mockResolvedValue({ accepted: true });
  getUserMedia.mockResolvedValue({ getTracks: () => [{ stop: trackStop }] });
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: { getUserMedia } });
  class Recorder {
    state = "inactive";
    mimeType = "audio/webm";
    ondataavailable: ((event: { data: Blob }) => void) | null = null;
    onstop: (() => void) | null = null;
    static isTypeSupported() { return true; }
    start() { this.state = "recording"; }
    stop() {
      this.state = "inactive";
      this.ondataavailable?.({ data: new Blob(["recorded speech"], { type: this.mimeType }) });
      this.onstop?.();
    }
  }
  vi.stubGlobal("MediaRecorder", Recorder);
});

it("sends recorded audio as multipart and releases the microphone", async () => {
  const onComplete = vi.fn().mockResolvedValue(undefined);
  render(<PlacementSpeaking testId="test" itemId="spoken-task" onComplete={onComplete} />);
  expect(getUserMedia).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Gravar resposta" }));
  fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));
  expect(trackStop).toHaveBeenCalled();
  fireEvent.click(await screen.findByRole("button", { name: "Enviar gravação" }));
  await waitFor(() => expect(onComplete).toHaveBeenCalledOnce());
  const [path, options] = apiMock.mock.calls[0];
  expect(path).toBe("/api/v1/placement-tests/test/speaking");
  expect(options.body).toBeInstanceOf(FormData);
  expect(options.body.get("item_id")).toBe("spoken-task");
  expect(options.body.get("file").size).toBeGreaterThan(0);
});

it("allows skipping after permission denial without sending a transcript", async () => {
  getUserMedia.mockRejectedValue(new Error("permission denied"));
  render(<PlacementSpeaking testId="test" itemId="task" onComplete={vi.fn().mockResolvedValue(undefined)} />);
  fireEvent.click(screen.getByRole("button", { name: "Gravar resposta" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível acessar o microfone");
  expect(apiMock).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Pular avaliação de fala" }));
  expect(screen.getByText("Pular a atividade de fala?")).toBeInTheDocument();
  expect(screen.getByText("Sem esta atividade, sua avaliação de fala ficará incompleta.")).toBeInTheDocument();
  expect(apiMock).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Pular atividade" }));
  await waitFor(() => expect(apiMock).toHaveBeenCalledOnce());
  expect(apiMock.mock.calls[0][0]).toContain("skip-production");
  expect(apiMock.mock.calls[0][1].body).toEqual({ item_id: "task", text: "skip", reason: "microphone_unavailable" });
  expect(screen.queryByText(/A1|PRE_A1|Pré-A1/)).not.toBeInTheDocument();
});

it("confirms intent before skipping and lets the learner continue with speaking", async () => {
  const onComplete = vi.fn().mockResolvedValue(undefined);
  render(<PlacementSpeaking testId="test" itemId="task" onComplete={onComplete} />);
  fireEvent.click(screen.getByRole("button", { name: "Pular avaliação de fala" }));
  fireEvent.click(screen.getByRole("button", { name: "Continuar com a fala" }));
  expect(screen.queryByText("Pular a atividade de fala?")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Gravar resposta" })).toBeInTheDocument();
  expect(apiMock).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Pular avaliação de fala" }));
  fireEvent.click(screen.getByRole("button", { name: "Pular atividade" }));
  await waitFor(() => expect(onComplete).toHaveBeenCalledOnce());
  expect(apiMock.mock.calls[0][1].body).toEqual({ item_id: "task", text: "skip", reason: "user_skipped" });
});

it("retries the upload after an error and keeps the recording", async () => {
  const { ApiError } = await import("@/lib/api");
  const onComplete = vi.fn().mockResolvedValue(undefined);
  apiMock.mockRejectedValueOnce(new ApiError("Falha no envio.", 500));
  render(<PlacementSpeaking testId="test" itemId="spoken-task" onComplete={onComplete} />);
  fireEvent.click(screen.getByRole("button", { name: "Gravar resposta" }));
  fireEvent.click(await screen.findByRole("button", { name: "Parar gravação" }));
  fireEvent.click(await screen.findByRole("button", { name: "Enviar gravação" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Falha no envio.");
  expect(onComplete).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Enviar gravação" }));
  await waitFor(() => expect(onComplete).toHaveBeenCalledOnce());
  expect(apiMock).toHaveBeenCalledTimes(2);
});

it("stops recording at 90 seconds and releases the microphone", async () => {
  const timeouts = vi.spyOn(global, "setTimeout");
  render(<PlacementSpeaking testId="test" itemId="task" onComplete={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Gravar resposta" }));
  expect(await screen.findByRole("button", { name: "Parar gravação" })).toBeInTheDocument();
  const limit = timeouts.mock.calls.find((call) => call[1] === 90_000);
  expect(limit).toBeTruthy();
  await act(async () => {
    (limit?.[0] as () => void)();
  });
  expect(screen.getByRole("button", { name: "Gravar resposta" })).toBeInTheDocument();
  expect(trackStop).toHaveBeenCalled();
  expect(screen.getByText(/pronúncia e fluência acústica não são medidas/)).toBeInTheDocument();
  timeouts.mockRestore();
});

it("unmounting during recording releases microphone tracks", async () => {
  const { unmount } = render(<PlacementSpeaking testId="test" itemId="task" onComplete={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Gravar resposta" }));
  await screen.findByRole("button", { name: "Parar gravação" });
  unmount();
  expect(trackStop).toHaveBeenCalled();
  expect(apiMock).not.toHaveBeenCalled();
});
