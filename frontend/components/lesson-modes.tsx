"use client";

/**
 * Renderizadores de lição por modo de estudo.
 *
 * Extraídos da página `/learn/[mode]` para serem reusados também pelo executor
 * do cronograma (`/cronograma/dia/[id]`): os dois fluxos servem a mesma lição,
 * e duplicar estes componentes faria as duas telas divergirem com o tempo.
 */

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AudioPlayer, Chat, Recorder } from "@/components/study";
import { ObjectiveChoice } from "@/components/objective-choice";
import { SpeechCoach } from "@/components/speech-coach";
import { Button } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useActiveLanguage } from "@/hooks/use-active-language";
import type {
  ConversationLesson,
  GrammarLesson,
  GuidedLesson,
  LessonEnvelope,
  ListeningLesson,
  PronunciationLesson,
  ReadingLesson,
  ReviewLesson,
  VocabularyLesson,
  WritingFeedback,
  WritingLesson,
} from "@/types/lesson";

export async function completeLesson(lessonId: string | undefined) {
  if (!lessonId) return;
  try {
    await api(`/api/v1/lessons/${lessonId}/complete`, { method: "POST", body: {} });
  } catch {
    /* progresso é best-effort no cliente */
  }
}

/* ------------------------------------------------------------------ */
/* Modos                                                               */
/* ------------------------------------------------------------------ */

function Guided({ lesson }: { lesson: GuidedLesson }) {
  const [step, setStep] = useState(0);
  const [completing, setCompleting] = useState(false);
  const steps = lesson.steps;
  const total = steps.length + 1; // +1 para a pergunta de verificação
  const atCheck = step >= steps.length;
  const current = atCheck ? null : steps[step];
  return (
    <div className="grid gap-7">
      <div>
        <div className="mb-2 flex justify-between text-xs text-text-secondary">
          <span>Progresso da aula</span>
          <span>
            {Math.min(step + 1, total)}/{total}
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-surface-elevated">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${(Math.min(step + 1, total) / total) * 100}%` }}
          />
        </div>
      </div>
      {current ? (
        <section className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-primary">
            {current.title}
          </p>
          <p className="mt-4 text-lg leading-8">{current.explanation}</p>
          {current.example && (
            <div className="mt-6 border-l-2 border-primary bg-surface px-5 py-4">
              <p className="font-medium">{current.example}</p>
              {current.example_translation && (
                <p className="mt-1 text-sm text-text-secondary">{current.example_translation}</p>
              )}
            </div>
          )}
        </section>
      ) : (
        <section className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-primary">
            Verificação
          </p>
          <p className="mt-4 text-lg leading-8">{lesson.check_question}</p>
          <p className="mt-3 text-sm text-text-secondary">
            Explicar com as próprias palavras é o que confirma que você entendeu — é a
            técnica Feynman.
          </p>
        </section>
      )}
      <div className="flex gap-3 border-t border-border pt-5">
        <Button variant="secondary" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          Anterior
        </Button>
        {!atCheck ? (
          <Button onClick={() => setStep((s) => s + 1)}>Continuar</Button>
        ) : (
          <Link
            href="/learn"
            onClick={() => {
              setCompleting(true);
              void completeLesson(lesson.lesson_id).finally(() => setCompleting(false));
            }}
            className={`inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white shadow-[0_4px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)] ${completing ? "pointer-events-none opacity-70" : ""}`}
          >
            {completing ? "Concluindo…" : "Concluir aula"}
          </Link>
        )}
      </div>
    </div>
  );
}

function Conversation({ lesson }: { lesson: ConversationLesson }) {
  return (
    <div className="grid gap-5">
      <div className="panel p-5">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Situação
        </p>
        <p className="mt-2 font-medium">{lesson.situation}</p>
        {lesson.target_expressions.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {lesson.target_expressions.map((expression) => (
              <span
                key={expression}
                className="rounded-full bg-surface-elevated px-3 py-1 text-xs font-medium"
              >
                {expression}
              </span>
            ))}
          </div>
        )}
      </div>
      <Chat
        languageCode={lesson.language_code}
        situation={lesson.situation}
        opening={lesson.opening}
        openingTranslation={lesson.opening_translation}
        studySessionId={lesson.study_session_id}
      />
    </div>
  );
}

type TutorTurn = { reply: string };

/**
 * Conversação por voz: o aluno ouve o tutor (nunca lê a resposta dele),
 * fala, e a transcrição vira o próximo turno — mesmo backend de conversa
 * multi-turno do modo por texto (`Chat`, em `study.tsx`), só a superfície é
 * diferente. A resposta em texto do tutor (`turnText`) fica só em memória
 * do componente, usada unicamente para gerar o áudio (`AudioPlayer`); nunca
 * é renderizada como `<p>`/texto na tela — ver docs do Practice Hub sobre
 * por que a experiência é "ouça e responda", não "leia e responda".
 */
function Voice({ lesson }: { lesson: ConversationLesson }) {
  const [turnText, setTurnText] = useState(lesson.opening);
  const [turnCount, setTurnCount] = useState(0);
  const [lastHeard, setLastHeard] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ending, setEnding] = useState(false);
  const [closed, setClosed] = useState(false);
  const conversationId = useRef<string | null>(null);

  async function ensureConversation() {
    if (conversationId.current) return conversationId.current;
    const started = await api<{ id: string }>("/api/v1/conversations", {
      method: "POST",
      body: {
        language_code: lesson.language_code,
        topic: lesson.situation,
        opening: lesson.opening,
        study_session_id: lesson.study_session_id,
      },
    });
    conversationId.current = started.id;
    return started.id;
  }

  async function respond(spokenText: string) {
    const said = spokenText.trim();
    if (!said || closed || thinking) return;
    setLastHeard(said);
    setThinking(true);
    setError(null);
    try {
      const id = await ensureConversation();
      const result = await api<TutorTurn>(`/api/v1/conversations/${id}/messages`, {
        method: "POST",
        body: { text: said },
      });
      setTurnText(result.reply);
      setTurnCount((count) => count + 1);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Não foi possível continuar a conversa.",
      );
    } finally {
      setThinking(false);
    }
  }

  return (
    <div className="grid gap-5 md:grid-cols-[1.1fr_.9fr]">
      <div className="panel p-5">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Situação
        </p>
        <p className="mt-2 font-medium">{lesson.situation}</p>

        <div className="mt-6 rounded-xl bg-surface-elevated p-5 text-center">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            {turnCount === 0 ? "O tutor começou" : "O tutor respondeu"}
          </p>
          <div className="mt-4 flex justify-center">
            <AudioPlayer text={turnText} languageCode={lesson.language_code} />
          </div>
          {thinking && (
            <p className="mt-3 text-sm text-text-secondary">Preparando a resposta…</p>
          )}
        </div>

        {error && (
          <p role="alert" className="mt-4 text-sm text-danger">
            {error}
          </p>
        )}
      </div>

      <div>
        <Recorder onTranscript={(text) => void respond(text)} languageCode={lesson.language_code} />
        {lastHeard && (
          <p className="mt-3 text-center text-xs text-text-secondary">
            Você disse: <span className="italic">“{lastHeard}”</span>
          </p>
        )}
        <div className="mt-6 flex justify-end">
          <Button
            variant="secondary"
            loading={ending}
            disabled={closed}
            onClick={() => {
              setEnding(true);
              setClosed(true);
              void completeLesson(lesson.lesson_id).finally(() => setEnding(false));
            }}
          >
            {closed ? "Encerrada" : "Encerrar prática"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Pronunciation({ lesson }: { lesson: PronunciationLesson }) {
  const [phrase, setPhrase] = useState(0);
  const [phraseDone, setPhraseDone] = useState(false);
  const current = lesson.target_phrases[phrase];
  const last = phrase >= lesson.target_phrases.length - 1;

  const transferPrompt =
    lesson.language_code === "en"
      ? "Agora diga algo parecido com as suas palavras — por exemplo, discorde de uma ideia e diga o motivo."
      : "Agora diga algo parecido com as suas palavras, usando a mesma ideia da frase-modelo.";

  return (
    <div className="grid gap-5">
      <p className="rounded-xl border border-border bg-surface-elevated/60 px-4 py-3 text-sm leading-6 text-text-secondary">
        Speech Coach: o BeFluent usa a transcrição para estimar inteligibilidade — o que
        ficou claro na fala. Isso <strong>não</strong> é nota de pronúncia nem análise
        fonética.
      </p>
      {lesson.focus_sounds.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          {lesson.focus_sounds.map((sound) => (
            <div key={sound.sound} className="panel p-4">
              <p className="font-semibold text-primary">{sound.sound}</p>
              <p className="mt-2 text-sm leading-6 text-text-secondary">{sound.why_hard}</p>
              <p className="mt-2 text-sm leading-6">{sound.how_to_produce}</p>
            </div>
          ))}
        </div>
      )}
      {current && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
              Frase {phrase + 1} de {lesson.target_phrases.length}
            </p>
            <button
              type="button"
              className="text-xs font-semibold text-primary hover:underline"
              onClick={() => {
                if (last) {
                  void completeLesson(lesson.lesson_id);
                  return;
                }
                setPhrase((p) => p + 1);
                setPhraseDone(false);
              }}
            >
              {last ? "Concluir prática" : "Próxima frase"}
            </button>
          </div>
          <SpeechCoach
            key={`${lesson.lesson_id}-${phrase}-${current.phrase}`}
            targetText={current.phrase}
            translation={current.translation}
            languageCode={lesson.language_code}
            transferPrompt={transferPrompt}
            onSuccess={() => setPhraseDone(true)}
            onContinue={() => {
              if (last) {
                void completeLesson(lesson.lesson_id);
                return;
              }
              setPhrase((p) => p + 1);
              setPhraseDone(false);
            }}
          />
          {phraseDone && (
            <p className="mt-3 text-sm text-success" role="status">
              Frase compreensível nesta tentativa. Você pode seguir ou praticar de novo.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Vocabulary({ lesson }: { lesson: VocabularyLesson }) {
  const { code } = useActiveLanguage();
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [finished, setFinished] = useState(false);
  const [savedCount, setSavedCount] = useState(0);
  const item = lesson.items[index];
  const last = index >= lesson.items.length - 1;

  async function saveAndAdvance(_kind: "learning" | "known") {
    if (!item || saving) return;
    setSaving(true);
    setError("");
    try {
      await api("/api/v1/vocabulary", {
        method: "POST",
        body: {
          language_code: code,
          term: item.term,
          translation_pt: item.translation,
          notes: item.usage_note || item.example || null,
        },
      });
      setSavedCount((value) => value + 1);
      if (last) {
        void completeLesson(lesson.lesson_id);
        setFinished(true);
        return;
      }
      setIndex((current) => current + 1);
      setRevealed(false);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível salvar o item.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (finished) {
    return (
      <div className="mx-auto max-w-2xl rounded-xl border border-border bg-surface p-8 text-center">
        <h2 className="text-xl font-semibold">Vocabulário concluído</h2>
        <p className="mt-3 text-sm leading-6 text-text-secondary">
          Você salvou {savedCount}{" "}
          {savedCount === 1 ? "expressão" : "expressões"} na fila de revisão.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/learn/review"
            className="inline-flex min-h-11 items-center rounded-xl bg-primary px-4 text-sm font-semibold text-white"
          >
            Ir para revisão
          </Link>
          <Link
            href="/learn"
            className="inline-flex min-h-11 items-center rounded-xl border border-border px-4 text-sm font-semibold"
          >
            Outra prática
          </Link>
        </div>
      </div>
    );
  }

  if (!item) return null;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex justify-between text-xs text-text-secondary">
        <span>
          Item {index + 1} de {lesson.items.length}
        </span>
        <span>Nível {lesson.level}</span>
      </div>
      <div className="panel min-h-80 p-7 sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Expressão
        </p>
        <h2 className="mt-5 text-3xl font-semibold tracking-tight">{item.term}</h2>
        <p className="mt-4 text-lg italic text-text-secondary">“{item.example}”</p>
        {revealed ? (
          <div className="mt-8 border-t border-border pt-6">
            <p className="font-semibold">{item.translation}</p>
            <p className="mt-1 text-sm text-text-secondary">{item.example_translation}</p>
            <p className="mt-3 text-sm leading-6 text-text-secondary">{item.usage_note}</p>
          </div>
        ) : (
          <Button className="mt-9" variant="secondary" onClick={() => setRevealed(true)}>
            Revelar significado
          </Button>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      )}
      <div className="mt-4 flex flex-wrap justify-between gap-3">
        <Button
          variant="secondary"
          loading={saving}
          disabled={saving || !revealed}
          onClick={() => void saveAndAdvance("learning")}
        >
          Difícil · salvar
        </Button>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            loading={saving}
            disabled={saving || !revealed}
            onClick={() => void saveAndAdvance("learning")}
          >
            Ainda aprendendo
          </Button>
          <Button
            loading={saving}
            disabled={saving || !revealed}
            onClick={() => void saveAndAdvance("known")}
          >
            {last ? "Eu sabia · concluir" : "Eu sabia · salvar"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Grammar({ lesson }: { lesson: GrammarLesson }) {
  const exercise = lesson.exercises[0];
  return (
    <div className="max-w-3xl">
      <section>
        <h2 className="section-title">A lógica</h2>
        <p className="mt-3 leading-7 text-text-secondary">{lesson.explanation}</p>
        {lesson.patterns.length > 0 && (
          <ul className="mt-4 grid gap-2 text-sm">
            {lesson.patterns.map((pattern) => (
              <li key={pattern} className="border-l-2 border-primary pl-3">
                {pattern}
              </li>
            ))}
          </ul>
        )}
      </section>
      {lesson.examples.length > 0 && (
        <section className="mt-7">
          <h2 className="section-title">Exemplos</h2>
          <div className="mt-3 grid gap-3">
            {lesson.examples.map((example) => (
              <div key={example.sentence} className="panel p-4">
                <p className="font-medium">{example.sentence}</p>
                <p className="mt-1 text-sm text-text-secondary">{example.translation}</p>
              </div>
            ))}
          </div>
        </section>
      )}
      {exercise && (
        <div className="mt-7 panel p-6">
          <ObjectiveChoice
            lessonId={lesson.lesson_id}
            index={0}
            surface="grammar"
            kind="exercise"
            question={{
              prompt: exercise.prompt,
              options: exercise.options,
              answer: exercise.answer,
              rationale: exercise.rationale,
              option_rationales: exercise.option_rationales,
            }}
            onEvaluated={(feedback) => {
              if (feedback.is_correct) {
                void completeLesson(lesson.lesson_id);
              }
            }}
          />
        </div>
      )}
    </div>
  );
}

function Questions({
  questions,
  lessonId,
  surface = "reading",
}: {
  questions: Array<{
    prompt: string;
    options: string[];
    answer: string;
    rationale?: string;
    option_rationales?: Record<string, string>;
  }>;
  lessonId?: string;
  surface?: string;
}) {
  const [resolvedCount, setResolvedCount] = useState(0);
  const seen = useState(() => new Set<number>())[0];

  return (
    <div className="grid gap-5">
      {questions.map((question, index) => (
        <div key={`${question.prompt}-${index}`} className="panel p-6">
          <ObjectiveChoice
            lessonId={lessonId}
            index={index}
            surface={surface}
            kind="question"
            question={question}
            onEvaluated={() => {
              if (seen.has(index)) return;
              seen.add(index);
              const next = resolvedCount + 1;
              setResolvedCount(next);
              if (next >= questions.length) {
                void completeLesson(lessonId);
              }
            }}
          />
        </div>
      ))}
    </div>
  );
}

function Listening({ lesson }: { lesson: ListeningLesson }) {
  return (
    <div className="max-w-3xl">
      <AudioPlayer text={lesson.transcript} languageCode={lesson.language_code} />
      <p className="mt-2 text-xs text-text-secondary">
        Velocidade de fala: {lesson.speaking_rate}
      </p>
      <div className="mt-7">
        <Questions
          questions={lesson.questions}
          lessonId={lesson.lesson_id}
          surface="listening"
        />
      </div>
    </div>
  );
}

function Reading({ lesson }: { lesson: ReadingLesson }) {
  const paragraphs = useMemo(() => lesson.text.split(/\n+/).filter(Boolean), [lesson.text]);
  return (
    <div className="grid gap-8 lg:grid-cols-[1.5fr_.7fr]">
      <article className="panel p-6 sm:p-9">
        <p className="mb-5 text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Leitura · nível {lesson.level}
        </p>
        <h2 className="text-2xl font-semibold tracking-tight">{lesson.title}</h2>
        <div className="mt-6 space-y-5 text-[1.05rem] leading-8">
          {paragraphs.map((paragraph) => (
            <p key={paragraph.slice(0, 40)}>{paragraph}</p>
          ))}
        </div>
      </article>
      <aside>
        {lesson.glossary.length > 0 && (
          <>
            <h2 className="section-title">Glossário</h2>
            <dl className="mt-4 divide-y divide-border border-y border-border text-sm">
              {lesson.glossary.map((entry) => (
                <div key={entry.term} className="py-3">
                  <dt className="font-semibold">{entry.term}</dt>
                  <dd className="mt-1 text-text-secondary">{entry.translation}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
        <div className="mt-5">
          <Questions
            questions={lesson.questions}
            lessonId={lesson.lesson_id}
            surface="reading"
          />
        </div>
      </aside>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const percent = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-text-secondary tabular-nums">{percent}%</span>
      </div>
      <div className="h-2 rounded-full bg-surface-elevated">
        <div
          className={`h-full rounded-full ${percent >= 70 ? "bg-success" : percent >= 45 ? "bg-warning" : "bg-danger"}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function WritingFeedbackPanel({ feedback }: { feedback: WritingFeedback }) {
  if (feedback.status !== "assessed") {
    return (
      <div className="mt-6 rounded-xl border border-border bg-surface p-5" role="status">
        <h2 className="section-title">Não foi possível avaliar</h2>
        <p className="mt-2 text-sm leading-6 text-text-secondary">
          O texto enviado está vazio ou curto demais para qualquer análise.
        </p>
      </div>
    );
  }

  const heuristic = feedback.evaluated_by === "heuristic";
  const score = Math.round((feedback.normalized_score ?? 0) * 100);

  return (
    <div className="mt-6 grid gap-4" role="status">
      <div className="panel p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="section-title">
            {heuristic ? "Análise preliminar" : "Correção"}
          </h2>
          <span className="text-sm text-text-secondary">
            {feedback.word_count} palavras
            {feedback.within_range ? (
              <span className="ml-1 text-success">· dentro da faixa</span>
            ) : (
              <span className="ml-1 text-warning">
                · fora da faixa de {feedback.min_words}–{feedback.max_words}
              </span>
            )}
          </span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="text-3xl font-bold tabular-nums">{score}%</span>
          {feedback.estimated_level && !heuristic && (
            <span className="rounded-md bg-primary-soft px-2.5 py-1.5 text-xs font-semibold text-primary">
              Sustenta {feedback.estimated_level}
            </span>
          )}
          {heuristic && (
            <span className="rounded-md bg-warning/15 px-2.5 py-1.5 text-xs font-semibold text-warning">
              Sem correção gramatical completa
            </span>
          )}
        </div>

        {feedback.feedback && (
          <p className="mt-4 text-sm leading-6">{feedback.feedback}</p>
        )}

        {heuristic && (
          <p className="mt-4 rounded-lg bg-warning/10 p-3 text-xs leading-5 text-warning">
            Avaliação preliminar. Sem a IA conectada, o BeFluent mede extensão, segmentação
            em frases e variedade de palavras — não corrige gramática nem vocabulário.
            Isto não é uma avaliação linguística completa.
          </p>
        )}
      </div>

      {feedback.criteria.length > 0 && (
        <div className="panel grid gap-4 p-5">
          <h3 className="text-sm font-semibold">Por critério</h3>
          {feedback.criteria.map((item) => (
            <ScoreBar key={item.key} label={item.label} value={item.score} />
          ))}
        </div>
      )}

      {heuristic && feedback.metrics && (
        <div className="panel grid gap-2 p-5 text-sm">
          <h3 className="text-sm font-semibold">O que foi medido</h3>
          <div className="flex justify-between text-text-secondary">
            <span>Frases</span>
            <span className="tabular-nums">{feedback.metrics.sentences}</span>
          </div>
          <div className="flex justify-between text-text-secondary">
            <span>Palavras distintas</span>
            <span className="tabular-nums">
              {Math.round(feedback.metrics.lexical_diversity * 100)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function Writing({ lesson }: { lesson: WritingLesson }) {
  const [text, setText] = useState("");
  const [feedback, setFeedback] = useState<WritingFeedback | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const inRange = words >= lesson.min_words && words <= lesson.max_words;

  async function submit() {
    setSending(true);
    setError("");
    setFeedback(null);
    try {
      const result = await api<WritingFeedback>("/api/v1/writing", {
        method: "POST",
        body: {
          language_code: lesson.language_code,
          prompt: lesson.prompt,
          content_text: text.trim(),
          target_level: lesson.level,
          min_words: lesson.min_words,
          max_words: lesson.max_words,
        },
      });
      setFeedback(result);
      void completeLesson(lesson.lesson_id);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível enviar o texto para correção.",
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="max-w-4xl">
      <div className="border-l-2 border-primary pl-5">
        <h2 className="section-title">Proposta</h2>
        <p className="mt-2 leading-7 text-text-secondary">{lesson.prompt}</p>
        <p className="mt-2 text-xs text-text-secondary">
          Entre {lesson.min_words} e {lesson.max_words} palavras.
        </p>
      </div>
      {lesson.rubric_hints.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {lesson.rubric_hints.map((hint) => (
            <span
              key={hint}
              className="rounded-full bg-surface-elevated px-3 py-1 text-xs font-medium"
            >
              {hint}
            </span>
          ))}
        </div>
      )}
      <label className="mt-7 block text-sm font-medium" htmlFor="writing">
        Seu texto
      </label>
      <textarea
        id="writing"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setFeedback(null);
        }}
        className="mt-2 min-h-64 w-full rounded-xl border border-border bg-surface p-5 leading-7"
        placeholder="Escreva aqui…"
      />
      <div className="mt-3 flex items-center justify-between">
        <span className={`text-xs ${inRange ? "text-success" : "text-text-secondary"}`}>
          {words} palavras
        </span>
        <Button
          disabled={!text.trim()}
          loading={sending}
          onClick={() => void submit()}
        >
          {sending ? "Corrigindo…" : "Enviar para correção"}
        </Button>
      </div>
      {error && (
        <p className="mt-4 rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger" role="alert">
          {error}
        </p>
      )}
      {feedback && <WritingFeedbackPanel feedback={feedback} />}
    </div>
  );
}

function Review({ lesson }: { lesson: ReviewLesson }) {
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [finished, setFinished] = useState(false);
  const item = lesson.items[index];
  const remaining = Math.max(lesson.items.length - index, 0);
  const last = index >= lesson.items.length - 1;

  if (finished) {
    return (
      <div className="mx-auto max-w-2xl rounded-xl border border-border bg-surface p-8 text-center">
        <h2 className="text-xl font-semibold">Revisão concluída</h2>
        <p className="mt-3 text-sm text-text-secondary">
          Você passou por {lesson.items.length}{" "}
          {lesson.items.length === 1 ? "item" : "itens"} desta prática.
        </p>
        <Link
          href="/learn"
          className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-primary px-4 text-sm font-semibold text-white"
        >
          Voltar para praticar
        </Link>
      </div>
    );
  }

  if (!item) return null;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex justify-between text-sm text-text-secondary">
        <span>
          {remaining} {remaining === 1 ? "item restante" : "itens restantes"}
        </span>
        <span>Nível {lesson.level}</span>
      </div>
      <p className="mb-3 text-xs text-text-secondary">
        Prática gerada (sem fila SRS). Itens salvos no vocabulário entram na revisão real.
      </p>
      <div className="panel p-8">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Recupere da memória
        </p>
        <p className="mt-6 text-2xl font-semibold">{item.prompt}</p>
        {revealed ? (
          <div className="mt-6 border-t border-border pt-5">
            <p className="text-xl font-semibold text-primary">{item.answer}</p>
            <p className="mt-2 text-sm text-text-secondary">{item.hint}</p>
          </div>
        ) : (
          <p className="mt-4 text-sm text-text-secondary">Dica: {item.hint}</p>
        )}
      </div>
      <div className="mt-4 flex justify-end gap-2">
        {!revealed ? (
          <Button onClick={() => setRevealed(true)}>Ver resposta</Button>
        ) : (
          <Button
            onClick={() => {
              if (last) {
                setFinished(true);
                return;
              }
              setIndex((i) => i + 1);
              setRevealed(false);
            }}
          >
            {last ? "Concluir" : "Próximo item"}
          </Button>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

export function LessonContent({ mode, lesson }: { mode: string; lesson: LessonEnvelope }) {
  switch (mode) {
    case "guided":
      return <Guided lesson={lesson as GuidedLesson} />;
    case "conversation":
      return <Conversation lesson={lesson as ConversationLesson} />;
    case "voice":
      return <Voice lesson={lesson as ConversationLesson} />;
    case "pronunciation":
      return <Pronunciation lesson={lesson as PronunciationLesson} />;
    case "vocabulary":
      return <Vocabulary lesson={lesson as VocabularyLesson} />;
    case "grammar":
      return <Grammar lesson={lesson as GrammarLesson} />;
    case "listening":
      return <Listening lesson={lesson as ListeningLesson} />;
    case "reading":
      return <Reading lesson={lesson as ReadingLesson} />;
    case "writing":
      return <Writing lesson={lesson as WritingLesson} />;
    case "review":
      return <Review lesson={lesson as ReviewLesson} />;
    default:
      return null;
  }
}

