"use client";

/**
 * Session awareness for the static frontend. The API owns the session
 * cookie; the frontend asks it who is signed in and redirects to the sign-in
 * page when a protected deployment has no session.
 */

import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, post } from "./api";

export type User = {
  id: string;
  email: string;
  name: string;
  role: "admin" | "analyst";
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
};

type SessionState = {
  loading: boolean;
  required: boolean;
  authenticated: boolean;
  user: User | null;
};

type SessionContextValue = SessionState & {
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

type SessionResponse = { required: boolean; authenticated: boolean; user: User | null };

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ loading: true, required: false, authenticated: false, user: null });

  const refresh = useCallback(async () => {
    try {
      const session = await api<SessionResponse>("/v1/auth/session");
      setState({ loading: false, required: session.required, authenticated: session.authenticated, user: session.user });
    } catch {
      setState({ loading: false, required: false, authenticated: true, user: null });
    }
  }, []);

  useEffect(() => {
    api<SessionResponse>("/v1/auth/session")
      .then((session) => setState({ loading: false, required: session.required, authenticated: session.authenticated, user: session.user }))
      .catch(() => setState({ loading: false, required: false, authenticated: true, user: null }));
  }, []);

  const signOut = useCallback(async () => {
    await post("/v1/auth/logout", {});
    setState((current) => ({ ...current, authenticated: !current.required, user: null }));
  }, []);

  return <SessionContext.Provider value={{ ...state, refresh, signOut }}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}

/** Render children only for a signed-in user (or any visitor when sign-in is off). */
export function RequireSession({ children, fallback }: { children: ReactNode; fallback?: ReactNode }) {
  const session = useSession();
  const router = useRouter();
  useEffect(() => {
    if (!session.loading && session.required && !session.authenticated) router.replace("/login/");
  }, [session.loading, session.required, session.authenticated, router]);
  if (session.loading) return <>{fallback ?? <p className="py-20 text-center text-sm text-ink-muted">Checking your session…</p>}</>;
  if (session.required && !session.authenticated) return <>{fallback ?? null}</>;
  return <>{children}</>;
}
