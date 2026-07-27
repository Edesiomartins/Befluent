"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Toggle } from "@/components/ui";

export default function SettingsPage() {
  const [settings, setSettings] = useState({ translation: false, autoplay: true, saveAudio: false, analytics: true });
  const [speed, setSpeed] = useState("1");
  const [correction, setCorrection] = useState("each");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  function update(key: keyof typeof settings, value: boolean) { setSettings((current) => ({ ...current, [key]: value })); setSaved(false); }
  async function save() {
    setSaving(true);
    try { await api("/api/v1/settings", { method: "PUT", body: { ...settings, voice_speed: Number(speed), correction_mode: correction } }); } catch { /* modo mock */ }
    setSaving(false); setSaved(true);
  }
  return (
    <div className="max-w-3xl">
      <p className="text-sm font-semibold text-primary">Preferências</p><h1 className="mt-2 page-title">Configurações</h1><p className="mt-3 leading-7 text-text-secondary">Ajuste como o BeFluent apresenta áudio, traduções e correções.</p>
      <section className="mt-9 border-t border-border py-7"><h2 className="section-title">Voz e áudio</h2><label className="mt-5 grid max-w-sm gap-2 text-sm font-medium">Velocidade padrão da voz<select value={speed} onChange={(e) => { setSpeed(e.target.value); setSaved(false); }} className="min-h-11 rounded-lg border border-border bg-surface px-3"><option value=".75">0,75× — mais lenta</option><option value="1">1× — normal</option><option value="1.25">1,25× — mais rápida</option></select></label><div className="mt-4"><Toggle label="Reproduzir áudio automaticamente" description="Inicia o áudio ao abrir atividades auditivas." checked={settings.autoplay} onChange={(value) => update("autoplay", value)} /></div></section>
      <section className="border-t border-border py-7"><h2 className="section-title">Apoio durante o estudo</h2><label className="mt-5 grid max-w-sm gap-2 text-sm font-medium">Momento das correções<select value={correction} onChange={(e) => { setCorrection(e.target.value); setSaved(false); }} className="min-h-11 rounded-lg border border-border bg-surface px-3"><option value="each">Após cada resposta</option><option value="end">Ao final da atividade</option><option value="request">Somente quando eu pedir</option></select></label><div className="mt-4"><Toggle label="Mostrar traduções por padrão" description="Você ainda poderá ocultar ou exibir durante cada atividade." checked={settings.translation} onChange={(value) => update("translation", value)} /></div></section>
      <section className="border-t border-border py-7"><h2 className="section-title">Privacidade</h2><div className="mt-3"><Toggle label="Salvar gravações de voz" description="Desativado: o áudio é descartado após o processamento." checked={settings.saveAudio} onChange={(value) => update("saveAudio", value)} /><Toggle label="Compartilhar dados de uso anônimos" description="Ajuda a identificar falhas sem incluir o conteúdo das suas atividades." checked={settings.analytics} onChange={(value) => update("analytics", value)} /></div></section>
      <div className="flex items-center justify-end gap-4 border-t border-border pt-6">{saved && <span className="text-sm font-medium text-success" role="status">Preferências salvas.</span>}<Button loading={saving} onClick={save}>Salvar alterações</Button></div>
    </div>
  );
}
