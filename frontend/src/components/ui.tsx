"use client";

/**
 * Design-system primitives. Every screen composes these so spacing, type,
 * color, and states stay consistent. Keep them small and unopinionated about
 * data; feature components own the content.
 */

import { ReactNode, SelectHTMLAttributes, InputHTMLAttributes, ButtonHTMLAttributes } from "react";

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ");

/* ---------------------------------------------------------------- Buttons */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "on-panel";
type ButtonSize = "sm" | "md" | "lg";

const buttonVariant: Record<ButtonVariant, string> = {
  primary: "bg-primary text-on-primary hover:bg-primary-strong shadow-sm",
  secondary: "border border-line-strong bg-surface text-ink hover:border-primary hover:text-primary-ink",
  ghost: "text-ink-secondary hover:bg-surface-muted hover:text-ink",
  danger: "border border-critical/30 bg-surface text-critical hover:bg-critical-soft",
  "on-panel": "border border-panel-line bg-panel-soft text-panel-ink hover:border-panel-accent",
};
const buttonSize: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-5 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  busy,
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize; busy?: boolean }) {
  return (
    <button
      {...props}
      disabled={props.disabled || busy}
      className={cx(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-control)] font-semibold transition",
        "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60",
        buttonVariant[variant],
        buttonSize[size],
        className,
      )}
    >
      {busy && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cx("inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent", className)}
    />
  );
}

/* ------------------------------------------------------------------ Cards */

export function Card({
  title,
  description,
  actions,
  children,
  className,
  tone = "surface",
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
  tone?: "surface" | "panel" | "muted";
}) {
  const toneClass =
    tone === "panel"
      ? "border-panel-line bg-panel text-panel-ink"
      : tone === "muted"
        ? "border-line bg-surface-muted"
        : "border-line bg-surface shadow-[var(--shadow-card)]";
  return (
    <section className={cx("rounded-[var(--radius-card)] border p-5 sm:p-6", toneClass, className)}>
      {(title || actions) && (
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {title && <h2 className="text-base font-semibold tracking-tight">{title}</h2>}
            {description && (
              <p className={cx("mt-1 max-w-2xl text-xs leading-5", tone === "panel" ? "text-panel-muted" : "text-ink-muted")}>
                {description}
              </p>
            )}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function SectionHeading({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h3 className="text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">{children}</h3>
      {hint && <span className="text-xs text-ink-muted">{hint}</span>}
    </div>
  );
}

/* ------------------------------------------------------------------ Stats */

export function Stat({
  label,
  value,
  hint,
  tone = "default",
  size = "md",
  onPanel,
}: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "accent" | "good" | "warn" | "critical";
  size?: "sm" | "md" | "lg";
  onPanel?: boolean;
}) {
  const toneClass = onPanel
    ? tone === "accent"
      ? "text-panel-accent"
      : "text-panel-ink"
    : tone === "accent"
      ? "text-primary-ink"
      : tone === "good"
        ? "text-good"
        : tone === "warn"
          ? "text-warn"
          : tone === "critical"
            ? "text-critical"
            : "text-ink";
  const sizeClass = size === "lg" ? "text-3xl sm:text-4xl" : size === "sm" ? "text-base" : "text-xl";
  return (
    <div className="min-w-0">
      <p className={cx("text-[11px] font-semibold uppercase tracking-[0.12em]", onPanel ? "text-panel-muted" : "text-ink-muted")}>
        {label}
      </p>
      <p className={cx("tabular mt-1 truncate font-semibold tracking-tight", sizeClass, toneClass)}>{value}</p>
      {hint && <p className={cx("mt-1 text-xs", onPanel ? "text-panel-muted" : "text-ink-muted")}>{hint}</p>}
    </div>
  );
}

/* ----------------------------------------------------------------- Badges */

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: "neutral" | "primary" | "good" | "warn" | "critical" | "info" | "on-panel";
  className?: string;
}) {
  const toneClass = {
    neutral: "bg-surface-muted text-ink-secondary ring-line",
    primary: "bg-primary-soft text-primary-ink ring-primary/20",
    good: "bg-good-soft text-good ring-good/20",
    warn: "bg-warn-soft text-warn ring-warn/20",
    critical: "bg-critical-soft text-critical ring-critical/20",
    info: "bg-info-soft text-info ring-info/20",
    "on-panel": "bg-white/10 text-panel-ink ring-white/10",
  }[tone];
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset",
        toneClass,
        className,
      )}
    >
      {children}
    </span>
  );
}

export const severityTone = (severity: string): "critical" | "warn" => (severity === "critical" ? "critical" : "warn");

/* ---------------------------------------------------------------- Banners */

export function Banner({
  tone,
  children,
  onDismiss,
}: {
  tone: "error" | "success" | "info";
  children: ReactNode;
  onDismiss?: () => void;
}) {
  const toneClass = {
    error: "border-critical/30 bg-critical-soft text-critical",
    success: "border-good/30 bg-good-soft text-primary-ink",
    info: "border-info/30 bg-info-soft text-info",
  }[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={cx("flex items-start gap-3 rounded-[var(--radius-control)] border px-4 py-3 text-sm", toneClass)}>
      <p className="flex-1 leading-5">{children}</p>
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Dismiss" className="text-current/70 hover:text-current">
          ×
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Forms */

const controlClass =
  "block w-full rounded-[var(--radius-control)] border border-line-strong bg-surface px-3 text-sm text-ink outline-none transition placeholder:text-ink-muted focus:border-primary focus:ring-4 focus:ring-primary/15 disabled:bg-surface-muted disabled:text-ink-muted";

export function Label({ children, hint, className }: { children: ReactNode; hint?: ReactNode; className?: string }) {
  return (
    <span className={cx("flex items-baseline justify-between gap-2 text-sm font-medium text-ink-secondary", className)}>
      <span>{children}</span>
      {hint && <span className="text-xs font-normal text-ink-muted">{hint}</span>}
    </span>
  );
}

export function TextInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(controlClass, "h-10", className)} />;
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...props} className={cx(controlClass, "h-10 pr-8", className)}>
      {children}
    </select>
  );
}

/** A labelled numeric input with a unit suffix inside the control. */
export function NumberField({
  label,
  hint,
  suffix,
  value,
  onChange,
  min,
  step = "any",
  required = true,
  help,
}: {
  label: ReactNode;
  hint?: ReactNode;
  suffix?: string;
  value: string;
  onChange: (value: string) => void;
  min?: string;
  step?: string;
  required?: boolean;
  help?: ReactNode;
}) {
  return (
    <label className="block">
      <Label hint={hint}>{label}</Label>
      <span className="relative mt-1.5 block">
        <input
          type="number"
          inputMode="decimal"
          step={step}
          min={min}
          required={required}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={cx(controlClass, "tabular h-10", suffix ? "pr-14" : "")}
        />
        {suffix && (
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs font-medium text-ink-muted">
            {suffix}
          </span>
        )}
      </span>
      {help && <span className="mt-1 block text-xs leading-5 text-ink-muted">{help}</span>}
    </label>
  );
}

export function Field({ label, hint, children, help }: { label: ReactNode; hint?: ReactNode; children: ReactNode; help?: ReactNode }) {
  return (
    <label className="block">
      <Label hint={hint}>{label}</Label>
      <span className="mt-1.5 block">{children}</span>
      {help && <span className="mt-1 block text-xs leading-5 text-ink-muted">{help}</span>}
    </label>
  );
}

/* ------------------------------------------------------------------- Tabs */

export type TabItem<K extends string> = { key: K; label: string; badge?: ReactNode; disabled?: boolean };

export function Tabs<K extends string>({ items, value, onChange }: { items: TabItem<K>[]; value: K; onChange: (key: K) => void }) {
  return (
    <div role="tablist" className="-mb-px flex gap-1 overflow-x-auto">
      {items.map((item) => {
        const active = item.key === value;
        return (
          <button
            key={item.key}
            role="tab"
            type="button"
            aria-selected={active}
            disabled={item.disabled}
            onClick={() => onChange(item.key)}
            className={cx(
              "flex h-11 shrink-0 items-center gap-2 border-b-2 px-3 text-sm font-medium transition",
              active ? "border-primary text-primary-ink" : "border-transparent text-ink-muted hover:text-ink",
              item.disabled && "cursor-not-allowed opacity-50",
            )}
          >
            {item.label}
            {item.badge}
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------ Empty state */

export function EmptyState({ title, description, action, compact }: { title: ReactNode; description?: ReactNode; action?: ReactNode; compact?: boolean }) {
  return (
    <div className={cx("flex flex-col items-center justify-center rounded-[var(--radius-card)] border border-dashed border-line-strong text-center", compact ? "px-4 py-8" : "px-6 py-14")}>
      <p className="text-sm font-semibold text-ink">{title}</p>
      {description && <p className="mt-1 max-w-sm text-xs leading-5 text-ink-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/* ------------------------------------------------------------ Definition */

export function KeyValue({ rows, onPanel }: { rows: Array<[ReactNode, ReactNode]>; onPanel?: boolean }) {
  return (
    <dl className={cx("grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-xs", onPanel ? "text-panel-ink" : "text-ink")}>
      {rows.map(([key, value], index) => (
        <div key={index} className="contents">
          <dt className={onPanel ? "text-panel-muted" : "text-ink-muted"}>{key}</dt>
          <dd className="tabular text-right font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ----------------------------------------------------------------- Dialog */

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  onConfirm,
  onCancel,
  busy,
}: {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-[var(--radius-card)] border border-line bg-surface p-6 shadow-xl">
        <h2 className="text-base font-semibold">{title}</h2>
        {description && <p className="mt-2 text-sm leading-6 text-ink-secondary">{description}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} busy={busy}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export { cx };
