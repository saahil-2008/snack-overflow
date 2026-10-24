import type { Metadata } from "next";
import FarmApp from "@/components/FarmApp";
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/dm-sans/700.css";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import "@fontsource/manrope/800.css";
import "./globals.css";
export const metadata: Metadata = {
  title: "FarmPool 360 — Grow better. Go together.",
  description:
    "Your harvest, connected. Smarter quality checks, shared transport, and a fresher food future.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <FarmApp />
        {children}
      </body>
    </html>
  );
}
