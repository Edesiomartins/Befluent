"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button, Input, Loading } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { levelShortCode } from "@/lib/levels";

type ProfileData = {
  id: string;
  email: string;
  name: string;
};

type DashboardSummary = {
  progress?: {
    study_sessions?: number;
    total_minutes_label?: string;
  };
  active_language?: {
    name_pt: string;
    level?: { current_level: string | null };
    level_estimate?: string | null;
    goal?: string | null;
  } | null;
};

export default function ProfilePage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [goal, setGoal] = useState("");
  const [languageLabel, setLanguageLabel] = useState("—");
  const [timeLabel, setTimeLabel] = useState("0min");
  const [sessions, setSessions] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      api<ProfileData>("/api/v1/profile"),
      api<DashboardSummary>("/api/v1/dashboard"),
    ])
      .then(([profile, dashboard]) => {
        if (!active) return;
        setName(profile.name);
        setEmail(profile.email);
        const lang = dashboard.active_language;
        if (lang) {
          const level =
            lang.level?.current_level
              ? levelShortCode(lang.level.current_level)
              : lang.level_estimate || null;
          setLanguageLabel(level ? `${lang.name_pt} · ${level}` : lang.name_pt);
          setGoal(lang.goal || "");
        }
        setTimeLabel(dashboard.progress?.total_minutes_label || "0min");
        setSessions(dashboard.progress?.study_sessions || 0);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível carregar o perfil.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const updated = await api<ProfileData>("/api/v1/profile", {
        method: "PATCH",
        body: { name: name.trim() },
      });
      setName(updated.name);
      setSaved(true);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível salvar o perfil.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Loading label="Carregando perfil" />;

  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "?";

  return (
    <div className="max-w-3xl">
      <p className="text-sm font-semibold text-primary">Sua conta</p>
      <h1 className="mt-2 page-title">Perfil</h1>

      <div className="mt-9 flex items-center gap-5 border-y border-border py-6">
        <span className="grid size-16 place-items-center rounded-full bg-primary text-xl font-semibold text-white">
          {initials}
        </span>
        <div>
          <h2 className="text-lg font-semibold">{name || "Sem nome"}</h2>
          <p className="mt-1 text-sm text-text-secondary">{email}</p>
        </div>
      </div>

      <form className="grid gap-5 py-7 sm:grid-cols-2" onSubmit={save}>
        <Input
          label="Nome"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setSaved(false);
          }}
        />
        <Input label="E-mail" value={email} disabled />
        {goal && (
          <label className="grid gap-2 text-sm font-medium sm:col-span-2">
            Objetivo do plano
            <input
              className="min-h-11 rounded-lg border border-border bg-surface-elevated px-3 text-text-secondary"
              value={goal}
              disabled
              readOnly
            />
          </label>
        )}
        {error && (
          <p role="alert" className="text-sm text-danger sm:col-span-2">
            {error}
          </p>
        )}
        <div className="flex items-center justify-end gap-4 sm:col-span-2">
          {saved && (
            <span role="status" className="text-sm font-medium text-success">
              Perfil atualizado.
            </span>
          )}
          <Button type="submit" loading={saving}>
            Salvar perfil
          </Button>
        </div>
      </form>

      <section className="border-y border-border py-7">
        <h2 className="section-title">Resumo do aprendizado</h2>
        <dl className="mt-5 grid gap-5 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-text-secondary">Idioma principal</dt>
            <dd className="mt-1 font-semibold">{languageLabel}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Tempo estudado</dt>
            <dd className="mt-1 font-semibold">{timeLabel}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Sessões</dt>
            <dd className="mt-1 font-semibold">{sessions}</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
