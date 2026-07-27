"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";

const navigation = [
  { href: "/dashboard", label: "Início", icon: "⌂" },
  { href: "/learn", label: "Aprender", icon: "▤" },
  { href: "/languages", label: "Idiomas", icon: "◎" },
  { href: "/progress", label: "Progresso", icon: "↗" },
];

function NavItem({ href, label, icon }: (typeof navigation)[number]) {
  const pathname = usePathname();
  const active = pathname === href || (href === "/learn" && pathname.startsWith("/learn/"));
  return (
    <Link
      href={href}
      className={`flex min-h-11 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${active ? "bg-primary text-white" : "text-text-secondary hover:bg-surface-elevated hover:text-text-primary"}`}
      aria-current={active ? "page" : undefined}
    >
      <span className="w-5 text-center text-lg" aria-hidden>{icon}</span>
      <span>{label}</span>
    </Link>
  );
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-border bg-surface p-5 lg:flex lg:flex-col">
      <Link href="/dashboard" className="mb-10 flex items-center gap-3 px-2">
        <span className="grid size-9 place-items-center rounded-lg bg-primary text-lg font-bold text-white">F</span>
        <span><span className="block text-lg font-semibold tracking-tight">Fluentia</span><span className="block text-xs text-text-secondary">Estudo com propósito</span></span>
      </Link>
      <nav className="grid gap-1.5" aria-label="Navegação principal">
        {navigation.map((item) => <NavItem key={item.href} {...item} />)}
      </nav>
      <nav className="mt-auto grid gap-1.5 border-t border-border pt-4" aria-label="Conta">
        <NavItem href="/settings" label="Configurações" icon="⚙" />
        <NavItem href="/profile" label="Perfil" icon="◉" />
      </nav>
    </aside>
  );
}

export function Header() {
  const router = useRouter();
  async function logout() {
    try { await api("/api/v1/auth/logout", { method: "POST" }); } finally {
      router.replace("/login");
      router.refresh();
    }
  }
  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface/90 px-5 backdrop-blur md:px-8">
      <div>
        <p className="text-xs font-medium uppercase tracking-[.12em] text-text-secondary">Idioma ativo</p>
        <p className="text-sm font-semibold">Inglês · B1</p>
      </div>
      <button onClick={logout} className="rounded-lg px-3 py-2 text-sm font-medium text-text-secondary hover:bg-surface-elevated hover:text-text-primary">Sair</button>
    </header>
  );
}

export function MobileNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-border bg-surface px-2 pb-[env(safe-area-inset-bottom)] lg:hidden" aria-label="Navegação móvel">
      {navigation.map((item) => <NavItem key={item.href} {...item} />)}
    </nav>
  );
}
