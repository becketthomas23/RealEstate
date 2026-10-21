import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CRE Price Solver",
  description: "Transparent commercial real estate underwriting.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body suppressHydrationWarning className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
