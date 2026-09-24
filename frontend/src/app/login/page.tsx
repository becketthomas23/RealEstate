"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

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
      if (!response.ok) {
        throw new Error("Incorrect password. Please try again.");
      }
      router.replace("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl border border-stone-200 bg-white p-7 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">CRE underwriting</p>
        <h1 className="mt-2 text-2xl font-semibold text-stone-900">Private access</h1>
        <p className="mt-2 text-sm leading-6 text-stone-600">Enter the shared password to open the price solver.</p>
        <label className="mt-6 block text-sm font-medium text-stone-700">
          Password
          <input
            autoFocus
            required
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1.5 block w-full rounded-xl border border-stone-300 px-3 py-2.5 outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
          />
        </label>
        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        <button disabled={submitting} className="mt-6 w-full rounded-xl bg-emerald-800 px-4 py-2.5 font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60">
          {submitting ? "Opening…" : "Open price solver"}
        </button>
      </form>
    </main>
  );
}
