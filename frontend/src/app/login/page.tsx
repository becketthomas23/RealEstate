"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Banner, Button, Field, TextInput } from "@/components/ui";

export default function Login() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!response.ok) throw new Error("Incorrect password. Please try again.");
      router.replace("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm rounded-[var(--radius-card)] border border-line bg-surface p-7 shadow-[var(--shadow-card)]">
        <div className="mb-6 flex items-center gap-2">
          <span aria-hidden className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-[11px] font-bold text-on-primary">
            CRE
          </span>
          <span className="font-semibold tracking-tight">Price Solver</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">Private access</h1>
        <p className="mt-2 text-sm leading-6 text-ink-secondary">Enter the shared password to open the underwriting workspace.</p>
        <div className="mt-6">
          <Field label="Password">
            <TextInput autoFocus required type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </Field>
        </div>
        {error && (
          <div className="mt-3">
            <Banner tone="error">{error}</Banner>
          </div>
        )}
        <Button type="submit" size="lg" className="mt-6 w-full" busy={submitting}>
          Open workspace
        </Button>
      </form>
    </main>
  );
}
