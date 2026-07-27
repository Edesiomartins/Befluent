import Link from "next/link";

const modes = [
  ["guided", "Aula guiada", "Uma sequência estruturada de explicação e prática.", "20 min"],
  ["conversation", "Conversação", "Dialogue por texto com correções no momento certo.", "15 min"],
  ["voice", "Conversa por voz", "Treine fala, transcrição e compreensão oral.", "10 min"],
  ["pronunciation", "Pronúncia", "Compare sua fala e receba orientações objetivas.", "10 min"],
  ["vocabulary", "Vocabulário", "Amplie e consolide palavras em contexto.", "12 min"],
  ["grammar", "Gramática", "Estude estruturas a partir de situações reais.", "15 min"],
  ["listening", "Compreensão auditiva", "Ouça, interprete e confira seu entendimento.", "12 min"],
  ["reading", "Leitura", "Leia textos adequados ao seu nível com apoio.", "15 min"],
  ["writing", "Escrita", "Produza textos e entenda cada correção.", "20 min"],
  ["review", "Revisão", "Retome itens agendados pelo seu progresso.", "8 min"],
  ["assessment", "Diagnóstico", "Atualize a estimativa do seu nível.", "25 min"],
];

export default function LearnPage() {
  return (
    <div>
      <p className="text-sm font-semibold text-primary">Prática</p>
      <h1 className="mt-2 page-title">O que vamos praticar?</h1>
      <p className="mt-3 max-w-2xl leading-7 text-text-secondary">
        Escolha uma habilidade para trabalhar agora. Recomendações personalizadas aparecem após o onboarding.
      </p>
      <Link href="/learn/guided" className="mt-8 grid gap-5 rounded-xl bg-[var(--primary-deep)] p-6 text-white sm:grid-cols-[1fr_auto] sm:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[.14em] text-white/60">Sugestão inicial</p>
          <h2 className="mt-2 text-xl font-semibold">Aula guiada</h2>
          <p className="mt-2 text-sm leading-6 text-white/70">
            Uma sequência estruturada para começar com clareza.
          </p>
        </div>
        <span className="font-semibold">Começar →</span>
      </Link>
      <div className="mt-9 grid gap-x-8 md:grid-cols-2">
        {modes.map(([slug, title, description, duration]) => <Link href={`/learn/${slug}`} key={slug} className="group flex items-start justify-between gap-4 border-b border-border py-5"><div><h2 className="font-semibold group-hover:text-primary">{title}</h2><p className="mt-1 text-sm leading-6 text-text-secondary">{description}</p></div><span className="shrink-0 text-xs text-text-secondary">{duration}</span></Link>)}
      </div>
    </div>
  );
}
