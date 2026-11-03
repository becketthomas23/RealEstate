import type { Metadata } from "next";
import { BootScreen } from "@/components/brand";
import { SessionProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Deal Scope", template: "%s · Deal Scope" },
  description: "Deal Scope: commercial real estate underwriting that solves the maximum supportable price from a target return and coverage, with a full audit trail.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body suppressHydrationWarning className="min-h-full">
        <SessionProvider>
          <BootScreen />
          {children}
        </SessionProvider>
      </body>
    </html>
  );
}
