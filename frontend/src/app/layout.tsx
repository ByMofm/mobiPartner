import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import ConditionalNavBar from "@/components/ConditionalNavBar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "mobiPartner - Inmuebles Tucuman",
  description: "Centraliza y analiza propiedades inmobiliarias en Tucuman, Argentina",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <ConditionalNavBar />
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  );
}
