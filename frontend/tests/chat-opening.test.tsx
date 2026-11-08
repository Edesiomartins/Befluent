import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NativeLanguageProvider } from "@/components/native-language-context";
import { Chat } from "@/components/study";

const apiMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: (...args: unknown[]) => apiMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status = 400) {
      super(message);
      this.status = status;
    }
  },
}));

const REJECTED = "Hello, let's speak English today.";

describe("abertura rejeitada", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("não exibe a abertura antes da validação nem quando o servidor a recusa", async () => {
    let resolveStart: (value: { id: string; opening_rejected: boolean }) => void = () => undefined;
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/conversations") {
        return new Promise((resolve) => {
          resolveStart = resolve;
        });
      }
      return Promise.resolve({});
    });

    render(
      <NativeLanguageProvider code="pt-BR">
        <Chat languageCode="fr" opening={REJECTED} openingTranslation="Olá." />
      </NativeLanguageProvider>,
    );

    expect(screen.queryByText(REJECTED)).not.toBeInTheDocument();
    expect(screen.queryByText("Olá.")).not.toBeInTheDocument();

    resolveStart({ id: "conv-rejected", opening_rejected: true });

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Encerrar conversa" })).toBeEnabled(),
    );
    expect(screen.queryByText(REJECTED)).not.toBeInTheDocument();
    expect(screen.queryByText("Olá.")).not.toBeInTheDocument();
  });

  it("mostra a abertura aceita só depois da resposta", async () => {
    let resolveStart: (value: { id: string; opening_rejected: boolean }) => void = () => undefined;
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/conversations") {
        return new Promise((resolve) => {
          resolveStart = resolve;
        });
      }
      if (path === "/api/v1/conversations/conv-ok/messages") {
        return Promise.resolve({ reply: "Bien reçu.", provider: "mock" });
      }
      return Promise.resolve({});
    });

    render(
      <NativeLanguageProvider code="pt-BR">
        <Chat languageCode="fr" opening="Bonjour." openingTranslation="Bom dia." />
      </NativeLanguageProvider>,
    );
    expect(screen.queryByText("Bonjour.")).not.toBeInTheDocument();

    resolveStart({ id: "conv-ok", opening_rejected: false });
    expect(await screen.findByText("Bonjour.")).toBeInTheDocument();
    expect(screen.getByText("Bom dia.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Sua resposta"), { target: { value: "Salut" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("Bien reçu.")).toBeInTheDocument();
    expect(screen.getByText("Bonjour.")).toBeInTheDocument();
    expect(screen.getByText("Salut")).toBeInTheDocument();
  });
});
