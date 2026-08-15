"use client";

import { FormEvent, useEffect, useState, type ReactNode } from "react";
import { Clock, MessagesSquare, Shield, Volume2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button, Loading, Toggle } from "@/components/ui";
import { modeColorClasses, type ModeColor } from "@/lib/modes";

function SettingsSection({
  icon: Icon,
  color,
  title,
  children,
}: {
  icon: typeof Volume2;
  color: ModeColor;
  title: string;
  children: ReactNode;
}) {
  const colors = modeColorClasses[color];
  return (
    <section className="panel mt-5 p-6">
      <div className="flex items-center gap-3">
        <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${colors.bg} ${colors.text}`}>
          <Icon className="size-5" aria-hidden />
        </span>
        <h2 className="section-title">{title}</h2>
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

type UiPrefs = {
  translation?: boolean;
  autoplay?: boolean;
  save_audio?: boolean;
  analytics?: boolean;
  correction_mode?: string;
};

type SettingsResponse = {
  tts_speed: number;
  ui_prefs: UiPrefs;
  default_language_id: string | null;
  timezone?: string;
};

const DEFAULT_PREFS: Required<UiPrefs> = {
  translation: false,
  autoplay: true,
  save_audio: false,
  analytics: true,
  correction_mode: "each",
};

export default function SettingsPage() {
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [speed, setSpeed] = useState("1");
  const [timezone, setTimezone] = useState("America/Sao_Paulo");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<SettingsResponse>("/api/v1/settings")
      .then((payload) => {
        if (!active) return;
        const ui = payload.ui_prefs || {};
        setPrefs({
          translation: Boolean(ui.translation ?? DEFAULT_PREFS.translation),
          autoplay: Boolean(ui.autoplay ?? DEFAULT_PREFS.autoplay),
          save_audio: Boolean(ui.save_audio ?? DEFAULT_PREFS.save_audio),
          analytics: Boolean(ui.analytics ?? DEFAULT_PREFS.analytics),
          correction_mode: String(ui.correction_mode ?? DEFAULT_PREFS.correction_mode),
        });
        setSpeed(String(payload.tts_speed || 1));
        setTimezone(payload.timezone || "America/Sao_Paulo");
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível carregar as configurações.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function updatePref<K extends keyof Required<UiPrefs>>(key: K, value: Required<UiPrefs>[K]) {
    setPrefs((current) => ({ ...current, [key]: value }));
    setSaved(false);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const payload = await api<SettingsResponse>("/api/v1/settings", {
        method: "PATCH",
        body: {
          tts_speed: Number(speed),
          timezone,
          ui_prefs: {
            translation: prefs.translation,
            autoplay: prefs.autoplay,
            save_audio: prefs.save_audio,
            analytics: prefs.analytics,
            correction_mode: prefs.correction_mode,
          },
        },
      });
      setSpeed(String(payload.tts_speed || 1));
      setSaved(true);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível salvar as preferências.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Loading label="Carregando configurações" />;

  return (
    <div className="max-w-3xl">
      <p className="text-sm font-semibold text-primary">Preferências</p>
      <h1 className="mt-2 page-title">Configurações</h1>
      <p className="mt-3 leading-7 text-text-secondary">
        Ajuste como o BeFluent apresenta áudio, traduções e correções.
      </p>

      <form onSubmit={save}>
        <SettingsSection icon={Volume2} color="primary" title="Voz e áudio">
          <label className="grid max-w-sm gap-2 text-sm font-medium">
            Velocidade padrão da voz
            <select
              value={speed}
              onChange={(e) => {
                setSpeed(e.target.value);
                setSaved(false);
              }}
              className="min-h-11 rounded-xl border-2 border-border bg-surface px-3.5"
            >
              <option value="0.75">0,75× — mais lenta</option>
              <option value="1">1× — normal</option>
              <option value="1.25">1,25× — mais rápida</option>
              <option value="1.5">1,5× — bem mais rápida</option>
            </select>
          </label>
          <div className="mt-4">
            <Toggle
              label="Reproduzir áudio automaticamente"
              description="Inicia o áudio ao abrir atividades auditivas."
              checked={prefs.autoplay}
              onChange={(value) => updatePref("autoplay", value)}
            />
          </div>
        </SettingsSection>

        <SettingsSection icon={Clock} color="teal" title="Fuso horário">
          <label className="grid max-w-sm gap-2 text-sm font-medium">
            Seu fuso (streak e minutos de hoje)
            <select
              value={timezone}
              onChange={(e) => {
                setTimezone(e.target.value);
                setSaved(false);
              }}
              className="min-h-11 rounded-xl border-2 border-border bg-surface px-3.5"
            >
              <option value="America/Sao_Paulo">Brasília (America/Sao_Paulo)</option>
              <option value="America/Manaus">Manaus (America/Manaus)</option>
              <option value="America/Noronha">Fernando de Noronha</option>
              <option value="UTC">UTC</option>
            </select>
          </label>
        </SettingsSection>

        <SettingsSection icon={MessagesSquare} color="violet" title="Apoio durante o estudo">
          <label className="grid max-w-sm gap-2 text-sm font-medium">
            Momento das correções
            <select
              value={prefs.correction_mode}
              onChange={(e) => updatePref("correction_mode", e.target.value)}
              className="min-h-11 rounded-xl border-2 border-border bg-surface px-3.5"
            >
              <option value="each">Após cada resposta</option>
              <option value="end">Ao final da atividade</option>
              <option value="request">Somente quando eu pedir</option>
            </select>
          </label>
          <div className="mt-4">
            <Toggle
              label="Mostrar traduções por padrão"
              description="Você ainda poderá ocultar ou exibir durante cada atividade."
              checked={prefs.translation}
              onChange={(value) => updatePref("translation", value)}
            />
          </div>
        </SettingsSection>

        <SettingsSection icon={Shield} color="rose" title="Privacidade">
          <Toggle
            label="Salvar gravações de voz"
            description="Desativado: o áudio é descartado após o processamento."
            checked={prefs.save_audio}
            onChange={(value) => updatePref("save_audio", value)}
          />
          <Toggle
            label="Compartilhar dados de uso anônimos"
            description="Ajuda a identificar falhas sem incluir o conteúdo das suas atividades."
            checked={prefs.analytics}
            onChange={(value) => updatePref("analytics", value)}
          />
        </SettingsSection>

        {error && (
          <p role="alert" className="mt-5 text-sm text-danger">
            {error}
          </p>
        )}

        <div className="mt-6 flex items-center justify-end gap-4">
          {saved && (
            <span className="text-sm font-medium text-success" role="status">
              Preferências salvas.
            </span>
          )}
          <Button type="submit" loading={saving}>
            Salvar alterações
          </Button>
        </div>
      </form>
    </div>
  );
}
