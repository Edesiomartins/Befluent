"use client";

/**
 * Ferramenta temporária de validação auditiva humana — NÃO é fluxo de aluno.
 * Aproxima o latim eclesiástico via speechSynthesis + voz italiana (it-IT).
 * O texto ortográfico exibido permanece intacto; só o utterance usa a forma preparada.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { prepareEcclesiasticalLatinForSpeech } from "@/lib/ecclesiastical-latin-speech";

const WORDS = [
  "caelum",
  "caeli",
  "ecclesia",
  "Cecilia",
  "regina",
  "angelus",
  "gratia",
  "oratio",
  "iustitia",
  "incarnatio",
  "regnum",
  "sanctus",
  "credo",
] as const;

const PHRASES = [
  "Pater noster, qui es in caelis.",
  "Ave Maria, gratia plena.",
  "Regina caeli, laetare.",
  "Credo in unum Deum.",
] as const;

function pickItalianVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  return voices.find((v) => v.lang.toLowerCase().startsWith("it")) ?? null;
}

export default function LatinSpeechCheckPage() {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [log, setLog] = useState<string>("");
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const sync = () => {
      const list = window.speechSynthesis.getVoices();
      voicesRef.current = list;
      setVoices(list);
    };
    sync();
    window.speechSynthesis.addEventListener("voiceschanged", sync);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", sync);
  }, []);

  const italianVoices = useMemo(
    () => voices.filter((v) => v.lang.toLowerCase().startsWith("it")),
    [voices],
  );

  const speak = useCallback((displayText: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setLog("speechSynthesis indisponível neste navegador.");
      return;
    }
    const speechText = prepareEcclesiasticalLatinForSpeech(displayText);
    if (!speechText.trim()) {
      setLog("Preparação fonética vazia — não reproduzindo ortografia bruta.");
      return;
    }
    const voice = pickItalianVoice(voicesRef.current);
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(speechText);
    utterance.lang = "it-IT";
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
    setLog(
      `Exibido: «${displayText}» → speechText: «${speechText}» · lang=it-IT · voice=${
        voice ? `${voice.name} (${voice.lang})` : "(nenhuma it-* — só lang)"
      }`,
    );
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
          Ferramenta de desenvolvimento — validação auditiva
        </p>
        <h1 className="text-2xl font-semibold text-text-primary">
          Latim eclesiástico → speechSynthesis (it-IT)
        </h1>
        <p className="text-sm leading-6 text-text-secondary">
          Ouça uma palavra/frase por vez. Confirme se a aproximação italiana soa como
          eclesiástico (ex.: <em>caelum</em> ≈ “tchêlum”, não “káelum”). A voz italiana é
          aproximação controlada — não pronúncia litúrgica perfeita. Varia por SO/navegador.
        </p>
        <p className="text-sm text-text-secondary">
          Vozes italianas detectadas:{" "}
          {italianVoices.length === 0
            ? "nenhuma (o navegador usará o fallback de lang=it-IT)"
            : italianVoices.map((v) => `${v.name} [${v.lang}]`).join(", ")}
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Palavras</h2>
        <ul className="grid gap-2 sm:grid-cols-2">
          {WORDS.map((word) => (
            <li
              key={word}
              className="flex items-center justify-between gap-3 rounded-xl border border-border px-4 py-3"
            >
              <div>
                <p className="font-medium">{word}</p>
                <p className="text-xs text-text-secondary">
                  speech: {prepareEcclesiasticalLatinForSpeech(word)}
                </p>
              </div>
              <button
                type="button"
                className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
                onClick={() => speak(word)}
              >
                Ouvir
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Frases</h2>
        <ul className="grid gap-2">
          {PHRASES.map((phrase) => (
            <li
              key={phrase}
              className="flex flex-col gap-2 rounded-xl border border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="font-medium">{phrase}</p>
                <p className="text-xs text-text-secondary">
                  speech: {prepareEcclesiasticalLatinForSpeech(phrase)}
                </p>
              </div>
              <button
                type="button"
                className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
                onClick={() => speak(phrase)}
              >
                Ouvir
              </button>
            </li>
          ))}
        </ul>
      </section>

      {log && (
        <p className="rounded-lg border border-border bg-surface-muted px-4 py-3 text-xs text-text-secondary">
          {log}
        </p>
      )}
    </div>
  );
}
