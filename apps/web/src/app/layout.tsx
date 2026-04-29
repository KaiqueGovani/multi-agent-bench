import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pharmacy Agent POC",
  description: "Web chat and event timeline for the pharmacy multi-agent POC"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
