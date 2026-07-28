"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";
import { CEFR_LEVELS, LEVEL_DETAILS, type CefrLevel } from "@/lib/levels";

const languages = [
  ["en", "Inglês"],
  ["es-ES", "Espanhol da Espanha"],
  ["fr", "Francês"],
  ["ja", "Japonês"],
  ["zh-CN", "Mandarim"],
];

type LevelChoice = "beginner" | "take_test" | "self_declared" | "later";

const levelChoices: { value: LevelChoice; label: string; hint: string }[] = [
  {
    value: "beginner",
    label: "Sou iniciante absoluto",
    hint: "Você começará do Pré-A1, do zero.",
  },
  {
    value: "take_test",
    label: "Quero fazer o teste de nível",
    hint: "Cerca de 15 minutos, com resultado por competência.",
  },
  {
    value: "self_declared",
    label: "Prefiro informar meu nível",
    hint: "Você escolhe o nível e pode ajustar depois.",
  },
  {
    value: "later",
    label: "Fazer o teste depois",
    hint: "Seu nível fica pendente até você avaliar.",
  },
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
  const [levelChoice, setLevelChoice] = useState<LevelChoice>("take_test");
  const [cefrLevel, setCefrLevel] = useState<CefrLevel>("A2");
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
          level_choice: levelChoice,
          cefr_level: levelChoice === "self_declared" ? cefrLevel : null,
          goal,
          minutes_per_day: minutes,
          skills: selectedSkills,
        },
      });

      if (levelChoice === "take_test") {
        // Cria a sessão de teste antes de navegar: falha aqui é erro real,
        // não pode virar redirecionamento silencioso para o dashboard.
        const test = await api<{ id: string }>("/api/v1/placement-tests", {
          method: "POST",
          body: { language_code: language, declared_beginner: false },
        });
        setSuccess(true);
        router.replace(`/placement-test/${test.id}`);
        return;
      }

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
                className={`cursor-pointer rounded-xl border-2 p-4 text-sm font-semibold transition ${
                  language === code
                    ? "border-primary bg-primary-soft text-primary"
                    : "border-border bg-surface hover:border-primary/40"
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
        <fieldset>
          <legend className="section-title">Você já sabe qual é o seu nível?</legend>
          <p className="mt-2 text-sm text-text-secondary">
            O BeFluent usa o padrão CEFR (Pré-A1 a C2). O resultado do teste é uma
            estimativa, não uma certificação oficial.
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {levelChoices.map((choice) => (
              <label
                key={choice.value}
                className={`cursor-pointer rounded-xl border-2 p-4 transition ${
                  levelChoice === choice.value
                    ? "border-primary bg-primary-soft"
                    : "border-border bg-surface hover:border-primary/40"
                }`}
              >
                <input
                  className="sr-only"
                  type="radio"
                  name="level_choice"
                  value={choice.value}
                  checked={levelChoice === choice.value}
                  onChange={() => setLevelChoice(choice.value)}
                />
                <span
                  className={`block text-sm font-semibold ${
                    levelChoice === choice.value ? "text-primary" : ""
                  }`}
                >
                  {choice.label}
                </span>
                <span className="mt-1 block text-sm text-text-secondary">{choice.hint}</span>
              </label>
            ))}
          </div>
          {levelChoice === "self_declared" && (
            <label className="mt-4 grid gap-2 text-sm font-medium">
              Qual é o seu nível?
              <select
                className="min-h-11 rounded-xl border-2 border-border bg-surface px-3"
                value={cefrLevel}
                onChange={(e) => setCefrLevel(e.target.value as CefrLevel)}
              >
                {CEFR_LEVELS.map((code) => (
                  <option key={code} value={code}>
                    {LEVEL_DETAILS[code].name}
                  </option>
                ))}
              </select>
              <span className="text-sm font-normal text-text-secondary">
                {LEVEL_DETAILS[cefrLevel].description}
              </span>
            </label>
          )}
        </fieldset>
        <label className="grid max-w-md gap-2 text-sm font-medium">
          Objetivo principal
          <select
            className="min-h-11 rounded-xl border-2 border-border bg-surface px-3"
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
        <fieldset>
          <legend className="section-title">Quanto tempo por dia?</legend>
          <div className="mt-4 flex flex-wrap gap-2">
            {[10, 20, 30, 45].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setMinutes(value)}
                className={`min-h-11 rounded-xl border-2 px-5 text-sm font-bold transition ${
                  minutes === value
                    ? "border-primary bg-primary text-white shadow-[0_3px_0_var(--primary-shadow)]"
                    : "border-border bg-surface hover:border-primary/40"
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
                className={`cursor-pointer rounded-xl border-2 px-4 py-3 text-sm font-medium transition ${
                  selectedSkills.includes(skill)
                    ? "border-primary bg-primary-soft text-primary"
                    : "border-border bg-surface hover:border-primary/40"
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
            {levelChoice === "take_test"
              ? "Plano criado. Abrindo seu teste de nível…"
              : "Plano criado com sucesso. Abrindo seu painel…"}
          </p>
        )}
        <div className="flex justify-end border-t border-border pt-6">
          <Button loading={loading || success} onClick={finish} disabled={loading || success}>
            {levelChoice === "take_test" ? "Criar plano e iniciar teste" : "Criar meu plano"}
          </Button>
        </div>
      </div>
    </div>
  );
}
