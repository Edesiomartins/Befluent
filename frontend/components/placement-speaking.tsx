"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";

export function PlacementSpeaking({ testId, itemId, onComplete }: {
  testId: string; itemId: string; onComplete: () => Promise<void>;
}) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [audio, setAudio] = useState<Blob | null>(null);
  const [error, setError] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      if (timer.current) clearTimeout(timer.current);
      if (recorder.current) recorder.current.onstop = null;
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach(track => track.stop());
    };
  }, []);

  function stop() {
    if (timer.current) clearTimeout(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
    stream.current?.getTracks().forEach(track => track.stop());
    setRecording(false);
  }

  async function start() {
    setError(""); setBusy(true); setAudio(null);
    try {
      const microphone = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!alive.current) { microphone.getTracks().forEach(track => track.stop()); return; }
      stream.current = microphone;
      const type = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"]
        .find(value => MediaRecorder.isTypeSupported(value));
      const rec = new MediaRecorder(microphone, type ? { mimeType: type } : undefined);
      recorder.current = rec;
      const chunks: Blob[] = [];
      rec.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      rec.onstop = () => {
        if (alive.current) setAudio(new Blob(chunks, { type: rec.mimeType }));
      };
      rec.start(); setRecording(true);
      timer.current = setTimeout(stop, 90_000);
    } catch {
      stream.current?.getTracks().forEach(track => track.stop());
      setError("Não foi possível acessar o microfone. Permita o acesso ou pule esta avaliação.");
    } finally { if (alive.current) setBusy(false); }
  }

  async function submit(skip = false) {
    if (busy || recording) return;
    setBusy(true); setError("");
    try {
      if (skip) {
        await api(`/api/v1/placement-tests/${testId}/skip-production`, {
          method: "POST", body: { item_id: itemId, text: "skip" },
        });
      } else if (audio) {
        const form = new FormData();
        form.append("item_id", itemId);
        form.append("file", audio, "speaking.webm");
        await api(`/api/v1/placement-tests/${testId}/speaking`, { method: "POST", body: form });
      } else return;
      await onComplete();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Não foi possível enviar a gravação. Tente novamente.");
    } finally { if (alive.current) setBusy(false); }
  }

  return <div className="mt-5 grid gap-4">
    <p className="text-sm text-text-secondary">Fale espontaneamente por 30 a 90 segundos. A análise linguística da transcrição é provisória; pronúncia e fluência acústica não são medidas.</p>
    <p role="status">{recording ? "Gravando…" : audio ? "Gravação pronta para enviar" : "Microfone solicitado somente ao gravar"}</p>
    <Button onClick={recording ? stop : start} disabled={busy}>{recording ? "Parar gravação" : "Gravar resposta"}</Button>
    {audio && <Button onClick={() => void submit()} disabled={busy || recording} loading={busy}>Enviar gravação</Button>}
    <Button variant="secondary" onClick={() => void submit(true)} disabled={busy || recording}>Pular avaliação de fala</Button>
    {error && <p role="alert" className="text-sm text-danger">{error}</p>}
  </div>;
}
