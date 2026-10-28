"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactNode, useState } from "react";
import { useSession } from "@/lib/auth";
import { Badge, cx } from "./ui";

export const PRODUCT_NAME = "Deal Scope";

export function Wordmark({ compact }: { compact?: boolean }) {
  return (
    <span className="flex items-center gap-2 font-semibold tracking-tight text-ink">
      <span aria-hidden className="grid h-7 w-7 place-items-center rounded-lg bg-primary text-[11px] font-bold text-on-primary">
        DS
      </span>
      {!compact && <span>{PRODUCT_NAME}</span>}
    </span>
  );
}

/** Top navigation and page frame shared by every screen. */
export function AppShell({ children, crumbs, actions }: { children: ReactNode; crumbs?: Array<{ label: string; href?: string }>; actions?: ReactNode }) {
  const session = useSession();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  async function signOut() {
    await session.signOut();
    router.replace("/login/");
  }
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <nav className="flex min-w-0 items-center gap-2 text-sm">
            <Link href="/" className="shrink-0">
              <Wordmark compact={Boolean(crumbs?.length)} />
            </Link>
            {crumbs?.map((crumb, index) => (
              <span key={index} className="flex min-w-0 items-center gap-2">
                <span aria-hidden className="text-ink-muted">
                  /
                </span>
                {crumb.href ? (
                  <Link href={crumb.href} className="truncate text-ink-secondary hover:text-ink">
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="truncate font-medium text-ink">{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            {actions}
            {session.required && session.user && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setMenuOpen((open) => !open)}
                  className="flex h-9 items-center gap-2 rounded-full border border-line bg-surface pl-1 pr-3 text-sm hover:border-line-strong"
                  aria-haspopup="menu"
                  aria-expanded={menuOpen}
                >
                  <span aria-hidden className="grid h-7 w-7 place-items-center rounded-full bg-primary-soft text-[11px] font-bold text-primary-ink">
                    {initials(session.user.name)}
                  </span>
                  <span className="hidden max-w-[160px] truncate sm:inline">{session.user.name}</span>
                  {session.user.role === "admin" && <Badge tone="primary">Admin</Badge>}
                </button>
                {menuOpen && (
                  <div role="menu" className="absolute right-0 mt-2 w-60 rounded-[var(--radius-card)] border border-line bg-surface p-2 shadow-lg">
                    <p className="truncate px-2 py-1 text-xs text-ink-muted">{session.user.email}</p>
                    {session.user.role === "admin" && (
                      <Link href="/team/" role="menuitem" className="block rounded-lg px-2 py-2 text-sm hover:bg-surface-muted" onClick={() => setMenuOpen(false)}>
                        Team and access
                      </Link>
                    )}
                    <Link href="/account/" role="menuitem" className="block rounded-lg px-2 py-2 text-sm hover:bg-surface-muted" onClick={() => setMenuOpen(false)}>
                      Change password
                    </Link>
                    <button type="button" role="menuitem" onClick={() => void signOut()} className="block w-full rounded-lg px-2 py-2 text-left text-sm text-critical hover:bg-critical-soft">
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            )}
            {!session.required && !session.loading && <Badge tone="neutral">Local mode · sign-in off</Badge>}
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      <footer className="border-t border-line py-4 text-center text-[11px] text-ink-muted">
        {PRODUCT_NAME} · Educational modeling tool, not financial advice. Verify every assumption independently.
      </footer>
    </div>
  );
}

export function PageHeader({ title, description, actions, className }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <div className={cx("mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0">
        <h1 className="truncate text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm leading-6 text-ink-secondary">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
