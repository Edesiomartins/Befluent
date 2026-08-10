"use client";

import Link from "next/link";
import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Input, PasswordInput } from "@/components/ui";
import { Logo } from "@/components/logo";
import { BRAND } from "@/lib/brand";

function PasswordHints({ password }: { password: string }) {
  const checks = [
    { ok: password.length >= 8, label: "Pelo menos 8 caracteres" },
    { ok: /[A-Za-z]/.test(password), label: "Contém letras" },
    { ok: /\d/.test(password) || password.length >= 10, label: "Números ou senha mais longa" },
  ];
  return (
    <ul className="grid gap-1 text-xs text-text-secondary" aria-live="polite">
      {checks.map((item) => (
        <li key={item.label} className={item.ok ? "text-success" : undefined}>
          {item.ok ? "✓" : "•"} {item.label}
        </li>
      ))}
    </ul>
  );
}

export default function RegisterPage() {
  const router = useRouter();
  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess(false);

    const trimmedName = name.trim();
    if (trimmedName.length < 2) {
      setError("O nome deve ter pelo menos 2 caracteres.");
      nameRef.current?.focus();
      return;
    }
    if (!email.trim()) {
      setError("Informe um e-mail válido.");
      emailRef.current?.focus();
      return;
    }
    if (password.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres.");
      passwordRef.current?.focus();
      return;
    }
    if (password !== passwordConfirmation) {
      setError("As senhas não coincidem.");
      confirmRef.current?.focus();
      return;
    }

    setLoading(true);
    try {
      await api("/api/v1/auth/register", {
        method: "POST",
        body: {
          name: trimmedName,
          email: email.trim(),
          password,
          password_confirmation: passwordConfirmation,
        },
      });
      setSuccess(true);
      setPassword("");
      setPasswordConfirmation("");
      window.setTimeout(() => {
        router.replace("/login?cadastro=ok");
      }, 900);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível criar a conta. Tente novamente.",
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
              "radial-gradient(circle at 20% 15%, rgba(37,99,235,.5), transparent 40%), radial-gradient(circle at 80% 70%, rgba(219,234,254,.16), transparent 38%)",
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
            Comece do seu jeito.
            <br />
            No seu ritmo.
          </h1>
          <p className="mt-7 max-w-md text-lg leading-8 text-white/70">
            {BRAND.description}
          </p>
        </div>
        <p className="relative text-sm text-white/45">{BRAND.institutional}</p>
      </section>
      <section className="flex items-center justify-center bg-surface px-5 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <Logo />
          </div>
          <p className="mb-2 text-sm font-semibold text-primary">Criar conta</p>
          <h1 className="page-title">Crie sua conta no BeFluent</h1>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            Comece agora sua jornada de aprendizado e fluência.
          </p>
          <form className="mt-8 grid gap-5" onSubmit={submit} autoComplete="off">
            <Input
              ref={nameRef}
              label="Nome"
              name="name"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Seu nome"
            />
            <Input
              ref={emailRef}
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
                ref={passwordRef}
                label="Senha"
                name="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <PasswordHints password={password} />
            </div>
            <PasswordInput
              ref={confirmRef}
              label="Confirmar senha"
              name="password_confirmation"
              autoComplete="new-password"
              value={passwordConfirmation}
              onChange={(e) => setPasswordConfirmation(e.target.value)}
            />
            {error && (
              <p
                className="rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger"
                role="alert"
              >
                {error}
              </p>
            )}
            {success && (
              <p
                className="rounded-lg border border-success/25 bg-success/5 p-3 text-sm text-success"
                role="status"
              >
                Conta criada com sucesso. Redirecionando para o login...
              </p>
            )}
            <Button type="submit" loading={loading} className="w-full" disabled={success}>
              {loading ? "Criando conta…" : "Criar minha conta"}
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-text-secondary">
            Já tem uma conta?{" "}
            <Link
              href="/login"
              className="font-semibold text-primary underline-offset-2 hover:underline"
            >
              Entrar
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
