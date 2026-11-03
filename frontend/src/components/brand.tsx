"use client";

/**
 * Deal Scope brand: the mark, the two-line wordmark, and the boot screen.
 *
 * The mark is a "D" drawn as nested rings on a stem, so it reads as both the
 * initial and a scope. The wordmark sets DEAL over SCOPE with the shorter word
 * tracked out to the same width, in the manner of two-line print logotypes.
 */

import { useEffect, useState } from "react";
import { useSession } from "@/lib/auth";
import { cx } from "./ui";

export const PRODUCT_NAME = "Deal Scope";

const RINGS = [
  { d: "M24 15 H50 A35 35 0 0 1 50 85 H24", delay: 0 },
  { d: "M24 31 H50 A19 19 0 0 1 50 69 H24", delay: 160 },
] as const;

/** The monogram alone. Fills with `currentColor`; pass `animate` for the boot sequence. */
export function Mark({ size = 28, animate, className }: { size?: number; animate?: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden className={cx("shrink-0", className)}>
      <rect x="10" y="10" width="14" height="80" fill="currentColor" className={animate ? "boot-stem" : undefined} />
      {RINGS.map((ring) => (
        <path
          key={ring.d}
          d={ring.d}
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          pathLength={1}
          className={animate ? "boot-ring" : undefined}
          style={animate ? { animationDelay: `${320 + ring.delay}ms` } : undefined}
        />
      ))}
      <path d="M24 44 H50 A6 6 0 0 1 50 56 H24 Z" fill="currentColor" className={animate ? "boot-core" : undefined} />
    </svg>
  );
}

/** DEAL over SCOPE, both lines justified to one width. Inherits `currentColor`. */
export function WordmarkText({ height = 26, className }: { height?: number; className?: string }) {
  return (
    <svg viewBox="0 0 92 44" height={height} width={(height * 92) / 44} aria-hidden className={cx("shrink-0 overflow-visible", className)}>
      <text x="1" y="19" textLength="90" lengthAdjust="spacing" fontSize="21" fontWeight="800" fill="currentColor" style={{ fontFamily: "inherit" }}>
        DEAL
      </text>
      <text x="1" y="43" textLength="90" lengthAdjust="spacing" fontSize="21" fontWeight="800" fill="currentColor" style={{ fontFamily: "inherit" }}>
        SCOPE
      </text>
    </svg>
  );
}

/**
 * Mark plus wordmark. `tone` picks the mark colour for light or dark
 * backgrounds; the wordmark takes the surrounding text colour.
 */
export function Logo({ compact, tone = "light", size = 30, className }: { compact?: boolean; tone?: "light" | "dark"; size?: number; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-2.5", className)} aria-label={PRODUCT_NAME} role="img">
      <Mark size={size} className={tone === "dark" ? "text-panel-accent" : "text-primary"} />
      {!compact && <WordmarkText height={size * 0.82} />}
    </span>
  );
}

const BOOT_FLAG = "dealscope-booted";
const BOOT_DURATION_MS = 2300;
const BOOT_FADE_MS = 500;

function shouldBoot(): boolean {
  if (typeof window === "undefined") return false;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
  try {
    if (window.sessionStorage.getItem(BOOT_FLAG)) return false;
    window.sessionStorage.setItem(BOOT_FLAG, "1");
  } catch {
    /* Private windows or blocked storage: still show the boot once per load. */
  }
  return true;
}

/**
 * Console-style boot screen shown once per browser session on first load. It
 * stays up for the animation and until the session check has finished, so it
 * doubles as the real loading state, then fades into the app.
 */
export function BootScreen() {
  const session = useSession();
  // The overlay is part of the prerendered markup so a cold load is dark from
  // the first paint; a tab that already booted this session dismisses it at once.
  const [phase, setPhase] = useState<"boot" | "leaving" | "done">("boot");
  const [elapsed, setElapsed] = useState(false);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      if (!shouldBoot()) setPhase("done");
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (phase !== "boot") return;
    const timer = window.setTimeout(() => setElapsed(true), BOOT_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, [phase]);

  // Leave once the animation has played and the session check has answered.
  useEffect(() => {
    if (phase !== "boot" || !elapsed || session.loading) return;
    const frame = window.requestAnimationFrame(() => setPhase("leaving"));
    const timer = window.setTimeout(() => setPhase("done"), BOOT_FADE_MS);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [phase, elapsed, session.loading]);

  if (phase === "done") return null;
  return (
    <div className={cx("boot", phase === "leaving" && "leaving")} role="status" aria-label={`${PRODUCT_NAME} is starting`}>
      <div className="boot-bloom" />
      <div className="boot-stage">
        <Mark size={132} animate className="text-panel-accent" />
        <div className="boot-word">
          <WordmarkText height={48} />
        </div>
      </div>
      <p className="boot-caption">Commercial real estate underwriting</p>
    </div>
  );
}
