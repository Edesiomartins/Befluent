"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CircleAlert, Clock, Headphones, Save } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button, ErrorState } from "@/components/ui";
import { LANGUAGES } from "@/lib/brand";
import { modeColorClasses, type ModeColor } from "@/lib/modes";
import type { PlacementTest } from "@/types/placement";

const CHECKLIST: Array<{ icon: typeof Clock; color: ModeColor; text: string }> = [
  { icon: Clock, color: "primary", text: "Duração aproximada: 15 a 20 minutos." },
  { icon: Headphones, color: "violet", text: "Use fones de ouvido: há atividades de compreensão auditiva." },
  { icon: Save, color: "teal", text: "Você pode sair e retomar depois — suas respostas ficam salvas." },
  { icon: CircleAlert, color: "gold", text: "O resultado é um nível estimado, não uma certificação oficial." },
];

export default function PlacementTestIntroPage() {
  const router = useRouter();
  const [language, setLanguage] = useState<string>("en");
  const [existing, setExisting] = useState<PlacementTest | null>(null);
  const [checking, setChecking] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<{ test: PlacementTest | null }>("/api/v1/placement-tests/current")
      .then((payload) => {
        if (active) setExisting(payload.test);
      })
      .catch(() => {
        if (active) setExisting(null);
      })
      .finally(() => {
        if (active) setChecking(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function start() {
    setStarting(true);
    setError("");
    try {
      const test = await api<PlacementTest>("/api/v1/placement-tests", {
        method: "POST",
        body: { language_code: language, declared_beginner: false },
      });
      router.push(`/placement-test/${test.id}`);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível iniciar o teste. Tente novamente.",
      );
      setStarting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <p className="text-sm font-semibold text-primary">Nivelamento</p>
      <h1 className="mt-2 page-title">Descubra seu nível atual</h1>
      <p className="mt-3 leading-7 text-text-secondary">
        Responda a atividades de vocabulário, leitura, escuta e produção. O resultado
        ajudará o BeFluent a personalizar seus estudos.
      </p>
      <span className="stat-pill mt-4 bg-primary-soft text-primary">
        <Clock className="size-3.5" aria-hidden />
        15–20 min
      </span>

      {existing && !checking && (
        <div className="mt-6 rounded-2xl border border-primary/25 bg-primary-soft/50 p-5" role="status">
          <h2 className="font-semibold">Você tem um teste em andamento</h2>
          <p className="mt-1 text-sm text-text-secondary">
            {existing.progress.answered} de {existing.progress.target} atividades respondidas.
          </p>
          <Link
            href={`/placement-test/${existing.id}`}
            className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-white shadow-[0_4px_0_var(--primary-shadow)]"
          >
            Retomar teste
          </Link>
        </div>
      )}

      <section className="panel mt-6 p-6">
        <h2 className="section-title">Antes de começar</h2>
        <ul className="mt-4 grid gap-4">
          {CHECKLIST.map((item) => {
            const Icon = item.icon;
            const colors = modeColorClasses[item.color];
            return (
              <li key={item.text} className="flex items-start gap-3 text-sm leading-6 text-text-secondary">
                <span className={`grid size-8 shrink-0 place-items-center rounded-lg ${colors.bg} ${colors.text}`}>
                  <Icon className="size-4" aria-hidden />
                </span>
                <span className="pt-1">{item.text}</span>
              </li>
            );
          })}
        </ul>
        <p className="mt-4 rounded-xl border border-border bg-[var(--surface-soft)] px-4 py-3 text-sm leading-6 text-text-secondary">
          A avaliação de fala ainda não está disponível e não será cobrada neste teste.
        </p>

        <label className="mt-6 grid max-w-sm gap-2 text-sm font-medium">
          Idioma do teste
          <select
            className="min-h-11 rounded-xl border-2 border-border bg-surface px-3"
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            disabled={starting}
          >
            {LANGUAGES.map((item) => (
              <option key={item.code} value={item.code}>
                {item.namePt}
              </option>
            ))}
          </select>
        </label>

        {error && (
          <div className="mt-5">
            <ErrorState message={error} />
          </div>
        )}

        <Button className="mt-6" onClick={start} loading={starting} disabled={starting}>
          Iniciar teste
        </Button>
      </section>
    </div>
  );
}
