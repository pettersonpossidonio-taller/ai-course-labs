import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Migration Workflow",
  description: "Minimal migration workflow frontend for Lab 03",
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
