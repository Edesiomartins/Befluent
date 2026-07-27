"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Input } from "@/components/ui";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!email || !password) return setError("Preencha seu e-mail e sua senha.");
    setLoading(true);
    try {
      await api("/api/v1/auth/login", {
        method: "POST",
        body: { email, password },
      });
      router.replace(searchParams.get("retorno") || "/dashboard");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Não foi possível acessar o servidor. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1fr_1.05fr]">
      <section className="hidden bg-[var(--primary-strong)] px-14 py-12 text-white lg:flex lg:flex-col">
        <span className="text-xl font-semibold">Fluentia</span>
        <div className="my-auto max-w-xl">
          <p className="mb-6 text-sm font-semibold uppercase tracking-[.18em] text-white/60">Aprendizado pessoal de idiomas</p>
          <h1 className="text-5xl font-semibold leading-[1.08] tracking-[-.045em]">Estude com clareza.<br />Evolua com constância.</h1>
          <p className="mt-7 max-w-md text-lg leading-8 text-white/70">Um espaço sóbrio para praticar conversação, compreensão e escrita no seu ritmo.</p>
        </div>
        <p className="text-sm text-white/50">Sua rotina, seu progresso, sem distrações.</p>
      </section>
      <section className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden"><span className="grid size-10 place-items-center rounded-lg bg-primary text-xl font-bold text-white">F</span></div>
          <p className="mb-2 text-sm font-semibold text-primary">Bem-vindo de volta</p>
          <h2 className="page-title">Entre na sua conta</h2>
          <p className="mt-3 text-sm leading-6 text-text-secondary">Continue seu plano de estudo de onde parou.</p>
          <form className="mt-8 grid gap-5" onSubmit={submit}>
            <Input label="E-mail" name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="voce@exemplo.com" />
            <Input label="Senha" name="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            {error && <p className="rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger" role="alert">{error}</p>}
            <Button type="submit" loading={loading} className="w-full">{loading ? "Entrando…" : "Entrar"}</Button>
          </form>
          <p className="mt-6 text-center text-xs leading-5 text-text-secondary">O acesso é protegido por uma sessão segura. Sua senha não fica armazenada neste dispositivo.</p>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="grid min-h-screen place-items-center text-sm text-text-secondary">Carregando acesso…</main>}>
      <LoginForm />
    </Suspense>
  );
}
