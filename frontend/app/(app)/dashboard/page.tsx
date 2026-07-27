import Link from "next/link";

export default function DashboardPage() {
  return (
    <div>
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-sm font-semibold text-primary">Segunda-feira, 27 de julho</p>
          <h1 className="page-title">Bom dia, Edesio.</h1>
          <p className="mt-3 text-text-secondary">Seu próximo passo está pronto.</p>
        </div>
        <Link href="/learn/guided" className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-[var(--primary-strong)]">Continuar estudo <span className="ml-2">→</span></Link>
      </div>

      <section className="mt-9 grid gap-6 border-y border-border py-7 md:grid-cols-[1.4fr_1fr]">
        <div className="md:border-r md:border-border md:pr-8">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">Próxima atividade</p>
          <div className="mt-4 flex items-start gap-4">
            <span className="grid size-11 shrink-0 place-items-center rounded-lg bg-primary/10 font-semibold text-primary">04</span>
            <div>
              <h2 className="text-xl font-semibold tracking-tight">Aula guiada · Situações do cotidiano</h2>
              <p className="mt-2 max-w-xl text-sm leading-6 text-text-secondary">Pratique como pedir informações e formular perguntas com naturalidade.</p>
              <div className="mt-4 flex gap-5 text-sm"><span><strong>20</strong> min</span><span><strong>B1</strong> intermediário</span></div>
            </div>
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">Hoje</p>
          <dl className="mt-4 grid grid-cols-3 gap-4">
            <div><dt className="text-xs text-text-secondary">Tempo</dt><dd className="mt-1 text-2xl font-semibold">24<span className="text-sm font-normal"> min</span></dd></div>
            <div><dt className="text-xs text-text-secondary">Sessões</dt><dd className="mt-1 text-2xl font-semibold">2</dd></div>
            <div><dt className="text-xs text-text-secondary">Revisões</dt><dd className="mt-1 text-2xl font-semibold text-warning">7</dd></div>
          </dl>
          <Link href="/learn/review" className="mt-5 inline-block text-sm font-semibold text-primary hover:underline">Revisar itens pendentes →</Link>
        </div>
      </section>

      <section className="mt-8 grid gap-8 md:grid-cols-[1.4fr_1fr]">
        <div>
          <div className="flex items-end justify-between"><div><p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">Meta semanal</p><h2 className="mt-2 section-title">82 de 120 minutos</h2></div><span className="text-sm text-text-secondary">68%</span></div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface-elevated"><div className="h-full w-[68%] rounded-full bg-primary" /></div>
          <div className="mt-5 grid grid-cols-7 gap-2 text-center text-xs text-text-secondary">
            {["S", "T", "Q", "Q", "S", "S", "D"].map((day, i) => <div key={`${day}-${i}`}><span className={`mx-auto mb-2 block size-7 rounded-full ${i < 4 ? "bg-primary" : "border border-border"}`} /><span>{day}</span></div>)}
          </div>
        </div>
        <div className="border-t border-border pt-6 md:border-l md:border-t-0 md:pl-8 md:pt-0">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">Idioma ativo</p>
          <h2 className="mt-2 text-xl font-semibold">Inglês</h2>
          <p className="mt-1 text-sm text-text-secondary">Nível B1 · 37% do plano atual</p>
          <Link href="/languages" className="mt-5 inline-block text-sm font-semibold text-primary hover:underline">Trocar idioma</Link>
        </div>
      </section>
    </div>
  );
}
