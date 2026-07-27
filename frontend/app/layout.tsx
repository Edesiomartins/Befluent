import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { BRAND } from "@/lib/brand";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: `${BRAND.name} — Aprenda idiomas com inteligência artificial`,
    template: `%s · ${BRAND.name}`,
  },
  description:
    "Pratique conversação, pronúncia, vocabulário e compreensão com tutores inteligentes no BeFluent.",
  applicationName: BRAND.name,
  metadataBase: new URL(`https://${BRAND.domain}`),
  openGraph: {
    title: `${BRAND.name} — Aprenda. Pratique. Fale.`,
    description: BRAND.description,
    siteName: BRAND.name,
    locale: "pt_BR",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#2563EB",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className={`${inter.variable} antialiased`}>{children}</body>
    </html>
  );
}
