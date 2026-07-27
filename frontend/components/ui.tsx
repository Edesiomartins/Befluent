import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
} from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  loading?: boolean;
};

export function Button({
  variant = "primary",
  loading,
  className = "",
  children,
  disabled,
  ...props
}: ButtonProps) {
  const styles = {
    primary: "bg-primary text-white hover:bg-[var(--primary-strong)]",
    secondary: "border border-border bg-surface text-text-primary hover:bg-surface-elevated",
    danger: "bg-danger text-white hover:opacity-90",
    ghost: "text-text-secondary hover:bg-surface-elevated hover:text-text-primary",
  };
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-55 ${styles[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden />}
      {children}
    </button>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
};

export function Input({ label, error, id, className = "", ...props }: InputProps) {
  const inputId = id ?? props.name;
  return (
    <label className="grid gap-2 text-sm font-medium" htmlFor={inputId}>
      {label}
      <input
        id={inputId}
        className={`min-h-11 rounded-lg border bg-surface px-3.5 py-2.5 text-text-primary placeholder:text-text-secondary/65 focus:border-primary ${error ? "border-danger" : "border-border"} ${className}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...props}
      />
      {error && <span id={`${inputId}-error`} className="text-sm font-normal text-danger">{error}</span>}
    </label>
  );
}

export function Loading({ label = "Carregando" }: { label?: string }) {
  return (
    <div className="grid gap-4" aria-label={label} role="status">
      <span className="sr-only">{label}</span>
      <div className="skeleton h-8 w-2/5" />
      <div className="skeleton h-24 w-full" />
      <div className="skeleton h-16 w-4/5" />
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="panel grid justify-items-start gap-3 p-6">
      <span className="text-2xl" aria-hidden>○</span>
      <h2 className="section-title">{title}</h2>
      <p className="max-w-lg text-sm leading-6 text-text-secondary">{description}</p>
      {action}
    </div>
  );
}

export function ErrorState({
  retry,
  message = "Não foi possível carregar este conteúdo.",
}: {
  retry?: () => void;
  message?: string;
}) {
  return (
    <div className="rounded-xl border border-danger/25 bg-danger/5 p-5" role="alert">
      <h2 className="font-semibold text-danger">Algo não saiu como esperado</h2>
      <p className="mt-1 text-sm text-text-secondary">{message}</p>
      {retry && <Button variant="secondary" className="mt-4" onClick={retry}>Tentar novamente</Button>}
    </div>
  );
}

export function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-5 border-b border-border py-4 last:border-0">
      <span><span className="block text-sm font-medium">{label}</span>{description && <span className="mt-1 block text-sm text-text-secondary">{description}</span>}</span>
      <input className="size-5 accent-[var(--primary)]" type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}
