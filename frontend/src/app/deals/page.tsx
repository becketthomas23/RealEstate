import { Suspense } from "react";
import { DealWorkspace } from "@/components/workspace/DealWorkspace";

export default function DealPage() {
  return (
    <Suspense fallback={<p className="py-20 text-center text-sm text-ink-muted">Loading deal…</p>}>
      <DealWorkspace />
    </Suspense>
  );
}
