"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

const SPEECH_LANGS: Record<string, string> = {
  en: "en-US",
  "es-ES": "es-ES",
  fr: "fr-FR",
  ja: "ja-JP",
  "zh-CN": "zh-CN",
};

export function AudioPlayer({
  text = "Áudio da atividade",
  demo = true,
  languageCode = "en",
}: {
  text?: string;
  demo?: boolean;
  languageCode?: string;
}) {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  function play() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = SPEECH_LANGS[languageCode] ?? "en-US";
      utterance.rate = speed;
      utterance.onend = () => setPlaying(false);
      window.speechSynthesis.speak(utterance);
      setPlaying(true);
    }
  }
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface p-4">
      <button
        onClick={
          playing
            ? () => {
                window.speechSynthesis.cancel();
                setPlaying(false);
              }
            : play
        }
        className="grid size-11 place-items-center rounded-full bg-primary text-white"
        aria-label={playing ? "Pausar áudio" : "Reproduzir áudio"}
      >
        {playing ? "Ⅱ" : "▶"}
      </button>
      <div className="min-w-40 flex-1">
        <div className="h-1.5 rounded-full bg-surface-elevated">
          <div className="h-full w-1/3 rounded-full bg-primary" />
        </div>
        <p className="mt-2 text-xs text-text-secondary">
          {demo ? "Síntese local de demonstração" : "Áudio da atividade"}
        </p>
      </div>
      <label className="text-xs text-text-secondary">
        Velocidade{" "}
        <select
          className="ml-1 rounded-md border border-border bg-surface p-1.5"
          value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
        >
          <option value=".75">0,75×</option>
          <option value="1">1×</option>
          <option value="1.25">1,25×</option>
        </select>
      </label>
    </div>
  );
}

export function Recorder({ onTranscript }: { onTranscript?: (text: string) => void }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [permissionError, setPermissionError] = useState(false);
  const [uploading, setUploading] = useState(false);
  const stream = useRef<MediaStream | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [recording]);

  async function toggle() {
    if (recording) {
      mediaRecorder.current?.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
      setRecording(false);
      return;
    }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const recorder = new MediaRecorder(stream.current);
      mediaRecorder.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.current.push(event.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(chunks.current, { type: "audio/webm" });
        const form = new FormData();
        form.append("file", blob, "voice.webm");
        form.append("language_code", "en");
        setUploading(true);
        try {
          const result = await api<{ text: string; provider: string }>(
            "/api/v1/speech/transcribe",
            { method: "POST", body: form },
          );
          onTranscript?.(result.text);
        } catch {
          onTranscript?.("I would like to practice ordering at a restaurant.");
        } finally {
          setUploading(false);
        }
      };
      recorder.start();
      setPermissionError(false);
      setSeconds(0);
      setRecording(true);
    } catch {
      setPermissionError(true);
    }
  }

  return (
    <div className="grid justify-items-center gap-4 rounded-xl border border-border bg-surface p-7">
      <button
        onClick={toggle}
        disabled={uploading}
        className={`grid size-20 place-items-center rounded-full border-4 text-sm font-bold ${
          recording
            ? "border-danger/20 bg-danger text-white"
            : "border-primary/15 bg-primary text-white"
        }`}
        aria-label={recording ? "Parar gravação" : "Iniciar gravação"}
      >
        {recording ? "PARAR" : uploading ? "..." : "GRAVAR"}
      </button>
      <p className="font-mono text-sm">
        {Math.floor(seconds / 60)
          .toString()
          .padStart(2, "0")}
        :{(seconds % 60).toString().padStart(2, "0")}
      </p>
      <p className="text-center text-sm text-text-secondary">
        {recording
          ? "Gravando… fale com naturalidade."
          : uploading
            ? "Enviando áudio para transcrição…"
            : "Toque para começar. O áudio será processado ao finalizar."}
      </p>
      {permissionError && (
        <p role="alert" className="text-center text-sm text-danger">
          Não foi possível acessar o microfone. Use a resposta por texto abaixo.
        </p>
      )}
    </div>
  );
}

type Correction = { original?: string; corrected?: string; explanation?: string };

type Message = {
  role: "tutor" | "user";
  text: string;
  translation?: string | null;
  corrections?: Correction[];
};

type TurnResponse = {
  reply: string;
  reply_translation?: string | null;
  corrections?: Correction[];
  natural_alternative?: string | null;
  suggestions?: string[];
  corrections_available?: boolean;
  provider?: string;
  level?: string;
};

export function Chat({
  languageCode = "en",
  situation,
  opening,
  openingTranslation,
}: {
  languageCode?: string;
  situation?: string;
  opening?: string;
  openingTranslation?: string | null;
}) {
  const [messages, setMessages] = useState<Message[]>(() =>
    opening
      ? [{ role: "tutor", text: opening, translation: openingTranslation }]
      : [],
  );
  const [text, setText] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demoMode, setDemoMode] = useState(true);
  const [correctionsOff, setCorrectionsOff] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const conversationId = useRef<string | null>(null);

  const topic = situation ?? "Conversa livre";

  useEffect(() => {
    let cancelled = false;
    conversationId.current = null;
    (async () => {
      try {
        const started = await api<{ id: string }>("/api/v1/conversations", {
          method: "POST",
          body: { language_code: languageCode, topic },
        });
        if (!cancelled) conversationId.current = started.id;
      } catch {
        if (!cancelled) conversationId.current = null;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [languageCode, topic]);

  async function send() {
    if (!text.trim()) return;
    const userText = text.trim();
    setText("");
    setError(null);
    setThinking(true);
    setMessages((current) => [...current, { role: "user", text: userText }]);
    try {
      if (!conversationId.current) {
        const started = await api<{ id: string }>("/api/v1/conversations", {
          method: "POST",
          body: { language_code: languageCode, topic },
        });
        conversationId.current = started.id;
      }
      const result = await api<TurnResponse>(
        `/api/v1/conversations/${conversationId.current}/messages`,
        { method: "POST", body: { text: userText } },
      );

      setDemoMode(result.provider !== "openrouter");
      setCorrectionsOff(result.corrections_available === false);
      setSuggestions(result.suggestions ?? []);

      const corrections = result.corrections ?? [];
      setMessages((current) => {
        const next = [...current];
        if (corrections.length) {
          for (let index = next.length - 1; index >= 0; index -= 1) {
            if (next[index].role === "user") {
              next[index] = { ...next[index], corrections };
              break;
            }
          }
        }
        next.push({
          role: "tutor",
          text: result.reply,
          translation: result.reply_translation,
        });
        return next;
      });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível obter resposta do tutor.",
      );
    } finally {
      setThinking(false);
    }
  }

  return (
    <div className="panel overflow-hidden">
      {demoMode && (
        <p className="border-b border-border bg-warning/10 px-4 py-2 text-xs leading-5 text-warning">
          {correctionsOff
            ? "Prática guiada por roteiro. Sem a IA conectada, o tutor propõe frases no seu nível mas não corrige o que você escreve."
            : "Modo demonstração de IA (mock) quando não há chave OpenRouter."}
        </p>
      )}
      <div className="min-h-80 space-y-5 p-5 sm:p-6" aria-live="polite">
        {messages.map((message, index) => (
          <div
            key={index}
            className={message.role === "user" ? "ml-auto max-w-[85%]" : "max-w-[85%]"}
          >
            <p className="mb-1 text-xs font-semibold text-text-secondary">
              {message.role === "user" ? "Você" : "Tutor"}
            </p>
            <div
              className={`rounded-xl p-3.5 text-sm leading-6 ${
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
            {message.corrections?.map((correction, position) => (
              <div
                key={position}
                className="mt-2 border-l-2 border-warning pl-3 text-sm text-text-secondary"
              >
                {correction.corrected && (
                  <p>
                    <strong className="text-text-primary">Mais natural:</strong>{" "}
                    {correction.corrected}
                  </p>
                )}
                {correction.explanation && (
                  <p className="mt-0.5">{correction.explanation}</p>
                )}
              </div>
            ))}
          </div>
        ))}
        {thinking && <p className="text-sm text-text-secondary">O tutor está respondendo…</p>}
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
      </div>
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 border-t border-border px-3 pt-3">
          <span className="text-xs font-medium text-text-secondary">Tente usar:</span>
          {suggestions.map((item) => (
            <span
              key={item}
              className="rounded-full bg-surface-elevated px-2.5 py-0.5 text-xs font-medium"
            >
              {item}
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2 border-t border-border p-3">
        <label className="sr-only" htmlFor="chat-message">
          Sua resposta
        </label>
        <textarea
          id="chat-message"
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          placeholder="Escreva sua resposta…"
          className="min-h-12 flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2.5 text-sm"
        />
        <Button onClick={() => void send()} disabled={!text.trim() || thinking}>
          Enviar
        </Button>
      </div>
    </div>
  );
}
