"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import {
  BookOpen,
  CalendarDays,
  Dumbbell,
  Flame,
  Globe,
  Home,
  LogOut,
  Menu,
  Settings,
  SlidersHorizontal,
  TrendingUp,
  User,
  X,
} from "lucide-react";
import { api, clearCsrfToken } from "@/lib/api";
import { Logo } from "@/components/logo";
import { useDashboardSummary } from "@/hooks/use-dashboard-summary";

const navigation = [
  { href: "/dashboard", label: "Início", icon: Home },
  { href: "/cronograma", label: "Cronograma", icon: CalendarDays },
  { href: "/learn", label: "Prática", icon: Dumbbell },
  { href: "/languages", label: "Idiomas", icon: Globe },
  { href: "/progress", label: "Progresso", icon: TrendingUp },
];

const secondary = [
  { href: "/onboarding", label: "Ajustar plano", icon: SlidersHorizontal },
  { href: "/settings", label: "Configurações", icon: Settings },
  { href: "/profile", label: "Perfil", icon: User },
];

function NavItem({
  href,
  label,
  icon: Icon,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: typeof Home;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const active =
    pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={`relative flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
        active
          ? "bg-surface font-semibold text-text-primary shadow-[inset_0_0_0_1px_var(--border)] before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:rounded-full before:bg-primary"
          : "font-medium text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
      }`}
      aria-current={active ? "page" : undefined}
    >
      <Icon className={`size-[1.1rem] shrink-0 ${active ? "text-primary" : ""}`} aria-hidden />
      {label}
    </Link>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const router = useRouter();

  async function logout() {
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
    } finally {
      clearCsrfToken();
      onNavigate?.();
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <>
      <Link href="/dashboard" className="mb-7 block px-2" onClick={onNavigate}>
        <Logo />
      </Link>
      <nav className="grid gap-1" aria-label="Navegação principal">
        {navigation.map((item) => (
          <NavItem key={item.href} {...item} onNavigate={onNavigate} />
        ))}
      </nav>
      <nav className="mt-auto grid gap-1 border-t border-border pt-4" aria-label="Conta">
        {secondary.map((item) => (
          <NavItem key={item.href} {...item} onNavigate={onNavigate} />
        ))}
        <button
          type="button"
          onClick={logout}
          className="flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
        >
          <LogOut className="size-[1.1rem] shrink-0" aria-hidden />
          Sair
        </button>
      </nav>
    </>
  );
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col border-r border-border bg-[var(--surface-soft)] px-4 py-5 lg:flex">
      <SidebarContent />
    </aside>
  );
}

function StatsBar() {
  const summary = useDashboardSummary();
  if (!summary) return null;
  return (
    <div className="flex items-center gap-4 text-sm text-text-secondary">
      <span className="inline-flex items-center gap-1.5" title="Sequência de dias estudando">
        <Flame
          className={`size-4 ${summary.streak_days > 0 ? "fill-[var(--streak)] text-[var(--streak)]" : ""}`}
          aria-hidden
        />
        <span className="font-semibold tabular-nums text-text-primary">{summary.streak_days}</span>
        <span className="sr-only">dias seguidos</span>
      </span>
      <span className="hidden items-center gap-1.5 sm:inline-flex" title="Palavras aprendidas">
        <BookOpen className="size-4" aria-hidden />
        <span className="font-semibold tabular-nums text-text-primary">{summary.vocabulary_items}</span>
        <span className="sr-only">palavras</span>
      </span>
    </div>
  );
}

export function Header() {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <header className="flex h-14 items-center justify-between border-b border-border bg-background/85 px-5 backdrop-blur md:px-8 lg:justify-end">
        <div className="flex items-center gap-3 lg:hidden">
          <button
            type="button"
            className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-lg border border-border"
            aria-expanded={open}
            aria-controls={panelId}
            aria-label={open ? "Fechar menu" : "Abrir menu"}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X className="size-5" aria-hidden /> : <Menu className="size-5" aria-hidden />}
          </button>
          <Logo showWordmark={false} />
        </div>
        <StatsBar />
      </header>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button
            type="button"
            className="absolute inset-0 bg-[var(--primary-deep)]/40"
            aria-label="Fechar menu"
            onClick={() => setOpen(false)}
          />
          <aside
            id={panelId}
            className="absolute inset-y-0 left-0 flex w-[min(18rem,88vw)] flex-col bg-surface p-5 shadow-xl"
          >
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}
    </>
  );
}

export function MobileNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-surface px-2 pb-[env(safe-area-inset-bottom)] lg:hidden"
      aria-label="Navegação móvel"
    >
      {navigation.map((item) => (
        <MobileNavItem key={item.href} {...item} />
      ))}
    </nav>
  );
}

function MobileNavItem({ href, label, icon: Icon }: { href: string; label: string; icon: typeof Home }) {
  const pathname = usePathname();
  const active =
    pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));
  return (
    <Link
      href={href}
      className={`flex flex-col items-center justify-center gap-0.5 py-2.5 text-[.7rem] font-semibold transition ${
        active ? "text-primary" : "text-text-secondary"
      }`}
      aria-current={active ? "page" : undefined}
    >
      <Icon className={`size-5 ${active ? "fill-primary/15" : ""}`} aria-hidden />
      {label}
    </Link>
  );
}
