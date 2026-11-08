import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
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

function conversationStarts() {
  return apiMock.mock.calls.filter((call) => call[0] === "/api/v1/conversations");
}

describe("Chat no StrictMode", () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it("abre uma só conversa quando o efeito roda duas vezes", async () => {
    apiMock.mockImplementation((path: string) =>
      path === "/api/v1/conversations" ? Promise.resolve({ id: "conv-1" }) : Promise.resolve({}),
    );

    render(
      <StrictMode>
        <Chat languageCode="en" opening="Hello!" />
      </StrictMode>,
    );

    await waitFor(() => expect(conversationStarts().length).toBeGreaterThan(0));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Encerrar conversa" })).toBeEnabled(),
    );
    expect(conversationStarts()).toHaveLength(1);
    expect(await screen.findByText("Hello!")).toBeInTheDocument();
  });

  it("envio enquanto a abertura ainda responde usa a mesma conversa", async () => {
    let resolveStart: (value: { id: string }) => void = () => undefined;
    apiMock.mockImplementation((path: string) => {
      if (path === "/api/v1/conversations") {
        return new Promise((resolve) => {
          resolveStart = resolve;
        });
      }
      if (path === "/api/v1/conversations/conv-1/messages") {
        return Promise.resolve({ reply: "Nice to meet you.", provider: "mock" });
      }
      return Promise.resolve({});
    });

    render(
      <StrictMode>
        <Chat languageCode="en" opening="Hello!" />
      </StrictMode>,
    );

    fireEvent.change(screen.getByLabelText("Sua resposta"), { target: { value: "Hi" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(typeof resolveStart).toBe("function"));
    resolveStart({ id: "conv-1" });

    expect(await screen.findByText("Nice to meet you.")).toBeInTheDocument();
    expect(conversationStarts()).toHaveLength(1);
    expect(apiMock).toHaveBeenCalledWith(
      "/api/v1/conversations/conv-1/messages",
      expect.objectContaining({ method: "POST", body: { text: "Hi" } }),
    );
  });

  it("troca de idioma descarta a abertura anterior e abre outra conversa", async () => {
    let resolveEnglish: (value: { id: string }) => void = () => undefined;
    let resolveFrench: (value: { id: string }) => void = () => undefined;
    apiMock.mockImplementation((path: string, options?: { body?: { language_code?: string } }) => {
      if (path !== "/api/v1/conversations") return Promise.resolve({});
      const code = options?.body?.language_code;
      if (code === "fr") {
        return new Promise((resolve) => {
          resolveFrench = resolve;
        });
      }
      return new Promise((resolve) => {
        resolveEnglish = resolve;
      });
    });

    const { rerender } = render(
      <StrictMode>
        <Chat languageCode="en" opening="Hello!" />
      </StrictMode>,
    );
    await waitFor(() => expect(conversationStarts()).toHaveLength(1));

    rerender(
      <StrictMode>
        <Chat languageCode="fr" opening="Bonjour." />
      </StrictMode>,
    );
    await waitFor(() => expect(conversationStarts()).toHaveLength(2));

    resolveEnglish({ id: "conv-en" });
    resolveFrench({ id: "conv-fr" });

    expect(await screen.findByText("Bonjour.")).toBeInTheDocument();
    expect(screen.queryByText("Hello!")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Sua resposta"), { target: { value: "Salut" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/api/v1/conversations/conv-fr/messages",
        expect.objectContaining({ body: { text: "Salut" } }),
      ),
    );
    expect(apiMock.mock.calls.some((call) => call[0] === "/api/v1/conversations/conv-en/messages")).toBe(false);
  });
});
