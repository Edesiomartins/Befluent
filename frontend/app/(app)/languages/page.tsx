"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui";

const languages = [
  { code: "en", name: "Inglês", native: "English", status: "Em andamento", level: "B1", progress: 37 },
  { code: "es-ES", name: "Espanhol da Espanha", native: "Español", status: "Novo", progress: 0 },
  { code: "fr", name: "Francês", native: "Français", status: "Novo", progress: 0 },
  { code: "ja", name: "Japonês", native: "日本語", status: "Novo", progress: 0 },
  { code: "zh-CN", name: "Mandarim", native: "中文", status: "Novo", progress: 0 },
];

export default function LanguagesPage() {
  const [active, setActive] = useState("en");
  const [saving, setSaving] = useState("");
  async function activate(code: string) {
    setSaving(code);
    try { await api(`/api/v1/languages/${code}/activate`, { method: "POST" }); } catch { /* modo mock */ }
    setActive(code); setSaving("");
  }
  return (
    <div>
      <p className="text-sm font-semibold text-primary">Catálogo de estudo</p>
      <h1 className="mt-2 page-title">Idiomas</h1>
      <p className="mt-3 max-w-2xl leading-7 text-text-secondary">Escolha o foco da sua próxima sessão. Seu progresso fica separado por idioma.</p>
      <div className="mt-9 divide-y divide-border border-y border-border">
        {languages.map((language) => (
          <article key={language.code} className="grid gap-4 py-5 sm:grid-cols-[1fr_auto] sm:items-center">
            <div className="flex items-center gap-4">
              <span className="grid size-12 place-items-center rounded-lg bg-surface-elevated text-sm font-bold text-primary">{language.code.toUpperCase().slice(0, 2)}</span>
              <div><h2 className="font-semibold">{language.name} <span className="ml-2 font-normal text-text-secondary">{language.native}</span></h2><p className="mt-1 text-sm text-text-secondary">{active === language.code ? "Idioma ativo" : language.status}{language.level ? ` · Nível ${language.level} · ${language.progress}% do plano` : ""}</p></div>
            </div>
            {active === language.code ? <span className="text-sm font-semibold text-success">Ativo</span> : <Button variant="secondary" loading={saving === language.code} onClick={() => activate(language.code)}>Estudar este idioma</Button>}
          </article>
        ))}
      </div>
    </div>
  );
}
