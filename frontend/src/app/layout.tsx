import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "CRE Price Solver", template: "%s · CRE Price Solver" },
  description: "Transparent commercial real estate underwriting: solve the maximum supportable price from a target return and coverage.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body suppressHydrationWarning className="min-h-full">
        {children}
      </body>
    </html>
  );
}
