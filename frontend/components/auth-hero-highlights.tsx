import { Mic, Sparkles, TrendingUp } from "lucide-react";

const HIGHLIGHTS = [
  { icon: Mic, text: "Correção de pronúncia com IA, na hora" },
  { icon: Sparkles, text: "Trilha adaptada ao seu nível a cada aula" },
  { icon: TrendingUp, text: "Acompanhamento de progresso e streak" },
];

/** Lista de destaques do painel escuro nas telas de login/cadastro. */
export function AuthHeroHighlights() {
  return (
    <ul className="relative mt-9 grid gap-4">
      {HIGHLIGHTS.map((item) => {
        const Icon = item.icon;
        return (
          <li key={item.text} className="flex items-center gap-3 text-white/85">
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-white/10">
              <Icon className="size-4.5" aria-hidden />
            </span>
            <span className="text-sm font-medium">{item.text}</span>
          </li>
        );
      })}
    </ul>
  );
}
