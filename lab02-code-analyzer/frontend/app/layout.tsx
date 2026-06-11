import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Code Analyzer",
  description: "Lab 02 code analyzer frontend",
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

