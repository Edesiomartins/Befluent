import { BarChart3, Clock, Trophy } from "lucide-react";
import { modeColorClasses } from "@/lib/modes";

export default function ProgressPage() {
  const skills = [["Conversação", 62], ["Compreensão auditiva", 54], ["Vocabulário", 71], ["Gramática", 48], ["Leitura", 66], ["Escrita", 43]];
  const stats = [
    { icon: Clock, color: "primary", label: "Tempo total", value: "18h 42min", hint: "+2h 15min este mês" },
    { icon: Trophy, color: "gold", label: "Sessões concluídas", value: "64", hint: "Média de 17 min" },
    { icon: BarChart3, color: "violet", label: "Vocabulário ativo", value: "386", hint: "42 em consolidação" },
  ] as const;
  return (
    <div>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-semibold text-primary">Acompanhamento</p><h1 className="mt-2 page-title">Seu progresso</h1><p className="mt-3 text-text-secondary">Tendências úteis, sem transformar aprendizado em uma falsa precisão.</p></div><label className="text-sm font-medium">Idioma <select className="ml-2 rounded-xl border-2 border-border bg-surface px-3 py-2"><option>Inglês</option></select></label></div>
      <section className="mt-8 grid gap-4 sm:grid-cols-3">
        {stats.map(({ icon: Icon, color, label, value, hint }) => {
          const colors = modeColorClasses[color];
          return (
            <div key={label} className="panel p-5">
              <span className={`grid size-11 place-items-center rounded-xl ${colors.bg} ${colors.text}`}>
                <Icon className="size-5" aria-hidden />
              </span>
              <p className="mt-4 text-sm text-text-secondary">{label}</p>
              <p className="mt-1 text-3xl font-bold tracking-tight">{value}</p>
              <p className="mt-1 text-xs text-success">{hint}</p>
            </div>
          );
        })}
      </section>
      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_.8fr]">
        <section className="panel p-6"><h2 className="section-title">Desenvolvimento por habilidade</h2><p className="mt-2 text-sm text-text-secondary">Estimativa relativa baseada nas atividades recentes.</p><div className="mt-6 space-y-5">{skills.map(([name, value]) => <div key={name as string}><div className="mb-2 flex justify-between text-sm"><span>{name}</span><span className="text-text-secondary">{value}%</span></div><div className="h-2.5 rounded-full bg-surface-elevated"><div className="h-full rounded-full bg-primary" style={{ width: `${value}%` }} /></div></div>)}</div></section>
        <section className="panel p-6"><h2 className="section-title">Atividade recente</h2><div className="mt-4 divide-y divide-border">{[["Hoje", "Aula guiada", "24 min"], ["Ontem", "Conversação", "18 min"], ["25 jul", "Revisão", "11 min"], ["23 jul", "Compreensão auditiva", "16 min"]].map(([date, activity, time]) => <div key={`${date}-${activity}`} className="grid grid-cols-[4rem_1fr_auto] gap-3 py-4 text-sm first:pt-0 last:pb-0"><span className="text-text-secondary">{date}</span><span className="font-medium">{activity}</span><span className="text-text-secondary">{time}</span></div>)}</div></section>
      </div>
    </div>
  );
}
