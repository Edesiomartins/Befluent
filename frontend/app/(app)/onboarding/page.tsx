"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";
import { CEFR_LEVELS, LEVEL_DETAILS, type CefrLevel } from "@/lib/levels";

const languages = [
  ["en", "Inglês"],
  ["es-ES", "Espanhol da Espanha"],
  ["fr", "Francês"],
  ["it", "Italiano"],
  ["de", "Alemão"],
  ["ja", "Japonês"],
  ["zh-CN", "Mandarim"],
  ["la", "Latim Eclesiástico"],
  ["la-classical", "Latim Clássico"],
] as const;
type LevelChoice = "beginner" | "take_test" | "self_declared" | "later";
const levelChoices: { value: LevelChoice; label: string; hint: string }[] = [
  { value: "beginner", label: "Sou iniciante absoluto", hint: "Você começará do Pré-A1, do zero." },
  { value: "take_test", label: "Quero fazer o teste de nível", hint: "Cerca de 15 minutos, com resultado por competência." },
  { value: "self_declared", label: "Prefiro informar meu nível", hint: "Você escolhe o nível e pode ajustar depois." },
  { value: "later", label: "Fazer o teste depois", hint: "Seu nível fica pendente até você avaliar." },
];
const goals = ["Conversar com confiança", "Viajar", "Trabalho e carreira", "Estudos e provas", "Consumir cultura"];
const skills = ["Conversação", "Compreensão auditiva", "Vocabulário", "Gramática", "Leitura", "Escrita"];
const stepTitles = ["Qual idioma você quer estudar?", "Você já sabe qual é o seu nível?", "Qual é seu objetivo principal?", "Como será sua rotina?", "Revise seu plano"];

export default function OnboardingPage() {
  const router = useRouter();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [step, setStep] = useState(0);
  const [language, setLanguage] = useState("en");
  const [levelChoice, setLevelChoice] = useState<LevelChoice>("take_test");
  const [cefrLevel, setCefrLevel] = useState<CefrLevel>("A2");
  const [goal, setGoal] = useState(goals[0]);
  const [minutes, setMinutes] = useState(20);
  const [selectedSkills, setSelectedSkills] = useState(["Conversação", "Compreensão auditiva"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => { headingRef.current?.focus(); }, [step]);

  async function finish() {
    if (loading || success) return;
    setLoading(true); setError(""); setSuccess(false);
    try {
      const completed = await api<{ curriculum_day_href?: string | null }>("/api/v1/onboarding/complete", {
        method: "POST",
        body: { language_code: language, level_choice: levelChoice, cefr_level: levelChoice === "self_declared" ? cefrLevel : null, goal, minutes_per_day: minutes, skills: selectedSkills },
      });
      window.dispatchEvent(new CustomEvent("befluent:language-changed"));
      if (levelChoice === "take_test") {
        const test = await api<{ id: string }>("/api/v1/placement-tests", { method: "POST", body: { language_code: language, declared_beginner: false } });
        setSuccess(true); router.replace(`/placement-test/${test.id}`); return;
      }
      setSuccess(true);
      window.setTimeout(() => { router.replace(completed.curriculum_day_href || "/cronograma"); router.refresh(); }, 700);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Não foi possível criar seu plano. Tente novamente.");
    } finally { setLoading(false); }
  }

  function toggleSkill(skill: string) {
    setSelectedSkills((current) => current.includes(skill) ? current.filter((item) => item !== skill) : [...current, skill]);
  }

  const languageName = languages.find(([code]) => code === language)?.[1] ?? language;
  const levelName = levelChoices.find((item) => item.value === levelChoice)?.label ?? "";
  const choiceClass = (selected: boolean) => `cursor-pointer rounded-xl border-2 p-4 transition focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/30 ${selected ? "border-primary bg-primary-soft text-primary" : "border-border bg-surface hover:border-primary/40"}`;

  return (
    <div className="mx-auto max-w-3xl">
      <p className="text-sm font-semibold text-primary">Configuração inicial</p>
      <div className="mt-4" role="progressbar" aria-label="Progresso da configuração" aria-valuemin={1} aria-valuemax={5} aria-valuenow={step + 1}>
        <div className="flex justify-between text-xs font-medium text-text-secondary"><span>Etapa {step + 1} de 5</span><span>{Math.round(((step + 1) / 5) * 100)}%</span></div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-elevated"><div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${((step + 1) / 5) * 100}%` }} /></div>
      </div>

      <section className="mt-8" aria-labelledby="onboarding-step-title">
        <h1 id="onboarding-step-title" ref={headingRef} tabIndex={-1} className="page-title outline-none">{stepTitles[step]}</h1>
        {step === 0 && <fieldset className="mt-6"><legend className="sr-only">Idioma</legend><div className="grid gap-2 sm:grid-cols-2">{languages.map(([code, name]) => <label key={code} className={choiceClass(language === code)}><input className="sr-only" type="radio" name="language" value={code} checked={language === code} onChange={() => setLanguage(code)} />{name}</label>)}</div></fieldset>}

        {step === 1 && <><p className="mt-3 text-sm text-text-secondary">O padrão CEFR ajuda a calibrar o início. O resultado do teste é uma estimativa, não uma certificação oficial.</p><fieldset className="mt-6"><legend className="sr-only">Nível atual</legend><div className="grid gap-2 sm:grid-cols-2">{levelChoices.map((choice) => <label key={choice.value} className={choiceClass(levelChoice === choice.value)}><input className="sr-only" type="radio" name="level_choice" value={choice.value} checked={levelChoice === choice.value} onChange={() => setLevelChoice(choice.value)} /><span className="block text-sm font-semibold">{choice.label}</span><span className="mt-1 block text-sm text-text-secondary">{choice.hint}</span></label>)}</div>{levelChoice === "self_declared" && <label className="mt-4 grid gap-2 text-sm font-medium">Qual é o seu nível?<select className="min-h-11 rounded-xl border-2 border-border bg-surface px-3" value={cefrLevel} onChange={(e) => setCefrLevel(e.target.value as CefrLevel)}>{CEFR_LEVELS.map((code) => <option key={code} value={code}>{LEVEL_DETAILS[code].name}</option>)}</select><span className="font-normal text-text-secondary">{LEVEL_DETAILS[cefrLevel].description}</span></label>}</fieldset></>}

        {step === 2 && <fieldset className="mt-6"><legend className="sr-only">Objetivo principal</legend><div className="grid gap-2 sm:grid-cols-2">{goals.map((item) => <label key={item} className={choiceClass(goal === item)}><input className="sr-only" type="radio" name="goal" checked={goal === item} onChange={() => setGoal(item)} />{item}</label>)}</div></fieldset>}

        {step === 3 && <div className="mt-6 grid gap-8"><fieldset><legend className="section-title">Quanto tempo por dia?</legend><div className="mt-4 flex flex-wrap gap-2">{[10, 20, 30, 45].map((value) => <button key={value} type="button" aria-pressed={minutes === value} onClick={() => setMinutes(value)} className={`min-h-11 rounded-xl border-2 px-5 text-sm font-bold focus-visible:ring-2 focus-visible:ring-primary ${minutes === value ? "border-primary bg-primary text-white" : "border-border bg-surface"}`}>{value} min</button>)}</div></fieldset><fieldset><legend className="section-title">Quais habilidades merecem mais atenção?</legend><div className="mt-4 flex flex-wrap gap-2">{skills.map((skill) => <label key={skill} className={`cursor-pointer rounded-xl border-2 px-4 py-3 text-sm font-medium focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/30 ${selectedSkills.includes(skill) ? "border-primary bg-primary-soft text-primary" : "border-border bg-surface"}`}><input className="sr-only" type="checkbox" checked={selectedSkills.includes(skill)} onChange={() => toggleSkill(skill)} />{skill}</label>)}</div></fieldset></div>}

        {step === 4 && <div className="panel mt-6 divide-y divide-border px-6"><p className="py-4"><span className="label block">Idioma</span><span className="mt-1 block font-semibold">{languageName}</span></p><p className="py-4"><span className="label block">Nível</span><span className="mt-1 block font-semibold">{levelChoice === "self_declared" ? `${levelName} · ${cefrLevel}` : levelName}</span></p><p className="py-4"><span className="label block">Objetivo</span><span className="mt-1 block font-semibold">{goal}</span></p><p className="py-4"><span className="label block">Rotina</span><span className="mt-1 block font-semibold">{minutes} min por dia · {selectedSkills.join(", ") || "sem prioridade específica"}</span></p></div>}

        {error && <p role="alert" className="mt-5 text-sm text-danger">{error}</p>}
        {success && <p role="status" className="mt-5 text-sm text-success">{levelChoice === "take_test" ? "Plano criado. Abrindo seu teste de nível…" : "Plano criado. Abrindo seu caminho de estudo…"}</p>}
        <div className="mt-8 flex items-center justify-between border-t border-border pt-6">
          {step > 0 ? <Button type="button" variant="secondary" disabled={loading || success} onClick={() => setStep((current) => current - 1)}>Voltar</Button> : <span />}
          {step < 4 ? <Button type="button" onClick={() => setStep((current) => current + 1)}>Continuar</Button> : <Button type="button" loading={loading || success} disabled={loading || success} onClick={() => void finish()}>{levelChoice === "take_test" ? "Criar plano e iniciar teste" : "Criar meu plano"}</Button>}
        </div>
      </section>
    </div>
  );
}
