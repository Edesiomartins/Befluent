"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Play } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { base64ToBlob } from "@/lib/audio";
import { Button } from "@/components/ui";
import { KokoroVoiceLab } from "@/components/kokoro-voice-lab";

type ModelCapability = {
  id: string;
  display_name: string;
  provider: string;
  supports_speed: boolean;
  supports_voice: boolean;
  supported_formats: string[];
  default_voice: string | null;
  free: boolean;
};

type GenerateResult = {
  model: string;
  audio_base64: string;
  content_type: string;
  latency_ms: number;
  audio_size_bytes: number;
  free_model: boolean;
  cost_available: boolean;
  estimated_cost: number | null;
};

type ModelRunState = {
  status: "idle" | "loading" | "ok" | "error" | "timeout" | "rate_limited";
  audioUrl?: string;
  latencyMs?: number;
  audioSizeBytes?: number;
  format?: string;
  errorMessage?: string;
};

type Rating = {
  naturalidade: number | null;
  clareza: number | null;
  entonacao: number | null;
  pausas: number | null;
  velocidade: "lenta" | "boa" | "rapida" | null;
};

const EMPTY_RATING: Rating = {
  naturalidade: null,
  clareza: null,
  entonacao: null,
  pausas: null,
  velocidade: null,
};

const PRESETS = [
  { label: "Conversação simples", text: "Hello! How are you doing today?" },
  {
    label: "Repetição",
    text: "I'm sorry, I didn't quite catch that. Could you say it again a little more slowly?",
  },
  {
    label: "Conversação natural",
    text: "Well... I'm not completely sure. Let me think about it for a second.",
  },
  { label: "Entonação", text: "Really? You went there by yourself? That's impressive!" },
  { label: "Situação cotidiana", text: "I'd like a cup of coffee, please. Actually, make that two." },
  {
    label: "Horários e números",
    text: "The meeting starts at 8:30 a.m., but I'd recommend arriving fifteen minutes early.",
  },
  { label: "B2", text: "Although I understand your point, I don't entirely agree with your conclusion." },
  { label: "Direções", text: "Could you tell me where the nearest train station is?" },
  {
    label: "Feedback pedagógico",
    text: "Great job. Your answer was correct, but let's work on making it sound more natural.",
  },
];

const SPEED_OPTIONS = [0.85, 0.9, 1.0, 1.1];
const PAUSE_OPTIONS = [0, 250, 500, 750];
const BLIND_LETTERS = ["A", "B", "C", "D", "E", "F"];

/** Heurística de espaçamento textual — nenhum suporte a SSML foi confirmado
 * para os modelos deste laboratório, então a "pausa" é só espaçamento entre
 * parágrafos, nunca uma tag de pausa inventada. */
function applyPauseHeuristic(text: string, pauseMs: number): string {
  const paragraphs = text.split(/\n+/).filter((part) => part.trim().length > 0);
  if (paragraphs.length <= 1) return text;
  const separator = "\n".repeat(1 + pauseMs / 250);
  return paragraphs.join(separator);
}

function shuffledLetters(count: number): string[] {
  const letters = BLIND_LETTERS.slice(0, count);
  for (let i = letters.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [letters[i], letters[j]] = [letters[j], letters[i]];
  }
  return letters;
}

export default function TTSLabPage() {
  const [models, setModels] = useState<ModelCapability[]>([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [text, setText] = useState(PRESETS[0].text);
  const [speed, setSpeed] = useState(1.0);
  const [pauseMs, setPauseMs] = useState(0);
  const [blindMode, setBlindMode] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [blindLabels, setBlindLabels] = useState<Record<string, string>>({});
  const [generatingAll, setGeneratingAll] = useState(false);

  const [runs, setRuns] = useState<Record<string, ModelRunState>>({});
  const [ratings, setRatings] = useState<Record<string, Rating>>({});

  const runsRef = useRef(runs);
  runsRef.current = runs;

  useEffect(() => {
    let active = true;
    api<{ models: ModelCapability[] }>("/api/v1/tts-lab/models")
      .then((response) => {
        if (!active) return;
        setModels(response.models);
        setRuns(
          Object.fromEntries(response.models.map((model) => [model.id, { status: "idle" as const }])),
        );
        setRatings(Object.fromEntries(response.models.map((model) => [model.id, { ...EMPTY_RATING }])));
      })
      .catch((error) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 403) {
          setAccessDenied(true);
        } else {
          setLoadError(
            error instanceof ApiError ? error.message : "Não foi possível carregar os modelos do TTS Lab.",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingModels(false);
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

  useEffect(() => {
    if (blindMode && models.length > 0) {
      const letters = shuffledLetters(models.length);
      setBlindLabels(Object.fromEntries(models.map((model, index) => [model.id, letters[index]])));
      setRevealed(false);
    }
  }, [blindMode, models]);

  const sortedByLatency = useMemo(() => {
    return [...models].sort((a, b) => (runs[a.id]?.latencyMs ?? Infinity) - (runs[b.id]?.latencyMs ?? Infinity));
  }, [models, runs]);

  async function generateOne(model: ModelCapability) {
    setRuns((current) => ({ ...current, [model.id]: { status: "loading" } }));

    const previousUrl = runsRef.current[model.id]?.audioUrl;
    if (previousUrl) URL.revokeObjectURL(previousUrl);

    const processedText = applyPauseHeuristic(text, pauseMs);
    try {
      const result = await api<GenerateResult>("/api/v1/tts-lab/generate", {
        method: "POST",
        body: {
          model: model.id,
          text: processedText,
          speed: model.supports_speed ? speed : undefined,
        },
      });
      const blob = base64ToBlob(result.audio_base64, result.content_type);
      const audioUrl = URL.createObjectURL(blob);
      setRuns((current) => ({
        ...current,
        [model.id]: {
          status: "ok",
          audioUrl,
          latencyMs: result.latency_ms,
          audioSizeBytes: result.audio_size_bytes,
          format: result.content_type,
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
        [model.id]: {
          status,
          errorMessage: error instanceof ApiError ? error.message : "Falha desconhecida.",
        },
      }));
    }
  }

  async function generateAll() {
    if (generatingAll) return;
    setGeneratingAll(true);
    try {
      for (const model of models) {
        await generateOne(model);
      }
    } finally {
      setGeneratingAll(false);
    }
  }

  function updateRating(modelId: string, patch: Partial<Rating>) {
    setRatings((current) => ({ ...current, [modelId]: { ...current[modelId], ...patch } }));
  }

  function labelFor(model: ModelCapability): string {
    if (blindMode && !revealed) return `Voz ${blindLabels[model.id] ?? "?"}`;
    return model.display_name;
  }

  if (accessDenied) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <h1 className="text-lg font-semibold text-danger">Acesso restrito</h1>
        <p className="mt-2 text-sm text-text-secondary">
          Esta conta não tem acesso ao TTS Lab. Fale com quem administra a implantação se precisar de acesso.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-bold">TTS Lab</h1>
        <p className="mt-1 text-sm text-text-secondary">Compare modelos de voz usando o mesmo texto.</p>
      </div>

      {loadError && (
        <p role="alert" className="rounded-xl border border-danger/25 bg-danger/5 p-4 text-sm text-danger">
          {loadError}
        </p>
      )}

      <div className="panel grid gap-4 p-5">
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => setText(preset.text)}
              className="rounded-full border border-border px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:border-primary hover:text-primary"
            >
              {preset.label}
            </button>
          ))}
        </div>

        <label className="grid gap-2 text-sm font-medium" htmlFor="tts-lab-text">
          Texto para teste
          <textarea
            id="tts-lab-text"
            rows={4}
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="min-h-24 resize-y rounded-xl border-2 border-border bg-surface px-3.5 py-2.5 text-sm"
          />
        </label>

        <div className="flex flex-wrap items-end gap-5">
          <label className="grid gap-1 text-sm font-medium" htmlFor="tts-lab-speed">
            Velocidade
            <select
              id="tts-lab-speed"
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

          <label className="grid gap-1 text-sm font-medium" htmlFor="tts-lab-pause">
            Pausa entre parágrafos
            <select
              id="tts-lab-pause"
              value={pauseMs}
              onChange={(event) => setPauseMs(Number(event.target.value))}
              className="min-h-11 rounded-xl border-2 border-border bg-surface px-3 text-sm"
            >
              {PAUSE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option} ms
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              type="checkbox"
              checked={blindMode}
              onChange={(event) => setBlindMode(event.target.checked)}
            />
            Modo teste cego
          </label>
          {blindMode && (
            <Button variant="secondary" type="button" onClick={() => setRevealed(true)} disabled={revealed}>
              Revelar modelos
            </Button>
          )}

          <Button
            type="button"
            onClick={() => void generateAll()}
            disabled={generatingAll || loadingModels || models.length === 0}
            loading={generatingAll}
            className="ml-auto"
          >
            Gerar em todos
          </Button>
        </div>
      </div>

      {loadingModels ? (
        <p className="text-sm text-text-secondary">Carregando modelos…</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {models.map((model) => {
            const run = runs[model.id] ?? { status: "idle" as const };
            return (
              <div key={model.id} className="panel grid gap-3 p-4">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="font-semibold">{labelFor(model)}</h2>
                  {model.free && <span className="rounded-full bg-success/10 px-2 py-0.5 text-[.65rem] font-bold uppercase text-success">Free</span>}
                </div>

                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => void generateOne(model)}
                  disabled={run.status === "loading"}
                  loading={run.status === "loading"}
                >
                  Gerar
                </Button>

                {!model.supports_speed && (
                  <p className="text-xs text-text-secondary">Speed control not supported</p>
                )}

                {run.status === "ok" && run.audioUrl && (
                  <>
                    <audio controls src={run.audioUrl} className="w-full">
                      <Play className="sr-only" aria-hidden />
                    </audio>
                    <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-text-secondary">
                      <dt>Latência</dt>
                      <dd>{run.latencyMs} ms</dd>
                      <dt>Tamanho</dt>
                      <dd>{Math.round((run.audioSizeBytes ?? 0) / 1024)} KB</dd>
                      <dt>Formato</dt>
                      <dd>{run.format}</dd>
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
                  {(["naturalidade", "clareza", "entonacao", "pausas"] as const).map((field) => (
                    <label key={field} className="grid gap-1 font-medium capitalize">
                      {field}
                      <select
                        aria-label={`${field} — ${model.display_name}`}
                        value={ratings[model.id]?.[field] ?? ""}
                        onChange={(event) =>
                          updateRating(model.id, { [field]: event.target.value ? Number(event.target.value) : null })
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
                      aria-label={`Velocidade percebida — ${model.display_name}`}
                      value={ratings[model.id]?.velocidade ?? ""}
                      onChange={(event) =>
                        updateRating(model.id, {
                          velocidade: (event.target.value || null) as Rating["velocidade"],
                        })
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
      )}

      {models.length > 0 && (
        <div className="panel overflow-x-auto p-4">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase text-text-secondary">
                <th className="py-2 pr-3">Modelo</th>
                <th className="py-2 pr-3">Latência</th>
                <th className="py-2 pr-3">Naturalidade</th>
                <th className="py-2 pr-3">Clareza</th>
                <th className="py-2 pr-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {sortedByLatency.map((model) => {
                const run = runs[model.id] ?? { status: "idle" as const };
                return (
                  <tr key={model.id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-3">{labelFor(model)}</td>
                    <td className="py-2 pr-3">{run.latencyMs ? `${run.latencyMs} ms` : "—"}</td>
                    <td className="py-2 pr-3">{ratings[model.id]?.naturalidade ?? "—"}</td>
                    <td className="py-2 pr-3">{ratings[model.id]?.clareza ?? "—"}</td>
                    <td className="py-2 pr-3">{run.status.toUpperCase()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <hr className="border-border" />

      <KokoroVoiceLab />
    </div>
  );
}
