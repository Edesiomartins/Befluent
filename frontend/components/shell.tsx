"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, CalendarDays, ChevronDown, Compass, Globe, Home, LogOut, Menu, Settings, SlidersHorizontal, TrendingUp, User, X } from "lucide-react";
import { api, clearCsrfToken } from "@/lib/api";
import { Logo } from "@/components/logo";

const navigation = [
  { href: "/dashboard", label: "Hoje", icon: Home },
  { href: "/cronograma", label: "Meu plano", icon: CalendarDays },
  { href: "/learn", label: "Praticar", icon: Compass },
  { href: "/progress", label: "Progresso", icon: TrendingUp },
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
    <Link href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
      className={`relative flex min-h-11 items-center gap-3 rounded-[10px] px-3 py-2 text-sm transition-colors ${active ? "bg-primary-soft/60 font-semibold text-primary" : "font-medium text-text-secondary hover:bg-surface-elevated hover:text-text-primary"}`}>
      <Icon className="size-5 shrink-0" aria-hidden />{label}
    </Link>
  );
}
function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const router = useRouter();
  const [logoutError, setLogoutError] = useState(false);
  const [leaving, setLeaving] = useState(false);
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
  return <>
    <Link href="/dashboard" className="mb-10 block px-3" onClick={onNavigate} aria-label="BeFluent — Hoje"><Logo /></Link>
    <p className="mb-3 px-3 text-xs font-medium text-text-secondary">Seu espaço de aprendizado</p>
    <nav className="grid gap-1.5" aria-label="Navegação principal">
      {navigation.map(item => <NavItem key={item.href} {...item} onNavigate={onNavigate} />)}
    </nav>
    <div className="my-8 px-3">
      <span className="mb-3 block h-px w-8 bg-primary/30" />
      <p className="max-w-40 text-sm leading-6 text-text-secondary">Um pouco hoje.<br />Mais possibilidades amanhã.</p>
    </div>
    <nav className="mt-auto grid gap-1 border-t border-border pt-4" aria-label="Conta">
      {secondary.map(item => <NavItem key={item.href} {...item} onNavigate={onNavigate} />)}
      <button type="button" onClick={logout} disabled={leaving}
        className="flex min-h-11 items-center gap-3 rounded-[10px] px-3 py-2 text-left text-sm text-text-secondary hover:bg-surface-elevated disabled:opacity-50">
        <LogOut className="size-5" aria-hidden />{leaving ? "Saindo…" : "Sair"}
      </button>
      {logoutError && <p role="alert" className="px-3 text-sm text-danger">Não foi possível sair. Tente novamente.</p>}
    </nav>
  </>;
}
export function Sidebar() {
  return <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col overflow-y-auto border-r border-border bg-surface px-4 py-8 lg:flex"><SidebarContent /></aside>;
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
        if (alive && current === request) setLanguage(languages.find(item => item.active) ?? null);
      } catch {
        if (alive && current === request) setLanguage(null);
      } finally {
        if (alive && current === request) setLoading(false);
      }
    }
    void load();
    const changed = () => { void load(); };
    window.addEventListener("befluent:language-changed", changed);
    return () => { alive = false; window.removeEventListener("befluent:language-changed", changed); };
  }, [pathname]);
  return <Link href="/languages" className="inline-flex min-h-11 min-w-0 items-center gap-2 rounded-[10px] px-2 text-sm font-medium hover:bg-surface-soft"
    aria-label={language ? language.name_pt + " — Trocar idioma" : loading ? "Carregando idioma" : "Escolher idioma"}>
    <Globe className="size-4 shrink-0 text-primary" aria-hidden />
    <span className="truncate">{loading ? "Carregando…" : language?.name_pt ?? "Escolher idioma"}</span>
    <ChevronDown className="size-4 shrink-0 text-text-secondary" aria-hidden />
  </Link>;
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
    const focusables = () => Array.from(panel.current?.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),input,select,textarea,[tabindex="0"]') ?? []);
    focusables()[0]?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") { event.preventDefault(); setOpen(false); }
      if (event.key === "Tab") {
        const items = focusables();
        const first = items[0], last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    }
    const onResize = () => { if (window.innerWidth >= 1024) setOpen(false); };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
      returnFocus?.focus();
    };
  }, [open]);
  return <>
    <header className="flex min-h-18 items-center justify-between gap-3 border-b border-border bg-background px-5 md:px-8">
      <div className="flex min-w-0 items-center gap-2">
        <button ref={trigger} type="button" className="grid size-11 shrink-0 place-items-center rounded-[10px] hover:bg-surface-soft lg:hidden"
          aria-expanded={open} aria-controls={panelId} aria-label="Abrir menu" onClick={() => setOpen(true)}><Menu className="size-5" aria-hidden /></button>
        <LanguageContext />
      </div>
      <Link href="/profile" aria-label="Seu perfil" className="grid size-11 shrink-0 place-items-center rounded-full border border-border bg-surface text-text-secondary hover:text-primary"><User className="size-5" aria-hidden /></Link>
    </header>
    {open && <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
      <div className="absolute inset-0 bg-text-primary/30" onClick={() => setOpen(false)} aria-hidden />
      <aside ref={panel} id={panelId} className="absolute inset-y-0 left-0 flex w-[min(19rem,90vw)] flex-col overflow-y-auto bg-surface p-5 shadow-xl">
        <button type="button" aria-label="Fechar menu" onClick={() => setOpen(false)} className="mb-4 grid size-11 place-items-center self-end rounded-[10px] hover:bg-surface-soft"><X className="size-5" aria-hidden /></button>
        <SidebarContent onNavigate={() => setOpen(false)} />
      </aside>
    </div>}
  </>;
}
export function MobileNav() {
  const pathname = usePathname();
  return <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-border bg-surface px-2 pb-[env(safe-area-inset-bottom)] lg:hidden" aria-label="Navegação móvel">
    {navigation.map(({ href, label, icon: Icon }) => {
      const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href + "/"));
      return <Link key={href} href={href} aria-current={active ? "page" : undefined}
        className={`flex min-h-16 flex-col items-center justify-center gap-1 px-1 py-2 text-xs font-medium transition-colors ${active ? "text-primary" : "text-text-secondary"}`}>
        <Icon className="size-5" aria-hidden />{label}
      </Link>;
    })}
  </nav>;
}
export function AppShell({ children, tutor }: { children: ReactNode; tutor?: ReactNode }) {
  const pathname = usePathname();
  const languagePicker = pathname === "/languages";
  const focus = /^\/learn\/(?!objetivo(?:\/|$))[^/]+\/?$/.test(pathname)
    || /^\/cronograma\/dia\/[^/]+\/?$/.test(pathname)
    || /^\/placement-test\/[^/]+\/?$/.test(pathname);
  const assessment = pathname.startsWith("/placement-test/");
  const practice = pathname.startsWith("/learn/");
  return <>
    <a href="#main-content" className="skip-link">Pular para o conteúdo</a>
    {languagePicker ? <>
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex min-h-18 max-w-3xl items-center justify-between gap-4 px-5 md:px-8">
          <Link href="/dashboard" aria-label="BeFluent — Hoje"><Logo /></Link>
          <Link href="/profile" aria-label="Seu perfil" className="grid size-11 shrink-0 place-items-center rounded-full border border-border bg-surface text-text-secondary hover:text-primary"><User className="size-5" aria-hidden /></Link>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-3xl px-5 py-8 md:px-8 md:py-12">{children}</main>
    </> : focus ? <>
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex min-h-18 max-w-6xl items-center justify-between gap-4 px-5 md:px-8">
          <Link href={assessment ? "/placement-test" : practice ? "/learn" : "/cronograma"} className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-text-secondary hover:text-primary"><ArrowLeft className="size-4" aria-hidden />{assessment ? "Voltar ao teste" : practice ? "Voltar à prática" : "Voltar ao plano"}</Link>
          <span className="hidden text-sm text-text-secondary sm:block">{assessment ? "Seu diagnóstico" : "Seu momento de estudo"}</span>
          <Logo showWordmark={false} />
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className="study-content mx-auto w-full max-w-4xl px-5 py-8 md:px-8 md:py-12">{children}</main>
    </> : <>
      <Sidebar />
      <div className="min-h-screen lg:pl-60">
        <Header />
        <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-[1200px] px-5 py-8 pb-28 md:px-8 md:py-10 lg:pb-12">{children}</main>
      </div>
      <MobileNav />{tutor}
    </>}
  </>;
}
