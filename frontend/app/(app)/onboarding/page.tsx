"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";

const languages = [
  ["en", "Inglês"],
  ["es-ES", "Espanhol da Espanha"],
  ["fr", "Francês"],
  ["ja", "Japonês"],
  ["zh-CN", "Mandarim"],
];
const skills = [
  "Conversação",
  "Compreensão auditiva",
  "Vocabulário",
  "Gramática",
  "Leitura",
  "Escrita",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [language, setLanguage] = useState("en");
  const [level, setLevel] = useState("iniciante");
  const [goal, setGoal] = useState("Conversar com confiança");
  const [minutes, setMinutes] = useState(20);
  const [selectedSkills, setSelectedSkills] = useState([
    "Conversação",
    "Compreensão auditiva",
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function finish() {
    if (loading || success) return;
    setLoading(true);
    setError("");
    setSuccess(false);
    try {
      await api("/api/v1/onboarding/complete", {
        method: "POST",
        body: {
          language_code: language,
          perceived_level: level,
          goal,
          minutes_per_day: minutes,
          skills: selectedSkills,
        },
      });
      setSuccess(true);
      window.setTimeout(() => {
        router.replace("/dashboard");
        router.refresh();
      }, 700);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível criar seu plano. Tente novamente.",
      );
    } finally {
      setLoading(false);
    }
  }

  function toggleSkill(skill: string) {
    setSelectedSkills((current) =>
      current.includes(skill)
        ? current.filter((item) => item !== skill)
        : [...current, skill],
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <p className="text-sm font-semibold text-primary">Configuração inicial</p>
      <h1 className="mt-2 page-title">Vamos construir seu plano.</h1>
      <p className="mt-3 max-w-xl leading-7 text-text-secondary">
        Conte o que você quer alcançar. Você poderá ajustar tudo depois.
      </p>
      <div className="mt-9 grid gap-8">
        <fieldset>
          <legend className="section-title">Qual idioma você quer estudar?</legend>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {languages.map(([code, name]) => (
              <label
                key={code}
                className={`cursor-pointer rounded-lg border p-4 text-sm font-medium ${
                  language === code
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-border bg-surface"
                }`}
              >
                <input
                  className="sr-only"
                  type="radio"
                  name="language"
                  value={code}
                  checked={language === code}
                  onChange={() => setLanguage(code)}
                />
                {name}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="grid gap-6 sm:grid-cols-2">
          <label className="grid gap-2 text-sm font-medium">
            Como você avalia seu nível?
            <select
              className="min-h-11 rounded-lg border border-border bg-surface px-3"
              value={level}
              onChange={(e) => setLevel(e.target.value)}
            >
              <option value="iniciante">Iniciante</option>
              <option value="basico">Básico</option>
              <option value="intermediario">Intermediário</option>
              <option value="avancado">Avançado</option>
              <option value="nao-sei">Não sei</option>
            </select>
          </label>
          <label className="grid gap-2 text-sm font-medium">
            Objetivo principal
            <select
              className="min-h-11 rounded-lg border border-border bg-surface px-3"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
            >
              <option>Conversar com confiança</option>
              <option>Viajar</option>
              <option>Trabalho e carreira</option>
              <option>Estudos e provas</option>
              <option>Consumir cultura</option>
            </select>
          </label>
        </div>
        <fieldset>
          <legend className="section-title">Quanto tempo por dia?</legend>
          <div className="mt-4 flex flex-wrap gap-2">
            {[10, 20, 30, 45].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setMinutes(value)}
                className={`min-h-11 rounded-lg border px-5 text-sm font-semibold ${
                  minutes === value
                    ? "border-primary bg-primary text-white"
                    : "border-border bg-surface"
                }`}
              >
                {value} min
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="section-title">Quais habilidades merecem mais atenção?</legend>
          <div className="mt-4 flex flex-wrap gap-2">
            {skills.map((skill) => (
              <label
                key={skill}
                className={`cursor-pointer rounded-lg border px-4 py-3 text-sm ${
                  selectedSkills.includes(skill)
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-border bg-surface"
                }`}
              >
                <input
                  className="sr-only"
                  type="checkbox"
                  checked={selectedSkills.includes(skill)}
                  onChange={() => toggleSkill(skill)}
                />
                {skill}
              </label>
            ))}
          </div>
        </fieldset>
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        {success && (
          <p role="status" className="text-sm text-success">
            Plano criado com sucesso. Abrindo seu painel…
          </p>
        )}
        <div className="flex justify-end border-t border-border pt-6">
          <Button loading={loading || success} onClick={finish} disabled={loading || success}>
            Criar meu plano
          </Button>
        </div>
      </div>
    </div>
  );
}
