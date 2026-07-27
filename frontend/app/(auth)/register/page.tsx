"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Input } from "@/components/ui";

export default function RegisterPage() {
  const router = useRouter();
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
    if (trimmedName.length < 2) return setError("O nome deve ter pelo menos 2 caracteres.");
    if (!email.trim()) return setError("Informe um e-mail válido.");
    if (password.length < 8) return setError("A senha deve ter pelo menos 8 caracteres.");
    if (password !== passwordConfirmation) {
      return setError("As senhas não coincidem.");
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
      <section className="hidden bg-[var(--primary-strong)] px-14 py-12 text-white lg:flex lg:flex-col">
        <span className="text-xl font-semibold">Fluentia</span>
        <div className="my-auto max-w-xl">
          <p className="mb-6 text-sm font-semibold uppercase tracking-[.18em] text-white/60">
            Aprendizado de idiomas
          </p>
          <h1 className="text-5xl font-semibold leading-[1.08] tracking-[-.045em]">
            Comece do seu jeito.
            <br />
            No seu ritmo.
          </h1>
          <p className="mt-7 max-w-md text-lg leading-8 text-white/70">
            Crie sua conta para praticar conversação, compreensão e escrita com acompanhamento claro.
          </p>
        </div>
        <p className="text-sm text-white/50">Cadastro aberto para novos estudantes.</p>
      </section>
      <section className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <span className="grid size-10 place-items-center rounded-lg bg-primary text-xl font-bold text-white">
              F
            </span>
          </div>
          <p className="mb-2 text-sm font-semibold text-primary">Criar conta</p>
          <h1 className="page-title">Cadastre-se no Fluentia</h1>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            Preencha seus dados para começar a estudar.
          </p>
          <form className="mt-8 grid gap-5" onSubmit={submit} autoComplete="off">
            <Input
              label="Nome"
              name="name"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Seu nome"
            />
            <Input
              label="E-mail"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="voce@exemplo.com"
            />
            <Input
              label="Senha"
              name="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Input
              label="Confirmar senha"
              name="password_confirmation"
              type="password"
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
                Conta criada com sucesso
              </p>
            )}
            <Button type="submit" loading={loading} className="w-full" disabled={success}>
              {loading ? "Criando conta…" : "Criar conta"}
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
