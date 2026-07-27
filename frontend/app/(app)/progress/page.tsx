export default function ProgressPage() {
  const skills = [["Conversação", 62], ["Compreensão auditiva", 54], ["Vocabulário", 71], ["Gramática", 48], ["Leitura", 66], ["Escrita", 43]];
  return (
    <div>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-semibold text-primary">Acompanhamento</p><h1 className="mt-2 page-title">Seu progresso</h1><p className="mt-3 text-text-secondary">Tendências úteis, sem transformar aprendizado em uma falsa precisão.</p></div><label className="text-sm font-medium">Idioma <select className="ml-2 rounded-lg border border-border bg-surface px-3 py-2"><option>Inglês</option></select></label></div>
      <section className="mt-9 grid gap-6 border-y border-border py-7 sm:grid-cols-3">
        <div><p className="text-sm text-text-secondary">Tempo total</p><p className="mt-2 text-3xl font-semibold tracking-tight">18h 42min</p><p className="mt-1 text-xs text-success">+2h 15min este mês</p></div>
        <div><p className="text-sm text-text-secondary">Sessões concluídas</p><p className="mt-2 text-3xl font-semibold tracking-tight">64</p><p className="mt-1 text-xs text-text-secondary">Média de 17 min</p></div>
        <div><p className="text-sm text-text-secondary">Vocabulário ativo</p><p className="mt-2 text-3xl font-semibold tracking-tight">386</p><p className="mt-1 text-xs text-text-secondary">42 em consolidação</p></div>
      </section>
      <div className="mt-9 grid gap-9 lg:grid-cols-[1fr_.8fr]">
        <section><h2 className="section-title">Desenvolvimento por habilidade</h2><p className="mt-2 text-sm text-text-secondary">Estimativa relativa baseada nas atividades recentes.</p><div className="mt-6 space-y-5">{skills.map(([name, value]) => <div key={name as string}><div className="mb-2 flex justify-between text-sm"><span>{name}</span><span className="text-text-secondary">{value}%</span></div><div className="h-2 rounded-full bg-surface-elevated"><div className="h-full rounded-full bg-primary" style={{ width: `${value}%` }} /></div></div>)}</div></section>
        <section className="lg:border-l lg:border-border lg:pl-8"><h2 className="section-title">Atividade recente</h2><div className="mt-4 divide-y divide-border border-y border-border">{[["Hoje", "Aula guiada", "24 min"], ["Ontem", "Conversação", "18 min"], ["25 jul", "Revisão", "11 min"], ["23 jul", "Compreensão auditiva", "16 min"]].map(([date, activity, time]) => <div key={`${date}-${activity}`} className="grid grid-cols-[4rem_1fr_auto] gap-3 py-4 text-sm"><span className="text-text-secondary">{date}</span><span className="font-medium">{activity}</span><span className="text-text-secondary">{time}</span></div>)}</div></section>
      </div>
    </div>
  );
}
