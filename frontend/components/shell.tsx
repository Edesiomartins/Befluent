"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import {
  BookOpen,
  Dumbbell,
  Flame,
  Globe,
  Home,
  LogOut,
  Menu,
  Settings,
  TrendingUp,
  User,
  X,
} from "lucide-react";
import { api, clearCsrfToken } from "@/lib/api";
import { Logo } from "@/components/logo";
import { BRAND } from "@/lib/brand";
import { useDashboardSummary } from "@/hooks/use-dashboard-summary";

const navigation = [
  { href: "/dashboard", label: "Início", icon: Home },
  { href: "/learn", label: "Prática", icon: Dumbbell },
  { href: "/languages", label: "Idiomas", icon: Globe },
  { href: "/progress", label: "Progresso", icon: TrendingUp },
];

const secondary = [
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
  const active = pathname === href || (href === "/learn" && pathname.startsWith("/learn/"));
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={`flex min-h-11 items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold transition ${
        active
          ? "bg-primary text-white shadow-[0_3px_0_var(--primary-shadow)]"
          : "text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
      }`}
      aria-current={active ? "page" : undefined}
    >
      <Icon className="size-5 shrink-0" aria-hidden />
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
      <Link href="/dashboard" className="mb-8 block px-1" onClick={onNavigate}>
        <Logo />
        <span className="mt-1 block px-0.5 text-xs text-text-secondary">{BRAND.slogan}</span>
      </Link>
      <nav className="grid gap-1.5" aria-label="Navegação principal">
        {navigation.map((item) => (
          <NavItem key={item.href} {...item} onNavigate={onNavigate} />
        ))}
      </nav>
      <nav className="mt-auto grid gap-1.5 border-t border-border pt-4" aria-label="Conta">
        {secondary.map((item) => (
          <NavItem key={item.href} {...item} onNavigate={onNavigate} />
        ))}
        <button
          type="button"
          onClick={logout}
          className="flex min-h-11 items-center gap-3 rounded-xl px-3 py-2 text-left text-sm font-semibold text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
        >
          <LogOut className="size-5 shrink-0" aria-hidden />
          Sair
        </button>
      </nav>
    </>
  );
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-border bg-[var(--surface-soft)] p-5 lg:flex">
      <SidebarContent />
    </aside>
  );
}

function StatsBar() {
  const summary = useDashboardSummary();
  if (!summary) return null;
  return (
    <div className="flex items-center gap-2">
      <span
        className="stat-pill border-[var(--streak-soft)] bg-[var(--streak-soft)] text-[var(--streak-shadow)]"
        title="Sequência de dias estudando"
      >
        <Flame className="size-4 fill-current" aria-hidden />
        {summary.streak_days}
      </span>
      <span
        className="hidden stat-pill border-[var(--violet-soft)] bg-[var(--violet-soft)] text-[var(--violet)] sm:inline-flex"
        title="Palavras aprendidas"
      >
        <BookOpen className="size-4" aria-hidden />
        {summary.vocabulary_items}
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
      <header className="flex h-16 items-center justify-between border-b border-border bg-surface/90 px-5 backdrop-blur md:px-8">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-xl border border-border lg:hidden"
            aria-expanded={open}
            aria-controls={panelId}
            aria-label={open ? "Fechar menu" : "Abrir menu"}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X className="size-5" aria-hidden /> : <Menu className="size-5" aria-hidden />}
          </button>
          <div className="hidden sm:block">
            <p className="text-xs font-medium uppercase tracking-[.12em] text-text-secondary">
              Área de estudo
            </p>
            <p className="text-sm font-semibold">{BRAND.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <StatsBar />
          <Link
            href="/onboarding"
            className="hidden rounded-xl px-3 py-2 text-sm font-semibold text-primary hover:bg-primary-soft sm:inline-flex"
          >
            Onboarding
          </Link>
        </div>
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
      className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-border bg-surface px-2 pb-[env(safe-area-inset-bottom)] lg:hidden"
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
  const active = pathname === href || (href === "/learn" && pathname.startsWith("/learn/"));
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
