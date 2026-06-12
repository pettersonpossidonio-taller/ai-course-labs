import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lab 05 Multi-Agent",
  description: "Minimal multi-agent orchestration UI for Lab 05",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

