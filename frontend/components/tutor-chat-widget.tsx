"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Bot, Send, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useActiveLanguage } from "@/hooks/use-active-language";

type Correction = { original?: string; corrected?: string; explanation?: string };

type ChatMessage = {
  role: "tutor" | "user";
  text: string;
  translation?: string | null;
};

type TutorChatResponse = {
  reply: string;
  reply_translation?: string | null;
  corrections?: Correction[];
  suggestions?: string[];
  corrections_available?: boolean;
  provider?: string;
};

const GREETING: ChatMessage = {
  role: "tutor",
  text:
    "Oi! Sou o tutor de apoio. Pode me perguntar sobre gramática, vocabulário, " +
    "tradução ou qualquer dúvida sobre o idioma que você está praticando.",
};

/**
 * Chat de apoio disponível em qualquer tela autenticada — diferente das
 * lições de "Conversação", não é roteirizado nem afeta progresso/streak.
 * Histórico vive só nesta sessão do navegador (endpoint stateless).
 */
export function TutorChatWidget() {
  const { code, resolved } = useActiveLanguage();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [text, setText] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serviceDown, setServiceDown] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const panelId = useId();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  async function send() {
    if (!text.trim() || !resolved) return;
    const userText = text.trim();
    const history = messages
      .filter((message) => message !== GREETING)
      .slice(-10)
      .map((message) => ({
        role: message.role === "tutor" ? ("assistant" as const) : ("user" as const),
        content: message.text,
      }));

    setText("");
    setError(null);
    setServiceDown(false);
    setThinking(true);
    setMessages((current) => [...current, { role: "user", text: userText }]);

    try {
      const result = await api<TutorChatResponse>("/api/v1/tutor-chat", {
        method: "POST",
        body: { language_code: code, text: userText, history },
      });
      setDemoMode(result.provider === "mock");
      setMessages((current) => [
        ...current,
        { role: "tutor", text: result.reply, translation: result.reply_translation },
      ]);
    } catch (err) {
      const unavailable =
        err instanceof ApiError && (err.code === "ai_unavailable" || err.status === 503);
      setServiceDown(unavailable);
      setError(
        err instanceof ApiError ? err.message : "Não foi possível obter resposta do tutor.",
      );
    } finally {
      setThinking(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={open ? "Fechar tutor de apoio" : "Abrir tutor de apoio"}
        className="fixed bottom-20 right-4 z-40 grid size-14 place-items-center rounded-full bg-primary text-white shadow-[0_4px_0_var(--primary-shadow)] transition hover:bg-[var(--primary-hover)] lg:bottom-6 lg:right-6"
      >
        {open ? <X className="size-6" aria-hidden /> : <Bot className="size-6" aria-hidden />}
      </button>

      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-modal="false"
          aria-label="Tutor de apoio"
          className="fixed inset-x-3 bottom-36 top-auto z-40 flex max-h-[70vh] flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-xl sm:inset-x-auto sm:bottom-24 sm:right-6 sm:w-96 lg:bottom-24 lg:right-6"
        >
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <p className="text-sm font-semibold">Tutor de apoio</p>
              <p className="text-xs text-text-secondary">Dúvidas rápidas, a qualquer momento</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Fechar"
              className="rounded-lg p-1.5 text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
            >
              <X className="size-4" aria-hidden />
            </button>
          </div>

          {demoMode && (
            <p className="border-b border-border bg-warning/10 px-4 py-2 text-xs leading-5 text-warning">
              Resposta em modo local (mock de desenvolvimento). Não é o tutor de IA.
            </p>
          )}
          {serviceDown && (
            <p className="border-b border-border bg-danger/10 px-4 py-2 text-xs leading-5 text-danger">
              Serviço de IA temporariamente indisponível. Tente enviar de novo em instantes.
            </p>
          )}

          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
            {messages.map((message, index) => (
              <div
                key={index}
                className={message.role === "user" ? "ml-auto max-w-[85%]" : "max-w-[85%]"}
              >
                <p className="mb-1 text-xs font-semibold text-text-secondary">
                  {message.role === "user" ? "Você" : "Tutor"}
                </p>
                <div
                  className={`rounded-xl p-3 text-sm leading-6 ${
                    message.role === "user" ? "bg-primary text-white" : "bg-surface-elevated"
                  }`}
                >
                  {message.text}
                </div>
                {message.translation && (
                  <p className="mt-1.5 pl-1 text-sm italic text-text-secondary">
                    {message.translation}
                  </p>
                )}
              </div>
            ))}
            {thinking && <p className="text-sm text-text-secondary">O tutor está respondendo…</p>}
            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}
          </div>

          <div className="flex gap-2 border-t border-border p-3">
            <label className="sr-only" htmlFor="tutor-chat-message">
              Sua pergunta
            </label>
            <textarea
              id="tutor-chat-message"
              rows={1}
              value={text}
              onChange={(event) => setText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void send();
                }
              }}
              placeholder="Digite sua dúvida…"
              className="min-h-11 flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2.5 text-sm"
            />
            <button
              type="button"
              onClick={() => void send()}
              disabled={!text.trim() || thinking || !resolved}
              aria-label="Enviar pergunta"
              className="grid size-11 shrink-0 place-items-center rounded-lg bg-primary text-white transition hover:bg-[var(--primary-hover)] disabled:cursor-not-allowed disabled:opacity-55"
            >
              <Send className="size-4" aria-hidden />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
