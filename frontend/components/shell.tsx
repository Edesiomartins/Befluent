"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, CalendarDays, ChevronDown, Compass, Globe, Home, LogOut, Menu, Settings, SlidersHorizontal, TrendingUp, User, Users, X } from "lucide-react";
import { api, clearCsrfToken } from "@/lib/api";
import { useFocusSession } from "@/components/focus-session";
import { Logo } from "@/components/logo";

const navigation = [
  { href: "/dashboard", label: "Hoje", icon: Home },
  { href: "/cronograma", label: "Meu plano", icon: CalendarDays },
  { href: "/learn", label: "Praticar", icon: Compass },
  { href: "/progress", label: "Progresso", icon: TrendingUp },
];
const mobileNavigation = [
  { href: "/dashboard", label: "Hoje", icon: Home },
  { href: "/learn", label: "Aprender", icon: Compass },
  { href: "/progress", label: "Progresso", icon: TrendingUp },
  { href: "/profile", label: "Perfil", icon: User },
];
const secondary = [
  { href: "/languages", label: "Idiomas", icon: Globe },
  { href: "/onboarding", label: "Ajustar plano", icon: SlidersHorizontal },
  { href: "/settings", label: "Configurações", icon: Settings },
  { href: "/profile", label: "Perfil", icon: User },
];
function NavItem({ href, label, icon: Icon, onNavigate }: {
  href: string; label: string; icon: typeof Home; onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href + "/"));
  return (
    <Link
      href={href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={`group relative flex min-h-10 items-center gap-3 rounded-[10px] px-3 py-2 text-sm transition-all ${
        active
          ? "bg-white/11 font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]"
          : "font-medium text-[var(--command-muted)] hover:bg-white/[0.05] hover:text-white"
      }`}
    >
      {active && (
        <span
          aria-hidden
          className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-primary"
        />
      )}
      <Icon
        className={`size-4.5 shrink-0 transition-colors ${
          active ? "text-[#60a5fa]" : "text-[var(--command-muted)] group-hover:text-white"
        }`}
        aria-hidden
      />
      {label}
    </Link>
  );
}
function useIsAdmin() {
  const [isAdmin, setIsAdmin] = useState(false);
  useEffect(() => {
    let alive = true;
    api<{ is_admin?: boolean }>("/api/v1/auth/me")
      .then((me) => {
        if (alive) setIsAdmin(me?.is_admin === true);
      })
      .catch(() => {
        if (alive) setIsAdmin(false);
      });
    return () => {
      alive = false;
    };
  }, []);
  return isAdmin;
}
function UserCorner() {
  const isAdmin = useIsAdmin();
  return (
    <div className="flex shrink-0 items-center gap-2.5">
      {isAdmin && (
        <Link
          href="/admin"
          className="inline-flex min-h-9 items-center rounded-[10px] bg-primary px-3 text-xs font-semibold text-white shadow-[0_1px_2px_rgba(15,23,42,0.12)] hover:bg-[var(--primary-hover)]"
        >
          Administrar
        </Link>
      )}
      <Link
        href="/profile"
        aria-label="Seu perfil"
        className="grid size-10 place-items-center rounded-full border border-border bg-surface text-text-secondary shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-colors hover:border-[var(--border-strong)] hover:text-primary"
      >
        <User className="size-4.5" aria-hidden />
      </Link>
    </div>
  );
}
function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const router = useRouter();
  const [logoutError, setLogoutError] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const isAdmin = useIsAdmin();
  const accountLinks = isAdmin
    ? [...secondary, { href: "/admin", label: "Usuários", icon: Users }]
    : secondary;
  async function logout() {
    setLeaving(true);
    setLogoutError(false);
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
      clearCsrfToken();
      onNavigate?.();
      router.replace("/login");
      router.refresh();
    } catch {
      setLogoutError(true);
    } finally {
      setLeaving(false);
    }
  }
  return (
    <>
      <div className="mb-7 flex items-center justify-between px-2.5">
        <Link href="/dashboard" onClick={onNavigate} aria-label="BeFluent — Hoje">
          <Logo variant="light" />
        </Link>
      </div>
      <p className="mb-2 px-3 text-[0.72rem] font-semibold tracking-[0.02em] text-[var(--command-muted)]">
        Seu espaço de aprendizado
      </p>
      <nav className="grid gap-1" aria-label="Navegação principal">
        {navigation.map((item) => (
          <NavItem key={item.href} {...item} onNavigate={onNavigate} />
        ))}
      </nav>
      <div className="my-6 rounded-xl border border-[var(--command-border)] bg-white/[0.03] p-3.5">
        <span className="mb-2 block h-0.5 w-6 rounded-full bg-primary" />
        <p className="text-xs leading-5 text-[var(--command-muted)]">
          Um pouco hoje.
          <br />
          Mais possibilidades amanhã.
        </p>
      </div>
      <nav
        className="mt-auto grid gap-1 border-t border-[var(--command-border)] pt-4"
        aria-label="Conta"
      >
        {accountLinks.map((item) => (
          <NavItem key={item.href} {...item} onNavigate={onNavigate} />
        ))}
        <button
          type="button"
          onClick={logout}
          disabled={leaving}
          className="flex min-h-10 items-center gap-3 rounded-[10px] px-3 py-2 text-left text-sm font-medium text-[var(--command-muted)] transition-colors hover:bg-white/[0.05] hover:text-white disabled:opacity-50"
        >
          <LogOut className="size-4.5" aria-hidden />
          {leaving ? "Saindo…" : "Sair"}
        </button>
        {logoutError && (
          <p role="alert" className="px-3 text-xs text-[#fca5a5]">
            Não foi possível sair. Tente novamente.
          </p>
        )}
      </nav>
    </>
  );
}
export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col overflow-y-auto border-r border-[var(--command-border)] bg-[var(--command-bg)] px-3.5 py-6 text-[var(--command-text)] lg:flex">
      <SidebarContent />
    </aside>
  );
}

type ActiveLanguage = { code: string; name_pt: string; active: boolean };
function LanguageContext() {
  const pathname = usePathname();
  const [language, setLanguage] = useState<ActiveLanguage | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    let request = 0;
    async function load() {
      const current = ++request;
      setLoading(true);
      setLanguage(null);
      try {
        const languages = await api<ActiveLanguage[]>("/api/v1/languages/mine");
        if (alive && current === request) setLanguage(languages.find((item) => item.active) ?? null);
      } catch {
        if (alive && current === request) setLanguage(null);
      } finally {
        if (alive && current === request) setLoading(false);
      }
    }
    void load();
    const changed = () => {
      void load();
    };
    window.addEventListener("befluent:language-changed", changed);
    return () => {
      alive = false;
      window.removeEventListener("befluent:language-changed", changed);
    };
  }, [pathname]);
  return (
    <Link
      href="/languages"
      className="inline-flex min-h-10 min-w-0 items-center gap-2 rounded-full border border-border bg-surface px-3.5 py-1.5 text-sm font-semibold shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--surface-soft)]"
      aria-label={
        language
          ? language.name_pt + " — Trocar idioma"
          : loading
            ? "Carregando idioma"
            : "Escolher idioma"
      }
    >
      <Globe className="size-4 shrink-0 text-primary" aria-hidden />
      <span className="truncate text-language-accent">
        {loading ? "Carregando…" : language?.name_pt ?? "Escolher idioma"}
      </span>
      <ChevronDown className="size-3.5 shrink-0 text-text-secondary" aria-hidden />
    </Link>
  );
}

export function Header() {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open) return;
    const returnFocus = trigger.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusables = () =>
      Array.from(
        panel.current?.querySelectorAll<HTMLElement>(
          'a[href],button:not([disabled]),input,select,textarea,[tabindex="0"]',
        ) ?? [],
      );
    focusables()[0]?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
      }
      if (event.key === "Tab") {
        const items = focusables();
        const first = items[0],
          last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    }
    const onResize = () => {
      if (window.innerWidth >= 1024) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
      returnFocus?.focus();
    };
  }, [open]);
  return (
    <>
      <header className="sticky top-0 z-10 flex min-h-16 items-center justify-between gap-3 border-b border-border/90 bg-surface/85 px-5 backdrop-blur-md md:px-8">
        <div className="flex min-w-0 items-center gap-2.5">
          <button
            ref={trigger}
            type="button"
            className="grid size-10 shrink-0 place-items-center rounded-[10px] border border-border bg-surface text-text-primary hover:bg-[var(--surface-soft)] lg:hidden"
            aria-expanded={open}
            aria-controls={panelId}
            aria-label="Abrir menu"
            onClick={() => setOpen(true)}
          >
            <Menu className="size-4.5" aria-hidden />
          </button>
          <LanguageContext />
        </div>
        <UserCorner />
      </header>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div
            className="absolute inset-0 bg-[#0b1220]/60 backdrop-blur-[2px]"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <aside
            ref={panel}
            id={panelId}
            className="absolute inset-y-0 left-0 flex w-[min(19rem,90vw)] flex-col overflow-y-auto border-r border-[var(--command-border)] bg-[var(--command-bg)] p-5 text-[var(--command-text)] shadow-2xl"
          >
            <button
              type="button"
              aria-label="Fechar menu"
              onClick={() => setOpen(false)}
              className="mb-4 grid size-10 place-items-center self-end rounded-[10px] text-[var(--command-muted)] hover:bg-white/10 hover:text-white"
            >
              <X className="size-5" aria-hidden />
            </button>
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}
    </>
  );
}
export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-border bg-surface/95 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur-md lg:hidden"
      aria-label="Navegação móvel"
    >
      {mobileNavigation.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href + "/"));
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`relative flex min-h-15 flex-col items-center justify-center gap-1 px-1 py-2 text-xs font-semibold transition-colors ${
              active ? "text-primary" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {active && (
              <span aria-hidden className="absolute top-0 h-0.5 w-8 rounded-b-full bg-primary" />
            )}
            <Icon className="size-4.5" aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
export function AppShell({ children, tutor }: { children: ReactNode; tutor?: ReactNode }) {
  const pathname = usePathname();
  const { active: sessionFocus } = useFocusSession();
  const languagePicker = pathname === "/languages";
  const focus =
    /^\/learn\/(?!objetivo(?:\/|$))[^/]+\/?$/.test(pathname) ||
    /^\/cronograma\/dia\/[^/]+\/?$/.test(pathname) ||
    /^\/placement-test\/[^/]+\/?$/.test(pathname);
  const assessment = pathname.startsWith("/placement-test/");
  const practice = pathname.startsWith("/learn/");
  if (sessionFocus) {
    return (
      <main id="main-content" tabIndex={-1} className="min-h-screen bg-background">
        {children}
      </main>
    );
  }
  return (
    <>
      <a href="#main-content" className="skip-link">
        Pular para o conteúdo
      </a>
      {languagePicker ? (
        <>
          <header className="border-b border-border bg-surface/90 backdrop-blur-md">
            <div className="mx-auto flex min-h-16 max-w-4xl items-center justify-between gap-4 px-5 md:px-8">
              <Link href="/dashboard" aria-label="BeFluent — Hoje">
                <Logo />
              </Link>
              <UserCorner />
            </div>
          </header>
          <main
            id="main-content"
            tabIndex={-1}
            className="mx-auto w-full max-w-4xl px-5 py-8 md:px-8 md:py-12"
          >
            {children}
          </main>
        </>
      ) : focus ? (
        <>
          <header className="sticky top-0 z-20 border-b border-[var(--command-border)] bg-[var(--command-bg)] text-[var(--command-text)]">
            <div className="mx-auto flex min-h-15 max-w-6xl items-center justify-between gap-4 px-5 md:px-8">
              <Link
                href={assessment ? "/placement-test" : practice ? "/learn" : "/cronograma"}
                className="inline-flex min-h-10 items-center gap-2 rounded-lg px-2 text-sm font-medium text-[var(--command-muted)] transition-colors hover:bg-white/5 hover:text-white"
              >
                <ArrowLeft className="size-4" aria-hidden />
                {assessment
                  ? "Voltar ao teste"
                  : practice
                    ? "Voltar à prática"
                    : "Voltar ao plano"}
              </Link>
              <span className="hidden text-xs font-semibold tracking-wide text-[var(--command-muted)] sm:block">
                {assessment ? "Seu diagnóstico" : "Seu momento de estudo"}
              </span>
              <Logo variant="light" showWordmark={false} />
            </div>
          </header>
          <main
            id="main-content"
            tabIndex={-1}
            className="study-content mx-auto w-full max-w-5xl px-5 py-8 md:px-8 md:py-10"
          >
            {children}
          </main>
        </>
      ) : (
        <>
          <Sidebar />
          <div className="min-h-screen lg:pl-64">
            <Header />
            <main
              id="main-content"
              tabIndex={-1}
              className="mx-auto w-full max-w-[1160px] px-5 py-7 pb-28 md:px-8 md:py-9 lg:pb-12"
            >
              {children}
            </main>
          </div>
          <MobileNav />
          {tutor}
        </>
      )}
    </>
  );
}
