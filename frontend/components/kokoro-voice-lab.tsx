"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { base64ToBlob } from "@/lib/audio";
import { Button } from "@/components/ui";
import { presetsForLanguage, type PresetLength } from "@/lib/kokoro-presets";

/** Seção "Kokoro Voice Lab" dentro do TTS Lab (`/admin/tts-lab`) — compara
 * vozes do `hexgrad/kokoro-82m` por idioma, usando o mesmo texto, para
 * escolher empiricamente a melhor voz por idioma. Estado só existe em
 * memória do React (sem persistência) — ver docs/TTS_LAB.md. Não altera o
 * TTS de produção (`app/services/speech.py`), que continua com sua própria
 * voz padrão por idioma. */

type KokoroVoice = { id: string; name: string; gender: string };
type KokoroLanguage = { code: string; name: string; voices: KokoroVoice[] };
type KokoroVoicesResponse = { model: string; languages: KokoroLanguage[] };

type KokoroGenerateResult = {
  model: string;
  language: string;
  voice: string;
  audio_base64: string;
  content_type: string;
  latency_ms: number;
  audio_size_bytes: number;
};

type VoiceRunState = {
  status: "idle" | "loading" | "ok" | "error" | "timeout" | "rate_limited";
  audioUrl?: string;
  latencyMs?: number;
  audioSizeBytes?: number;
  errorMessage?: string;
};

type VoiceRating = {
  clareza: number | null;
  naturalidade: number | null;
  entonacao: number | null;
  ritmo: number | null;
  velocidade: "lenta" | "boa" | "rapida" | null;
};

const EMPTY_RATING: VoiceRating = {
  clareza: null,
  naturalidade: null,
  entonacao: null,
  ritmo: null,
  velocidade: null,
};

const SPEED_OPTIONS = [0.85, 0.9, 1.0, 1.1];
const BLIND_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const LENGTH_LABEL: Record<PresetLength, string> = { short: "Curta", medium: "Média", long: "Longa" };

function shuffledLetters(count: number): string[] {
  const letters = BLIND_LETTERS.slice(0, count);
  for (let i = letters.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [letters[i], letters[j]] = [letters[j], letters[i]];
  }
  return letters;
}

export function KokoroVoiceLab() {
  const [languages, setLanguages] = useState<KokoroLanguage[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);

  const [languageCode, setLanguageCode] = useState("");
  const [voiceId, setVoiceId] = useState("");
  const [text, setText] = useState("");
  const [speed, setSpeed] = useState(1.0);
  const [lengthFilter, setLengthFilter] = useState<PresetLength | "all">("all");

  const [blindMode, setBlindMode] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [blindLabels, setBlindLabels] = useState<Record<string, string>>({});

  const [runs, setRuns] = useState<Record<string, VoiceRunState>>({});
  const [ratings, setRatings] = useState<Record<string, VoiceRating>>({});
  const [preferredByLanguage, setPreferredByLanguage] = useState<Record<string, string | null>>({});
  const [comparingAll, setComparingAll] = useState(false);
  const [compareProgress, setCompareProgress] = useState<{ done: number; total: number } | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const runsRef = useRef(runs);
  runsRef.current = runs;

  useEffect(() => {
    let active = true;
    api<KokoroVoicesResponse>("/api/v1/tts-lab/kokoro/voices")
      .then((response) => {
        if (!active) return;
        setLanguages(response.languages);
        if (response.languages.length > 0) setLanguageCode(response.languages[0].code);
      })
      .catch((error) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 403) {
          setAccessDenied(true);
        } else {
          setLoadError(
            error instanceof ApiError ? error.message : "Não foi possível carregar as vozes do Kokoro.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      Object.values(runsRef.current).forEach((run) => {
        if (run.audioUrl) URL.revokeObjectURL(run.audioUrl);
      });
    };
  }, []);

  const currentLanguage = useMemo(
    () => languages.find((lang) => lang.code === languageCode) ?? null,
    [languages, languageCode],
  );
  const voices = currentLanguage?.voices ?? [];
  const presets = useMemo(() => presetsForLanguage(languageCode), [languageCode]);
  const visiblePresets = useMemo(
    () => (lengthFilter === "all" ? presets : presets.filter((p) => p.length === lengthFilter)),
    [presets, lengthFilter],
  );

  useEffect(() => {
    if (!currentLanguage) return;
    setVoiceId(currentLanguage.voices[0]?.id ?? "");
    Object.values(runsRef.current).forEach((run) => {
      if (run.audioUrl) URL.revokeObjectURL(run.audioUrl);
    });
    setRuns({});
    setRatings({});
    setRevealed(false);
    setText(presetsForLanguage(languageCode)[0]?.text ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [languageCode]);

  useEffect(() => {
    if (blindMode && voices.length > 0) {
      const letters = shuffledLetters(voices.length);
      setBlindLabels(Object.fromEntries(voices.map((v, i) => [v.id, letters[i]])));
      setRevealed(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blindMode, voices]);

  function labelFor(voice: KokoroVoice): string {
    if (blindMode && !revealed) return `Voz ${blindLabels[voice.id] ?? "?"}`;
    return `${voice.name} (${voice.id})`;
  }

  async function generateVoice(voice: KokoroVoice) {
    setRuns((current) => ({ ...current, [voice.id]: { status: "loading" } }));
    const previousUrl = runsRef.current[voice.id]?.audioUrl;
    if (previousUrl) URL.revokeObjectURL(previousUrl);

    try {
      const result = await api<KokoroGenerateResult>("/api/v1/tts-lab/kokoro/generate", {
        method: "POST",
        body: { language: languageCode, voice: voice.id, text, speed },
      });
      const blob = base64ToBlob(result.audio_base64, result.content_type);
      const audioUrl = URL.createObjectURL(blob);
      setRuns((current) => ({
        ...current,
        [voice.id]: {
          status: "ok",
          audioUrl,
          latencyMs: result.latency_ms,
          audioSizeBytes: result.audio_size_bytes,
        },
      }));
    } catch (error) {
      const status =
        error instanceof ApiError && error.status === 504
          ? "timeout"
          : error instanceof ApiError && error.status === 429
            ? "rate_limited"
            : "error";
      setRuns((current) => ({
        ...current,
        [voice.id]: {
          status,
          errorMessage: error instanceof ApiError ? error.message : "Falha desconhecida.",
        },
      }));
    }
  }

  async function compareAllVoices() {
    if (comparingAll || voices.length === 0) return;
    setComparingAll(true);
    setCompareProgress({ done: 0, total: voices.length });
    if (blindMode) {
      const letters = shuffledLetters(voices.length);
      setBlindLabels(Object.fromEntries(voices.map((v, i) => [v.id, letters[i]])));
      setRevealed(false);
    }
    try {
      for (let i = 0; i < voices.length; i += 1) {
        // eslint-disable-next-line no-await-in-loop
        await generateVoice(voices[i]);
        setCompareProgress({ done: i + 1, total: voices.length });
      }
    } finally {
      setComparingAll(false);
      setCompareProgress(null);
    }
  }

  function updateRating(targetVoiceId: string, patch: Partial<VoiceRating>) {
    setRatings((current) => ({
      ...current,
      [targetVoiceId]: { ...(current[targetVoiceId] ?? EMPTY_RATING), ...patch },
    }));
  }

  function togglePreferred(targetVoiceId: string) {
    setPreferredByLanguage((current) => ({
      ...current,
      [languageCode]: current[languageCode] === targetVoiceId ? null : targetVoiceId,
    }));
  }

  const preferredVoiceId = preferredByLanguage[languageCode] ?? null;

  async function copySummary() {
    const preferred = voices.find((v) => v.id === preferredVoiceId);
    const generated = voices.filter((v) => runs[v.id]?.status === "ok");
    const avgLatency =
      generated.length > 0
        ? Math.round(generated.reduce((sum, v) => sum + (runs[v.id]?.latencyMs ?? 0), 0) / generated.length)
        : null;
    const preferredRating = preferred ? ratings[preferred.id] ?? EMPTY_RATING : EMPTY_RATING;

    const summary = [
      `Language: ${languageCode}`,
      `Winner: ${preferred ? `${preferred.id} (${preferred.name})` : "—"}`,
      "",
      `Clarity: ${preferredRating.clareza ?? "—"}`,
      `Naturalness: ${preferredRating.naturalidade ?? "—"}`,
      `Intonation: ${preferredRating.entonacao ?? "—"}`,
      `Rhythm: ${preferredRating.ritmo ?? "—"}`,
      `Average latency: ${avgLatency !== null ? `${avgLatency} ms` : "—"}`,
    ].join("\n");

    try {
      await navigator.clipboard.writeText(summary);
      setCopyFeedback("Resumo copiado.");
    } catch {
      setCopyFeedback(summary);
    }
    setTimeout(() => setCopyFeedback(null), 4000);
  }

  if (accessDenied) return null;

  return (
    <div className="grid gap-6">
      <div>
        <h2 className="text-xl font-bold">Kokoro Voice Lab</h2>
        <p className="mt-1 text-sm text-text-secondary">
          Compare vozes do <code>hexgrad/kokoro-82m</code> dentro do mesmo idioma, com o mesmo texto, para escolher
          empiricamente a melhor voz por idioma. Critério mais importante:{" "}
          <strong>clareza / inteligibilidade para o aluno</strong> — a voz mais humana nem sempre é a melhor voz
          pedagógica. Nenhuma escolha feita aqui muda a voz usada nas aulas.
        </p>
      </div>

      {loadError && (
        <p role="alert" className="rounded-xl border border-danger/25 bg-danger/5 p-4 text-sm text-danger">
          {loadError}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-text-secondary">Carregando vozes…</p>
      ) : (
        <>
          <div className="panel grid gap-4 p-5">
            <div className="flex flex-wrap items-end gap-5">
              <label className="grid gap-1 text-sm font-medium" htmlFor="kokoro-language">
                Idioma
                <select
                  id="kokoro-language"
                  value={languageCode}
                  onChange={(event) => setLanguageCode(event.target.value)}
                  className="min-h-11 rounded-xl border-2 border-border bg-surface px-3 text-sm"
                >
                  {languages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-1 text-sm font-medium" htmlFor="kokoro-voice">
                Voz
                <select
                  id="kokoro-voice"
                  value={voiceId}
                  onChange={(event) => setVoiceId(event.target.value)}
                  className="min-h-11 rounded-xl border-2 border-border bg-surface px-3 text-sm"
                >
                  {voices.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {blindMode && !revealed ? `Voz ${blindLabels[voice.id] ?? "?"}` : `${voice.name} (${voice.id})`}
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-1 text-sm font-medium" htmlFor="kokoro-speed">
                Velocidade (geração)
                <select
                  id="kokoro-speed"
                  value={speed}
                  onChange={(event) => setSpeed(Number(event.target.value))}
                  className="min-h-11 rounded-xl border-2 border-border bg-surface px-3 text-sm"
                >
                  {SPEED_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option.toFixed(2)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex items-center gap-2 text-sm font-medium">
                <input type="checkbox" checked={blindMode} onChange={(event) => setBlindMode(event.target.checked)} />
                Modo teste cego
              </label>
              {blindMode && (
                <Button variant="secondary" type="button" onClick={() => setRevealed(true)} disabled={revealed}>
                  Revelar vozes
                </Button>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              {(["all", "short", "medium", "long"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setLengthFilter(option)}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                    lengthFilter === option
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-text-secondary hover:border-primary hover:text-primary"
                  }`}
                >
                  {option === "all" ? "Todos os tamanhos" : LENGTH_LABEL[option]}
                </button>
              ))}
            </div>

            {visiblePresets.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {visiblePresets.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => setText(preset.text)}
                    title={LENGTH_LABEL[preset.length]}
                    className="rounded-full border border-border px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:border-primary hover:text-primary"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            )}

            <label className="grid gap-2 text-sm font-medium" htmlFor="kokoro-text">
              Texto
              <textarea
                id="kokoro-text"
                rows={3}
                value={text}
                onChange={(event) => setText(event.target.value)}
                className="min-h-20 resize-y rounded-xl border-2 border-border bg-surface px-3.5 py-2.5 text-sm"
              />
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  const voice = voices.find((v) => v.id === voiceId);
                  if (voice) void generateVoice(voice);
                }}
                disabled={!voiceId || runs[voiceId]?.status === "loading"}
                loading={runs[voiceId]?.status === "loading"}
              >
                Gerar
              </Button>
              <Button
                type="button"
                onClick={() => void compareAllVoices()}
                disabled={comparingAll || voices.length === 0}
                loading={comparingAll}
              >
                Comparar todas as vozes
              </Button>
              {compareProgress && (
                <span className="text-xs text-text-secondary">
                  {compareProgress.done}/{compareProgress.total} vozes geradas…
                </span>
              )}
              {preferredVoiceId && (
                <span className="ml-auto text-xs text-text-secondary">
                  Preferida da sessão para {currentLanguage?.name}:{" "}
                  <strong>{blindMode && !revealed ? "(oculta no modo cego)" : preferredVoiceId}</strong>
                </span>
              )}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {voices.map((voice) => {
              const run = runs[voice.id] ?? { status: "idle" as const };
              const rating = ratings[voice.id] ?? EMPTY_RATING;
              const isPreferred = preferredVoiceId === voice.id;
              return (
                <div key={voice.id} className={`panel grid gap-3 p-4 ${isPreferred ? "ring-2 ring-primary" : ""}`}>
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-semibold">{labelFor(voice)}</h3>
                    <button
                      type="button"
                      onClick={() => togglePreferred(voice.id)}
                      className={`rounded-full border px-3 py-1 text-xs font-bold transition ${
                        isPreferred
                          ? "border-primary bg-primary text-white"
                          : "border-border text-text-secondary hover:border-primary hover:text-primary"
                      }`}
                    >
                      {isPreferred ? "⭐ Preferida" : "☆ Minha preferida"}
                    </button>
                  </div>
                  {!(blindMode && !revealed) && (
                    <p className="text-xs text-text-secondary">
                      Voice ID: <code>{voice.id}</code> · Idioma: {currentLanguage?.name} · Gênero: {voice.gender}
                    </p>
                  )}

                  <Button
                    variant="secondary"
                    type="button"
                    onClick={() => void generateVoice(voice)}
                    disabled={run.status === "loading"}
                    loading={run.status === "loading"}
                  >
                    Gerar
                  </Button>

                  {run.status === "ok" && run.audioUrl && (
                    <>
                      <audio controls src={run.audioUrl} className="w-full" />
                      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-text-secondary">
                        <dt>Latência</dt>
                        <dd>{run.latencyMs} ms</dd>
                        <dt>Tamanho</dt>
                        <dd>{Math.round((run.audioSizeBytes ?? 0) / 1024)} KB</dd>
                        <dt>Status</dt>
                        <dd>OK</dd>
                      </dl>
                    </>
                  )}

                  {(run.status === "error" || run.status === "timeout" || run.status === "rate_limited") && (
                    <p role="alert" className="text-sm text-danger">
                      Status: {run.status === "timeout" ? "TIMEOUT" : run.status === "rate_limited" ? "RATE_LIMITED" : "ERROR"}
                      {" — "}
                      {run.errorMessage}
                    </p>
                  )}

                  <div className="grid grid-cols-2 gap-3 border-t border-border pt-3 text-xs">
                    <label className="col-span-2 grid gap-1 font-medium text-primary">
                      Clareza (critério principal)
                      <select
                        aria-label={`Clareza — ${voice.id}`}
                        value={rating.clareza ?? ""}
                        onChange={(event) =>
                          updateRating(voice.id, { clareza: event.target.value ? Number(event.target.value) : null })
                        }
                        className="min-h-9 rounded-lg border border-primary/60 bg-surface px-2"
                      >
                        <option value="">—</option>
                        {[1, 2, 3, 4, 5].map((score) => (
                          <option key={score} value={score}>
                            {score}
                          </option>
                        ))}
                      </select>
                    </label>
                    {(["naturalidade", "entonacao", "ritmo"] as const).map((field) => (
                      <label key={field} className="grid gap-1 font-medium capitalize">
                        {field}
                        <select
                          aria-label={`${field} — ${voice.id}`}
                          value={rating[field] ?? ""}
                          onChange={(event) =>
                            updateRating(voice.id, { [field]: event.target.value ? Number(event.target.value) : null })
                          }
                          className="min-h-9 rounded-lg border border-border bg-surface px-2"
                        >
                          <option value="">—</option>
                          {[1, 2, 3, 4, 5].map((score) => (
                            <option key={score} value={score}>
                              {score}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                    <label className="col-span-2 grid gap-1 font-medium">
                      Velocidade percebida
                      <select
                        aria-label={`Velocidade percebida — ${voice.id}`}
                        value={rating.velocidade ?? ""}
                        onChange={(event) =>
                          updateRating(voice.id, { velocidade: (event.target.value || null) as VoiceRating["velocidade"] })
                        }
                        className="min-h-9 rounded-lg border border-border bg-surface px-2"
                      >
                        <option value="">—</option>
                        <option value="lenta">Lenta</option>
                        <option value="boa">Boa</option>
                        <option value="rapida">Rápida</option>
                      </select>
                    </label>
                  </div>
                </div>
              );
            })}
          </div>

          {voices.some((v) => runs[v.id]?.status === "ok") && (
            <div className="panel overflow-x-auto p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="font-semibold">Resumo — {currentLanguage?.name}</h3>
                <Button variant="secondary" type="button" onClick={() => void copySummary()}>
                  Copiar resultado
                </Button>
              </div>
              {copyFeedback && <p className="mb-2 text-xs text-text-secondary">{copyFeedback}</p>}
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs uppercase text-text-secondary">
                    <th className="py-2 pr-3">Voz</th>
                    <th className="py-2 pr-3">Clareza</th>
                    <th className="py-2 pr-3">Naturalidade</th>
                    <th className="py-2 pr-3">Entonação</th>
                    <th className="py-2 pr-3">Ritmo</th>
                    <th className="py-2 pr-3">Latência</th>
                  </tr>
                </thead>
                <tbody>
                  {voices.map((voice) => {
                    const run = runs[voice.id];
                    if (!run) return null;
                    const rating = ratings[voice.id] ?? EMPTY_RATING;
                    return (
                      <tr key={voice.id} className="border-b border-border last:border-0">
                        <td className="py-2 pr-3">{labelFor(voice)}</td>
                        <td className="py-2 pr-3">{rating.clareza ?? "—"}</td>
                        <td className="py-2 pr-3">{rating.naturalidade ?? "—"}</td>
                        <td className="py-2 pr-3">{rating.entonacao ?? "—"}</td>
                        <td className="py-2 pr-3">{rating.ritmo ?? "—"}</td>
                        <td className="py-2 pr-3">{run.latencyMs ? `${run.latencyMs} ms` : run.status.toUpperCase()}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
