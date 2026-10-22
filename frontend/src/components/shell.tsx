"use client";

import Link from "next/link";
import { ReactNode } from "react";
import { cx } from "./ui";

/** Top navigation and page frame shared by every screen. */
export function AppShell({ children, crumbs, actions }: { children: ReactNode; crumbs?: Array<{ label: string; href?: string }>; actions?: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <nav className="flex min-w-0 items-center gap-2 text-sm">
            <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight text-ink">
              <span aria-hidden className="grid h-7 w-7 place-items-center rounded-lg bg-primary text-[11px] font-bold text-on-primary">
                CRE
              </span>
              <span className="hidden sm:inline">Price Solver</span>
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
          <div className="flex items-center gap-2">{actions}</div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      <footer className="border-t border-line py-4 text-center text-[11px] text-ink-muted">
        Educational modeling tool, not financial advice. Verify every assumption independently.
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
