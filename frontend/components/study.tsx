"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { api, apiBlob, ApiError } from "@/lib/api";
import { useCooldown } from "@/hooks/use-cooldown";
import { prepareClassicalLatinForSpeech } from "@/lib/classical-latin-speech";
import { prepareEcclesiasticalLatinForSpeech } from "@/lib/ecclesiastical-latin-speech";

/** Cooldown do circuit breaker de IA no backend (`provider_resilience.py`). */
const AI_RETRY_COOLDOWN_SECONDS = 30;

const SPEECH_LANGS: Record<string, string> = {
  en: "en-US",
  "es-ES": "es-ES",
  fr: "fr-FR",
  ja: "ja-JP",
  "zh-CN": "zh-CN",
  la: "la",
  // Modo de teste: tag BCP-47 `la`; preparação clássica é feita à parte.
  "la-classical": "la",
};

/** Voz italiana instalada (aproximação fonética para latim eclesiástico). */
function pickItalianVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  return voices.find((voice) => voice.lang.toLowerCase().startsWith("it")) ?? null;
}

export type TranscriptResult = {
  text: string;
  provider?: string | null;
  model?: string | null;
};

function pickRecorderMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "audio/webm";
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported?.(type)) return type;
  }
  return "audio/webm";
}

/**
 * TTS: Kokoro-82M via backend (`/speech/synthesize`) como voz principal;
 * se a chamada falhar, cai no SpeechSynthesis do navegador como rede de
 * segurança (nunca deixa o aluno sem áudio nenhum).
 *
 * `variant="compact"`: botão único “Ouvir” (cards de vocabulário).
 * `variant="full"` (padrão): player com status e velocidade.
 */
export function AudioPlayer({
  text = "Áudio da atividade",
  languageCode = "en",
  variant = "full",
  label = "Ouvir",
  phoneticActivity = false,
}: {
  text?: string;
  /** @deprecated Mantido por compatibilidade; sem efeito. */
  demo?: boolean;
  languageCode?: string;
  variant?: "full" | "compact";
  /** Rótulo do botão na variante compacta. */
  label?: string;
  /**
   * Atividade que avalia/ensina pronúncia: se a preparação fonética do latim
   * falhar, não reproduz o texto ortográfico bruto (evita /k/ clássico).
   */
  phoneticActivity?: boolean;
}) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [unsupported, setUnsupported] = useState(false);
  const [usingBrowserVoice, setUsingBrowserVoice] = useState(false);
  const [phoneticUnavailable, setPhoneticUnavailable] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  /** Cancela uma geração Kokoro ainda em voo ao parar, trocar de áudio, ou
   * desmontar — evita que uma resposta tardia comece a tocar depois que o
   * aluno já saiu da tela ou pediu outro áudio. */
  const abortRef = useRef<AbortController | null>(null);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Vozes do navegador podem carregar de forma assíncrona (`voiceschanged`).
  // Apenas sincroniza a lista — nunca dispara reprodução.
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const synthesis = window.speechSynthesis;
    if (typeof synthesis.getVoices !== "function") return;

    const syncVoices = () => {
      voicesRef.current = synthesis.getVoices();
    };
    syncVoices();

    if (typeof synthesis.addEventListener === "function") {
      synthesis.addEventListener("voiceschanged", syncVoices);
      return () => synthesis.removeEventListener("voiceschanged", syncVoices);
    }

    // Chrome legado: onvoiceschanged
    const previousHandler = synthesis.onvoiceschanged;
    synthesis.onvoiceschanged = syncVoices;
    return () => {
      synthesis.onvoiceschanged = previousHandler;
    };
  }, []);

  // Ao mudar o texto (próximo item do deck), interrompe o áudio atual.
  useEffect(() => {
    abortRef.current?.abort();
    audioRef.current?.pause();
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setPlaying(false);
    setLoading(false);
    setUnsupported(false);
    setUsingBrowserVoice(false);
    setPhoneticUnavailable(false);
  }, [text, languageCode]);

  function playBrowserFallback() {
    setLoading(false);
    if (
      typeof window === "undefined" ||
      !("speechSynthesis" in window) ||
      typeof SpeechSynthesisUtterance === "undefined"
    ) {
      setUnsupported(true);
      setPlaying(false);
      return;
    }

    // displayText = `text` (ortografia pedagógica). speechText só para síntese.
    const displayText = text;
    let speechText = displayText;
    let utteranceLang = SPEECH_LANGS[languageCode] ?? "en-US";
    let selectedVoice: SpeechSynthesisVoice | null = null;

    if (languageCode === "la") {
      try {
        speechText = prepareEcclesiasticalLatinForSpeech(displayText);
      } catch {
        speechText = "";
      }
      if (!speechText.trim()) {
        setUsingBrowserVoice(false);
        setPlaying(false);
        if (phoneticActivity) {
          setPhoneticUnavailable(true);
          setUnsupported(false);
        } else {
          setPhoneticUnavailable(false);
          setUnsupported(true);
        }
        return;
      }
      // Aproximação controlada: voz italiana (não latim clássico do navegador).
      utteranceLang = "it-IT";
      selectedVoice = pickItalianVoice(voicesRef.current);
      if (!selectedVoice && process.env.NODE_ENV === "development") {
        console.info(
          "[BeFluent] Nenhuma voz it-* instalada; usando lang=it-IT sem voice explícita (aproximação).",
        );
      }
    } else if (languageCode === "la-classical") {
      try {
        speechText = prepareClassicalLatinForSpeech(displayText);
      } catch {
        speechText = "";
      }
      if (!speechText.trim()) {
        setUsingBrowserVoice(false);
        setPlaying(false);
        if (phoneticActivity) {
          setPhoneticUnavailable(true);
          setUnsupported(false);
        } else {
          setPhoneticUnavailable(false);
          setUnsupported(true);
        }
        return;
      }
      // Modo de teste: speechSynthesis com lang=la; NÃO usar voz italiana eclesiástica.
      // Qualidade do áudio clássico exige validação auditiva humana — não declarar validado só porque o código roda.
      utteranceLang = "la";
      selectedVoice =
        voicesRef.current.find((voice) => voice.lang.toLowerCase().startsWith("la")) ?? null;
      if (!selectedVoice && process.env.NODE_ENV === "development") {
        console.info(
          "[BeFluent] Latim clássico em modo de teste (speechSynthesis lang=la); validação auditiva humana pendente.",
        );
      }
    }

    setPhoneticUnavailable(false);
    setUnsupported(false);
    setUsingBrowserVoice(true);
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(speechText);
    utterance.lang = utteranceLang;
    if (selectedVoice) utterance.voice = selectedVoice;
    utterance.rate = speed;
    utterance.onend = () => setPlaying(false);
    utterance.onerror = () => {
      setPlaying(false);
      setUnsupported(true);
    };
    window.speechSynthesis.speak(utterance);
    setPlaying(true);
  }

  async function play() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setUnsupported(false);
    setUsingBrowserVoice(false);
    setPhoneticUnavailable(false);
    setLoading(true);
    setPlaying(true);
    try {
      const blob = await apiBlob("/api/v1/speech/synthesize", {
        method: "POST",
        body: { text, language_code: languageCode, speed },
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
      const url = URL.createObjectURL(blob);
      objectUrlRef.current = url;
      const audio = audioRef.current;
      if (!audio) throw new Error("elemento de áudio indisponível");
      audio.src = url;
      await audio.play();
      setLoading(false);
    } catch {
      if (controller.signal.aborted) {
        setLoading(false);
        return;
      }
      playBrowserFallback();
    }
  }

  function stop() {
    abortRef.current?.abort();
    audioRef.current?.pause();
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setLoading(false);
    setPlaying(false);
  }

  const audioElement = (
    <audio
      ref={audioRef}
      className="hidden"
      onEnded={() => setPlaying(false)}
      onError={() => {
        setPlaying(false);
        setLoading(false);
        playBrowserFallback();
      }}
    />
  );

  if (variant === "compact") {
    return (
      <div className="inline-flex flex-col items-start gap-1">
        {audioElement}
        <button
          type="button"
          onClick={playing ? stop : () => void play()}
          disabled={loading || !text.trim()}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
          aria-label={playing ? "Parar áudio" : `${label}: ${text}`}
        >
          <span aria-hidden="true">{playing ? "Ⅱ" : "▶"}</span>
          {loading ? "Gerando…" : playing ? "Parar" : label}
        </button>
        {unsupported && (
          <p role="alert" className="text-xs text-danger">
            Leitura em voz alta indisponível neste navegador.
          </p>
        )}
        {phoneticUnavailable && (
          <p role="status" className="text-xs text-text-secondary">
            Áudio de pronúncia indisponível para este item.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface p-4">
      {audioElement}
      <button
        type="button"
        onClick={playing ? stop : () => void play()}
        className="grid size-11 place-items-center rounded-full bg-primary text-white"
        aria-label={playing ? "Pausar áudio" : "Reproduzir áudio"}
      >
        {playing ? "Ⅱ" : "▶"}
      </button>
      <div className="min-w-40 flex-1">
        <p className="text-sm font-medium text-text-primary" role="status">
          {loading ? "Gerando áudio…" : usingBrowserVoice ? "Voz do navegador" : "Voz do BeFluent"}
        </p>
        <p className="mt-1 text-xs text-text-secondary">
          {playing ? "Áudio em reprodução" : "Pronto para reproduzir"}
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
      {unsupported && (
        <p role="alert" className="w-full basis-full text-sm text-danger">
          Este navegador não oferece leitura em voz alta. Leia o texto na tela.
        </p>
      )}
      {phoneticUnavailable && (
        <p role="status" className="w-full basis-full text-sm text-text-secondary">
          Áudio de pronúncia indisponível para este item.
        </p>
      )}
    </div>
  );
}

export function Recorder({
  onTranscript,
  languageCode = "en",
}: {
  onTranscript?: (text: string, meta?: TranscriptResult) => void;
  languageCode?: string;
}) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [permissionError, setPermissionError] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sttError, setSttError] = useState("");
  const [providerNote, setProviderNote] = useState("");
  const [canRetry, setCanRetry] = useState(false);
  const stream = useRef<MediaStream | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const mimeType = useRef("audio/webm");

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
      mimeType.current = pickRecorderMimeType();
      const recorder = new MediaRecorder(stream.current, {
        mimeType: mimeType.current,
      });
      mediaRecorder.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.current.push(event.data);
      };
      recorder.onstop = async () => {
        const blobType = recorder.mimeType || mimeType.current || "audio/webm";
        const blob = new Blob(chunks.current, { type: blobType });
        const extension = blobType.includes("ogg") ? "ogg" : "webm";
        const form = new FormData();
        form.append("file", blob, `voice.${extension}`);
        form.append("language_code", languageCode);
        setUploading(true);
        setSttError("");
        setProviderNote("");
        setCanRetry(false);
        try {
          const result = await api<TranscriptResult>("/api/v1/speech/transcribe", {
            method: "POST",
            body: form,
          });
          const text = (result.text || "").trim();
          if (!text) {
            setSttError("A transcrição veio vazia. Tente gravar de novo ou responda por texto.");
            setCanRetry(true);
            return;
          }
          onTranscript?.(text, result);
          if (result.provider === "mock") {
            setProviderNote(
              "Transcrição em modo mock (desenvolvimento). Não é reconhecimento de fala real.",
            );
          }
        } catch (caught) {
          const message =
            caught instanceof ApiError
              ? caught.message
              : "Não foi possível transcrever o áudio. Tente de novo ou responda por texto.";
          setSttError(message);
          setCanRetry(true);
        } finally {
          setUploading(false);
        }
      };
      recorder.start();
      setPermissionError(false);
      setSttError("");
      setCanRetry(false);
      setSeconds(0);
      setRecording(true);
    } catch {
      setPermissionError(true);
    }
  }

  return (
    <div className="grid justify-items-center gap-4 rounded-xl border border-border bg-surface p-7">
      <button
        type="button"
        onClick={() => void toggle()}
        disabled={uploading}
        className={`grid size-20 place-items-center rounded-full border-4 text-sm font-bold ${
          recording
            ? "border-danger/20 bg-danger text-white"
            : "border-primary/15 bg-primary text-white"
        }`}
        aria-label={recording ? "Parar gravação" : "Iniciar gravação"}
      >
        {recording ? "Parar" : uploading ? "…" : "Gravar"}
      </button>
      <p className="font-mono text-sm">
        {Math.floor(seconds / 60)
          .toString()
          .padStart(2, "0")}
        :{(seconds % 60).toString().padStart(2, "0")}
      </p>
      <p className="text-center text-sm font-medium text-text-primary" role="status">
        {recording
          ? "Gravando — fale com naturalidade."
          : uploading
            ? "Processando áudio…"
            : "Pronto para gravar"}
      </p>
      {!recording && !uploading && (
        <p className="text-center text-sm text-text-secondary">
          Toque para começar. O áudio será processado ao finalizar.
        </p>
      )}
      {permissionError && (
        <p role="alert" className="text-center text-sm text-danger">
          Não foi possível acessar o microfone. Use a resposta por texto abaixo.
        </p>
      )}
      {sttError && (
        <div className="grid justify-items-center gap-2">
          <p role="alert" className="text-center text-sm text-danger">
            {sttError}
          </p>
          {canRetry && (
            <button
              type="button"
              className="text-sm font-semibold text-primary hover:underline"
              onClick={() => {
                setSttError("");
                setCanRetry(false);
              }}
            >
              Tentar gravar de novo
            </button>
          )}
        </div>
      )}
      {providerNote && (
        <p role="status" className="text-center text-xs text-text-secondary">
          {providerNote}
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
  model?: string | null;
  level?: string;
};

export function Chat({
  languageCode = "en",
  situation,
  opening,
  openingTranslation,
  studySessionId,
}: {
  languageCode?: string;
  situation?: string;
  opening?: string;
  openingTranslation?: string | null;
  studySessionId?: string;
}) {
  const [messages, setMessages] = useState<Message[]>(() =>
    opening
      ? [{ role: "tutor", text: opening, translation: openingTranslation }]
      : [],
  );
  const [text, setText] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serviceDown, setServiceDown] = useState(false);
  const [serviceDownAt, setServiceDownAt] = useState(0);
  const cooldownRemaining = useCooldown(AI_RETRY_COOLDOWN_SECONDS, serviceDownAt, serviceDown);
  // null = ainda não houve turno; só avisamos mock após resposta com provider=mock
  const [demoMode, setDemoMode] = useState<boolean | null>(null);
  const [correctionsOff, setCorrectionsOff] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [closing, setClosing] = useState(false);
  const [closed, setClosed] = useState(false);
  const conversationId = useRef<string | null>(null);

  const topic = situation ?? "Conversa livre";

  useEffect(() => {
    let cancelled = false;
    conversationId.current = null;
    (async () => {
      try {
        const started = await api<{ id: string }>("/api/v1/conversations", {
          method: "POST",
          body: {
            language_code: languageCode,
            topic,
            opening,
            study_session_id: studySessionId ?? undefined,
          },
        });
        if (!cancelled) conversationId.current = started.id;
      } catch {
        if (!cancelled) conversationId.current = null;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [languageCode, topic, opening, studySessionId]);

  async function endConversation() {
    if (!conversationId.current || closed) return;
    setClosing(true);
    setError(null);
    try {
      await api(`/api/v1/conversations/${conversationId.current}/complete`, {
        method: "POST",
        body: {},
      });
      setClosed(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível encerrar a conversa.",
      );
    } finally {
      setClosing(false);
    }
  }

  async function send() {
    if (!text.trim() || thinking || closing || closed || (serviceDown && cooldownRemaining > 0)) return;
    const userText = text.trim();
    setText("");
    setError(null);
    setServiceDown(false);
    setThinking(true);
    setMessages((current) => [...current, { role: "user", text: userText }]);
    try {
      if (!conversationId.current) {
        const started = await api<{ id: string }>("/api/v1/conversations", {
          method: "POST",
          body: {
            language_code: languageCode,
            topic,
            opening,
            study_session_id: studySessionId ?? undefined,
          },
        });
        conversationId.current = started.id;
      }
      const result = await api<TurnResponse>(
        `/api/v1/conversations/${conversationId.current}/messages`,
        { method: "POST", body: { text: userText } },
      );

      // Só mock explícito vira aviso de demo — falha de IA em produção vem como erro 503.
      setDemoMode(result.provider === "mock");
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
      const unavailable =
        err instanceof ApiError &&
        (err.code === "ai_unavailable" || err.status === 503);
      setServiceDown(unavailable);
      if (unavailable) setServiceDownAt(Date.now());
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível obter resposta do tutor.",
      );
      setText((current) => current || userText);
    } finally {
      setThinking(false);
    }
  }

  return (
    <div className="panel overflow-hidden">
      {demoMode === true && (
        <p className="note border-b border-border bg-surface-soft px-4 py-2">
          {correctionsOff
            ? "Prática guiada por roteiro (modo local). Sem a IA conectada, o tutor propõe frases no seu nível mas não corrige o que você escreve."
            : "Resposta em modo local (mock de desenvolvimento). Não é o tutor de IA."}
        </p>
      )}
      {serviceDown && (
        <p className="border-b border-border bg-danger/10 px-4 py-2 text-xs leading-5 text-danger">
          {cooldownRemaining > 0
            ? `Serviço de IA temporariamente indisponível. Seu histórico foi preservado — tente enviar de novo em ${cooldownRemaining}s.`
            : "Serviço de IA temporariamente indisponível. Você já pode tentar enviar de novo."}
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
                className="mt-3 border-l-2 border-primary/40 bg-surface-soft py-3 pl-4 pr-3 text-sm"
              >
                <p className="text-xs font-semibold text-text-secondary">Resposta original</p>
                <p className="mt-1 text-text-primary">
                  {correction.original ?? message.text}
                </p>
                {correction.corrected && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-primary">Sugestão</p>
                    <p className="mt-1 text-text-primary">{correction.corrected}</p>
                  </div>
                )}
                {correction.explanation && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-text-secondary">Explicação</p>
                    <p className="mt-1 leading-6 text-text-secondary">{correction.explanation}</p>
                  </div>
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
      <div className="flex flex-col gap-3 border-t border-border p-4 sm:flex-row sm:items-end">
        <div className="min-w-0 flex-1">
          <label className="mb-2 block text-sm font-semibold text-text-primary" htmlFor="chat-message">
            Sua resposta
          </label>
          <textarea
            id="chat-message"
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            placeholder="Escreva sua resposta…"
            disabled={closed}
            className="min-h-24 w-full resize-y rounded-lg border border-border bg-surface px-3 py-2.5 text-sm outline-none ring-primary focus:ring-2 disabled:opacity-60"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Button
            onClick={() => void send()}
            disabled={!text.trim() || thinking || closed || (serviceDown && cooldownRemaining > 0)}
          >
            Enviar
          </Button>
          <Button
            variant="secondary"
            loading={closing}
            disabled={closed || !conversationId.current}
            onClick={() => void endConversation()}
          >
            {closed ? "Encerrada" : "Encerrar conversa"}
          </Button>
        </div>
      </div>
    </div>
  );
}
