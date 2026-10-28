"use client";

import { Suspense } from "react";
import { DealWorkspace } from "@/components/workspace/DealWorkspace";
import { RequireSession } from "@/lib/auth";

export default function DealPage() {
  return (
    <RequireSession>
      <Suspense fallback={<p className="py-20 text-center text-sm text-ink-muted">Loading deal…</p>}>
        <DealWorkspace />
      </Suspense>
    </RequireSession>
  );
}
