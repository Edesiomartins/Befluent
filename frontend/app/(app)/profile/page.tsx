"use client";

import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { api } from "@/lib/api";

export default function ProfilePage() {
  const [name, setName] = useState("Edesio");
  const [goal, setGoal] = useState("Conversar com confiança");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  async function save() {
    setSaving(true);
    try { await api("/api/v1/profile", { method: "PATCH", body: { name, general_goal: goal } }); } catch { /* modo mock */ }
    setSaving(false); setSaved(true);
  }
  return (
    <div className="max-w-3xl">
      <p className="text-sm font-semibold text-primary">Sua conta</p><h1 className="mt-2 page-title">Perfil</h1>
      <div className="mt-9 flex items-center gap-5 border-y border-border py-6"><span className="grid size-16 place-items-center rounded-full bg-primary text-xl font-semibold text-white">ED</span><div><h2 className="text-lg font-semibold">{name}</h2><p className="mt-1 text-sm text-text-secondary">Membro desde julho de 2026</p></div></div>
      <section className="grid gap-5 py-7 sm:grid-cols-2"><Input label="Nome" value={name} onChange={(e) => { setName(e.target.value); setSaved(false); }} /><Input label="E-mail" value="edesio@exemplo.com" disabled /><label className="grid gap-2 text-sm font-medium sm:col-span-2">Objetivo geral<select value={goal} onChange={(e) => { setGoal(e.target.value); setSaved(false); }} className="min-h-11 rounded-lg border border-border bg-surface px-3"><option>Conversar com confiança</option><option>Viajar com autonomia</option><option>Desenvolvimento profissional</option><option>Estudos acadêmicos</option></select></label></section>
      <section className="border-y border-border py-7"><h2 className="section-title">Resumo do aprendizado</h2><dl className="mt-5 grid gap-5 sm:grid-cols-3"><div><dt className="text-xs text-text-secondary">Idioma principal</dt><dd className="mt-1 font-semibold">Inglês · B1</dd></div><div><dt className="text-xs text-text-secondary">Tempo estudado</dt><dd className="mt-1 font-semibold">18h 42min</dd></div><div><dt className="text-xs text-text-secondary">Sessões</dt><dd className="mt-1 font-semibold">64</dd></div></dl></section>
      <div className="mt-6 flex items-center justify-end gap-4">{saved && <span role="status" className="text-sm font-medium text-success">Perfil atualizado.</span>}<Button loading={saving} onClick={save}>Salvar perfil</Button></div>
    </div>
  );
}
