"use client";

import Link from "next/link";
import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError, storeCsrfToken } from "@/lib/api";
import { Button, Input, PasswordInput } from "@/components/ui";
import { Logo } from "@/components/logo";
import { AuthHeroHighlights } from "@/components/auth-hero-highlights";
import { BRAND } from "@/lib/brand";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const success = searchParams.get("cadastro") === "ok";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!email || !password) return setError("Preencha seu e-mail e sua senha.");
    setLoading(true);
    try {
      const result = await api<{ csrf_token?: string }>("/api/v1/auth/login", {
        method: "POST",
        body: { email, password },
      });
      storeCsrfToken(result.csrf_token);
      router.replace(searchParams.get("retorno") || "/dashboard");
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível acessar o servidor. Tente novamente.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1fr_1.05fr]">
      <section className="relative hidden overflow-hidden bg-[var(--primary-deep)] px-14 py-12 text-white lg:flex lg:flex-col">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          aria-hidden
          style={{
            background:
              "radial-gradient(circle at 15% 20%, rgba(37,99,235,.55), transparent 42%), radial-gradient(circle at 85% 80%, rgba(219,234,254,.18), transparent 40%)",
          }}
        />
        <div className="relative">
          <Logo variant="light" />
        </div>
        <div className="relative my-auto max-w-xl">
          <p className="mb-6 text-sm font-semibold uppercase tracking-[.18em] text-white/55">
            {BRAND.slogan}
          </p>
          <h1 className="text-5xl font-semibold leading-[1.08] tracking-[-.045em]">
            Estude com clareza.
            <br />
            Evolua com constância.
          </h1>
          <p className="mt-7 max-w-md text-lg leading-8 text-white/70">
            {BRAND.description}
          </p>
          <AuthHeroHighlights />
        </div>
        <p className="relative text-sm text-white/45">{BRAND.institutional}</p>
      </section>
      <section className="flex items-center justify-center bg-surface px-5 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <Logo />
            <p className="mt-2 text-sm text-text-secondary">{BRAND.slogan}</p>
          </div>
          <p className="mb-2 text-sm font-semibold text-primary">Bem-vindo de volta</p>
          <h2 className="page-title">Entre na sua conta</h2>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            Continue sua jornada de aprendizado de onde parou.
          </p>
          {success && (
            <p
              className="mt-5 rounded-lg border border-success/25 bg-success/5 p-3 text-sm text-success"
              role="status"
            >
              Conta criada com sucesso. Faça login para continuar.
            </p>
          )}
          <form className="mt-8 grid gap-5" onSubmit={submit}>
            <Input
              label="E-mail"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="voce@exemplo.com"
            />
            <div className="grid gap-2">
              <PasswordInput
                label="Senha"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <Link
                href="/esqueci-senha"
                className="justify-self-end text-sm font-medium text-primary underline-offset-2 hover:underline"
              >
                Esqueceu a senha?
              </Link>
            </div>
            {error && (
              <p
                className="rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger"
                role="alert"
              >
                {error}
              </p>
            )}
            <Button type="submit" loading={loading} className="w-full">
              {loading ? "Entrando…" : "Entrar"}
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-text-secondary">
            Ainda não tem uma conta?{" "}
            <Link
              href="/register"
              className="font-semibold text-primary underline-offset-2 hover:underline"
            >
              Criar conta
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center text-sm text-text-secondary">
          Carregando acesso…
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
