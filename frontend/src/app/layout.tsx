import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Header } from "@/components/Header";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Paris Sportif - Predictions Football",
  description:
    "Application de predictions de paris sportifs sur le football europeen. 5 picks par jour analyses par IA.",
  keywords: ["paris sportifs", "football", "predictions", "betting", "IA"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={inter.variable} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>
          <div className="min-h-screen flex flex-col">
            <Header />
            <main className="flex-1 container mx-auto px-4 py-8">
              {children}
            </main>
            <footer className="border-t border-gray-200 dark:border-slate-700 py-6 text-center text-gray-600 dark:text-slate-400 text-sm">
              <p>Paris Sportif - Predictions basees sur IA</p>
              <p className="mt-1 text-xs">
                Avertissement: Les paris comportent des risques. Jouez
                responsablement.
              </p>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
