"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/brand";
import { Wordmark } from "@/components/shell";
import { Banner, Button, Field, TextInput } from "@/components/ui";
import { post } from "@/lib/api";
import { useSession } from "@/lib/auth";

export default function Login() {
  const router = useRouter();
  const session = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!session.loading && (!session.required || session.authenticated)) router.replace("/");
  }, [session.loading, session.required, session.authenticated, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await post("/v1/auth/login", { email: email.trim(), password });
      await session.refresh();
      router.replace("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in.");
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="hidden flex-col justify-between bg-panel p-10 text-panel-ink lg:flex">
        <Logo tone="dark" size={36} className="text-panel-ink" />
        <div className="max-w-md">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-panel-accent">Commercial real estate underwriting</p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-tight">Price every deal to your return target, with the audit trail to defend it.</h1>
          <ul className="mt-6 space-y-2 text-sm text-panel-muted">
            <li>Reverse-solve the maximum supportable price from a target IRR and DSCR floor.</li>
            <li>Import a broker packet or Excel template and keep every version immutable.</li>
            <li>Correlated risk simulation, sensitivity grids, and analyst-grade Excel exports.</li>
          </ul>
        </div>
        <p className="text-xs text-panel-muted">Educational modeling tool, not financial advice.</p>
      </section>
      <section className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm rounded-[var(--radius-card)] border border-line bg-surface p-7 shadow-[var(--shadow-card)]">
          <div className="mb-6 lg:hidden">
            <Wordmark />
          </div>
          <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-2 text-sm leading-6 text-ink-secondary">Use the account your administrator created for you.</p>
          <div className="mt-6 space-y-4">
            <Field label="Email">
              <TextInput autoFocus required type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} />
            </Field>
            <Field label="Password">
              <TextInput required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </Field>
          </div>
          {error && (
            <div className="mt-3">
              <Banner tone="error">{error}</Banner>
            </div>
          )}
          <Button type="submit" size="lg" className="mt-6 w-full" busy={submitting}>
            Sign in
          </Button>
          <p className="mt-4 text-center text-xs text-ink-muted">Forgot your password? Ask a Deal Scope administrator to reset it.</p>
        </form>
      </section>
    </main>
  );
}
