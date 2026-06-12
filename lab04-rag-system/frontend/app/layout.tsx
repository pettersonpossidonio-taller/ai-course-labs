import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RAG System",
  description: "Minimal RAG frontend for Lab 04",
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
