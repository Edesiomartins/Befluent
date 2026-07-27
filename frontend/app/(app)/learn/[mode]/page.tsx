"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { AudioPlayer, Chat, Recorder } from "@/components/study";
import { Button, EmptyState, ErrorState, Loading } from "@/components/ui";

const meta: Record<string, { title: string; subtitle: string }> = {
  guided: { title: "Aula guiada", subtitle: "Situações do cotidiano · Lição 4 de 8" },
  conversation: { title: "Conversação por texto", subtitle: "Tema: viagens · Nível B1" },
  voice: { title: "Conversa por voz", subtitle: "Prática oral em modo demonstração" },
  pronunciation: { title: "Pronúncia", subtitle: "Ritmo, clareza e inteligibilidade" },
  vocabulary: { title: "Vocabulário", subtitle: "Palavras em contexto · 8 itens" },
  grammar: { title: "Gramática", subtitle: "Present perfect × simple past" },
  listening: { title: "Compreensão auditiva", subtitle: "Uma conversa no aeroporto" },
  reading: { title: "Leitura", subtitle: "Hábitos de trabalho em diferentes culturas" },
  writing: { title: "Escrita", subtitle: "E-mail informal · 80–120 palavras" },
  review: { title: "Revisão", subtitle: "7 itens agendados para hoje" },
  assessment: { title: "Diagnóstico", subtitle: "Atualização de nível · cerca de 25 min" },
};

function PageHeader({ mode }: { mode: string }) {
  const data = meta[mode];
  return (
    <header className="mb-8">
      <Link href="/learn" className="text-sm font-medium text-text-secondary hover:text-primary">← Voltar para aprender</Link>
      <div className="mt-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div><h1 className="page-title">{data.title}</h1><p className="mt-2 text-text-secondary">{data.subtitle}</p></div>
        <span className="w-fit rounded-md bg-info/10 px-2.5 py-1.5 text-xs font-semibold text-info">Conteúdo demonstrativo</span>
      </div>
    </header>
  );
}

function Guided() {
  const [step, setStep] = useState(1);
  return <div className="grid gap-7"><div><div className="mb-2 flex justify-between text-xs text-text-secondary"><span>Progresso da aula</span><span>{step}/3</span></div><div className="h-1.5 rounded-full bg-surface-elevated"><div className="h-full rounded-full bg-primary transition-all" style={{ width: `${step * 33.33}%` }} /></div></div><section className="max-w-3xl"><p className="text-xs font-semibold uppercase tracking-[.12em] text-primary">Objetivo</p><h2 className="mt-3 text-2xl font-semibold tracking-tight">Fazer perguntas de forma natural</h2><p className="mt-4 text-lg leading-8">Em inglês, perguntas no presente normalmente usam <strong>do</strong> ou <strong>does</strong> antes do sujeito.</p><div className="mt-6 border-l-2 border-primary bg-surface px-5 py-4"><p className="font-medium">Where do you usually have lunch?</p><p className="mt-1 text-sm text-text-secondary">Onde você costuma almoçar?</p></div></section><div className="flex gap-3 border-t border-border pt-5"><Button variant="secondary" disabled={step === 1} onClick={() => setStep((s) => s - 1)}>Anterior</Button><Button onClick={() => setStep((s) => Math.min(3, s + 1))}>{step === 3 ? "Concluir aula" : "Continuar"}</Button></div></div>;
}

function Conversation() {
  const [translation, setTranslation] = useState(false);
  return <div><div className="mb-4 flex flex-wrap items-center gap-4 text-sm"><label>Tema <select className="ml-2 rounded-lg border border-border bg-surface px-3 py-2"><option>Viagens</option><option>Trabalho</option><option>Cultura</option></select></label><label>Correção <select className="ml-2 rounded-lg border border-border bg-surface px-3 py-2"><option>Após cada resposta</option><option>Ao final</option><option>Somente quando eu pedir</option></select></label><label className="ml-auto flex items-center gap-2"><input type="checkbox" checked={translation} onChange={(e) => setTranslation(e.target.checked)} className="accent-[var(--primary)]" /> Tradução opcional</label></div><Chat />{translation && <p className="mt-3 text-sm text-text-secondary">Traduções aparecem abaixo das mensagens do tutor quando solicitadas.</p>}</div>;
}

function Voice() {
  const [transcript, setTranscript] = useState("");
  return <div className="grid gap-5 md:grid-cols-[.85fr_1.15fr]"><div><Recorder onTranscript={setTranscript} /><p className="mt-3 rounded-lg bg-warning/10 p-3 text-xs leading-5 text-warning">Modo demonstração: a transcrição é simulada. O provedor de voz definitivo ainda não foi escolhido.</p></div><div className="panel p-5"><h2 className="section-title">Transcrição</h2><textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} placeholder="Sua fala aparecerá aqui. Você também pode digitar como alternativa." className="mt-4 min-h-32 w-full resize-y rounded-lg border border-border p-3 text-sm" /><h3 className="mt-6 text-sm font-semibold">Resposta do tutor</h3><p className="mt-2 text-sm leading-6 text-text-secondary">That is a great situation to practice. How would you ask for the menu?</p><div className="mt-4"><AudioPlayer text="That is a great situation to practice. How would you ask for the menu?" /></div></div></div>;
}

function Pronunciation() {
  const [transcript, setTranscript] = useState("");
  return <div className="grid gap-5"><div className="rounded-lg border border-info/25 bg-info/5 p-4 text-sm leading-6 text-info"><strong>Limite importante:</strong> reconhecimento de fala (STT) verifica principalmente a transcrição. Ele não substitui uma avaliação fonética especializada de sons, entonação ou sotaque.</div><div className="grid gap-5 md:grid-cols-2"><div className="panel p-5"><p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">Frase-alvo</p><p className="my-5 text-2xl font-medium">Could you tell me where the station is?</p><AudioPlayer text="Could you tell me where the station is?" /></div><Recorder onTranscript={setTranscript} /></div>{transcript && <div className="panel p-5"><h2 className="section-title">Resultado indicativo</h2><p className="mt-2 text-sm text-success">A frase foi reconhecida por completo.</p><p className="mt-3 text-sm text-text-secondary">Transcrição: {transcript}</p></div>}</div>;
}

function Vocabulary() {
  const [revealed, setRevealed] = useState(false);
  const [index, setIndex] = useState(1);
  return <div className="mx-auto max-w-2xl"><div className="mb-3 flex justify-between text-xs text-text-secondary"><span>Item {index} de 8</span><span>Revisão contextual</span></div><div className="panel min-h-80 p-7 sm:p-10"><p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">Expressão</p><h2 className="mt-5 text-3xl font-semibold tracking-tight">to figure out</h2><p className="mt-4 text-lg italic text-text-secondary">“We need to figure out a better solution.”</p>{revealed ? <div className="mt-8 border-t border-border pt-6"><p className="font-semibold">descobrir; entender; resolver</p><p className="mt-2 text-sm leading-6 text-text-secondary">Usado quando chegamos a uma resposta por reflexão ou tentativa.</p></div> : <Button className="mt-9" variant="secondary" onClick={() => setRevealed(true)}>Revelar significado</Button>}</div><div className="mt-4 flex flex-wrap justify-between gap-3"><Button variant="secondary">Difícil</Button><div className="flex gap-2"><Button variant="secondary">Ainda aprendendo</Button><Button onClick={() => { setIndex((i) => Math.min(8, i + 1)); setRevealed(false); }}>Eu sabia</Button></div></div></div>;
}

function Grammar() {
  const [answer, setAnswer] = useState(""); const [checked, setChecked] = useState(false);
  return <div className="max-w-3xl"><section><h2 className="section-title">Escolha pelo contexto</h2><p className="mt-3 leading-7 text-text-secondary">Use o present perfect quando a experiência mantém relação com o presente; use o simple past quando o tempo está encerrado ou explícito.</p></section><div className="mt-7 panel p-6"><p className="text-sm text-text-secondary">Complete a frase:</p><p className="mt-3 text-xl font-medium">I ____ to Paris three times.</p><div className="mt-5 grid gap-2">{["have been", "went", "was going"].map((option) => <label key={option} className={`rounded-lg border p-3 ${answer === option ? "border-primary bg-primary/5" : "border-border"}`}><input className="mr-3 accent-[var(--primary)]" type="radio" name="answer" checked={answer === option} onChange={() => { setAnswer(option); setChecked(false); }} />{option}</label>)}</div><Button className="mt-5" disabled={!answer} onClick={() => setChecked(true)}>Verificar resposta</Button>{checked && <p className={`mt-4 rounded-lg p-3 text-sm ${answer === "have been" ? "bg-success/10 text-success" : "bg-danger/10 text-danger"}`}>{answer === "have been" ? "Correto. Não há um tempo passado encerrado na frase." : "Quase. Como não há um momento passado específico, use “have been”."}</p>}</div></div>;
}

function Listening() {
  const [answer, setAnswer] = useState(""); const [done, setDone] = useState(false);
  return <div className="max-w-3xl"><AudioPlayer text="Attention passengers. Flight 482 to Madrid has been delayed by thirty minutes. Boarding will begin at gate sixteen." /><div className="mt-7 panel p-6"><h2 className="section-title">Por que o voo sofreu uma alteração?</h2><div className="mt-4 grid gap-2">{["O portão mudou.", "O voo está atrasado.", "O voo foi cancelado."].map((item) => <label key={item} className="rounded-lg border border-border p-3"><input className="mr-3 accent-[var(--primary)]" type="radio" checked={answer === item} onChange={() => setAnswer(item)} />{item}</label>)}</div><Button className="mt-5" disabled={!answer} onClick={() => setDone(true)}>Responder</Button>{done && <p className="mt-4 text-sm font-medium text-success">{answer === "O voo está atrasado." ? "Correto." : "Ouça novamente: “has been delayed” indica atraso."}</p>}</div></div>;
}

function Reading() {
  return <div className="grid gap-8 lg:grid-cols-[1.5fr_.7fr]"><article className="panel p-6 sm:p-9"><p className="mb-5 text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">Leitura · aproximadamente 4 min</p><h2 className="text-2xl font-semibold tracking-tight">How flexible work changed our routines</h2><div className="mt-6 space-y-5 text-[1.05rem] leading-8"><p>For many professionals, flexible work has changed more than the place where tasks are completed. It has also altered how people organize their attention, communicate with colleagues, and separate work from personal life.</p><p>Some employees value the autonomy, while others miss the spontaneous conversations of a shared office. Research suggests that the most effective arrangements depend less on a fixed model and more on clear expectations.</p></div></article><aside><h2 className="section-title">Glossário</h2><dl className="mt-4 divide-y divide-border border-y border-border text-sm"><div className="py-3"><dt className="font-semibold">altered</dt><dd className="mt-1 text-text-secondary">mudou, modificou</dd></div><div className="py-3"><dt className="font-semibold">arrangements</dt><dd className="mt-1 text-text-secondary">acordos, configurações</dd></div></dl><Button variant="secondary" className="mt-5">Responder questões</Button></aside></div>;
}

function Writing() {
  const [text, setText] = useState(""); const [sent, setSent] = useState(false);
  return <div className="max-w-4xl"><div className="border-l-2 border-primary pl-5"><h2 className="section-title">Proposta</h2><p className="mt-2 leading-7 text-text-secondary">Escreva para um amigo contando sobre uma mudança recente na sua rotina e como você se sentiu. Use entre 80 e 120 palavras.</p></div><label className="mt-7 block text-sm font-medium" htmlFor="writing">Seu texto</label><textarea id="writing" value={text} onChange={(e) => { setText(e.target.value); setSent(false); }} className="mt-2 min-h-64 w-full rounded-xl border border-border bg-surface p-5 leading-7" placeholder="Hi Alex,&#10;&#10;I wanted to tell you about…" /><div className="mt-3 flex items-center justify-between"><span className="text-xs text-text-secondary">{text.trim() ? text.trim().split(/\s+/).length : 0} palavras</span><Button disabled={!text.trim()} onClick={() => setSent(true)}>Enviar para correção</Button></div>{sent && <div className="mt-6 rounded-xl border border-success/25 bg-success/5 p-5"><h2 className="font-semibold text-success">Texto recebido</h2><p className="mt-2 text-sm leading-6 text-text-secondary">No modo conectado, a correção detalhará clareza, gramática e alternativas naturais sem reescrever sua voz.</p></div>}</div>;
}

function Review() {
  const [remaining, setRemaining] = useState(7);
  if (!remaining) return <EmptyState title="Nada pendente hoje" description="Sua fila está em dia. Novos itens aparecerão conforme o agendamento simples de revisão." action={<Link href="/learn" className="text-sm font-semibold text-primary">Escolher outra atividade</Link>} />;
  return <div className="mx-auto max-w-2xl"><div className="mb-3 flex justify-between text-sm text-text-secondary"><span>{remaining} itens restantes</span><span>Vocabulário</span></div><div className="panel p-8"><p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">Traduza para o inglês</p><p className="mt-6 text-2xl font-semibold">“Eu ainda não decidi.”</p><input className="mt-8 min-h-12 w-full rounded-lg border border-border px-4" placeholder="Digite sua resposta…" /></div><div className="mt-4 flex justify-end gap-2"><Button variant="secondary" onClick={() => setRemaining((n) => n - 1)}>Adiar</Button><Button onClick={() => setRemaining((n) => n - 1)}>Responder</Button></div></div>;
}

function Assessment() {
  const [started, setStarted] = useState(false);
  if (started) return <div className="max-w-3xl"><div className="mb-8"><div className="flex justify-between text-xs text-text-secondary"><span>Questão 1 de 12</span><span>Compreensão gramatical</span></div><div className="mt-2 h-1.5 rounded-full bg-surface-elevated"><div className="h-full w-[8%] rounded-full bg-primary" /></div></div><div className="panel p-6"><h2 className="text-xl font-semibold">Choose the sentence that sounds most natural.</h2><div className="mt-5 grid gap-2">{["I have seen her yesterday.", "I saw her yesterday.", "I was see her yesterday."].map((item) => <label key={item} className="rounded-lg border border-border p-4"><input type="radio" name="assessment" className="mr-3 accent-[var(--primary)]" />{item}</label>)}</div><Button className="mt-5">Próxima questão</Button></div></div>;
  return <div className="max-w-2xl"><h2 className="text-2xl font-semibold tracking-tight">Antes de começar</h2><p className="mt-3 leading-7 text-text-secondary">Este diagnóstico combina leitura, gramática, vocabulário e compreensão. O resultado é uma estimativa para ajustar seu plano — não uma certificação.</p><ul className="my-7 space-y-3 border-y border-border py-6 text-sm"><li>• Reserve cerca de 25 minutos.</li><li>• Responda sem usar tradutores.</li><li>• Você pode ouvir cada áudio duas vezes.</li></ul><Button onClick={() => setStarted(true)}>Iniciar diagnóstico</Button></div>;
}

const content: Record<string, () => ReactNode> = { guided: Guided, conversation: Conversation, voice: Voice, pronunciation: Pronunciation, vocabulary: Vocabulary, grammar: Grammar, listening: Listening, reading: Reading, writing: Writing, review: Review, assessment: Assessment };

export default function StudyModePage() {
  const params = useParams<{ mode: string }>();
  const mode = params.mode;
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  useEffect(() => { const timer = window.setTimeout(() => setState("ready"), 300); return () => window.clearTimeout(timer); }, [mode]);
  if (!meta[mode]) notFound();
  const Content = content[mode];
  return <div><PageHeader mode={mode} />{state === "loading" ? <Loading label={`Carregando ${meta[mode].title}`} /> : state === "error" ? <ErrorState retry={() => setState("ready")} /> : <Content />}</div>;
}
