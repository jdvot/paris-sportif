"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Header } from "./Header";

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * AppShell - Layout wrapper for the application
 *
 * IMPORTANT: Authentication is handled by the Next.js middleware (middleware.ts).
 * The middleware runs on the server and validates the session before the page loads.
 * We do NOT duplicate auth checks here to avoid race conditions and redirect loops.
 *
 * If a user reaches a protected page, it means the middleware has already validated
 * their session. The client-side Supabase auth state will catch up eventually.
 */
export function AppShell({ children }: AppShellProps) {
  const t = useTranslations("footer");

  return (
    <div className="min-h-screen flex flex-col">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary-600 focus:text-white focus:rounded-lg focus:text-sm focus:font-medium"
      >
        {t("skipToContent")}
      </a>
      <Header />
      <main id="main-content" className="flex-1 container mx-auto px-4 py-8">
        {children}
      </main>
      <footer className="border-t border-gray-200 dark:border-dark-700 py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-dark-400">
              <Link
                href="/privacy"
                className="hover:text-gray-700 dark:hover:text-dark-200 transition-colors"
              >
                {t("privacy")}
              </Link>
              <Link
                href="/terms"
                className="hover:text-gray-700 dark:hover:text-dark-200 transition-colors"
              >
                {t("terms")}
              </Link>
              <Link
                href="/plans"
                className="hover:text-gray-700 dark:hover:text-dark-200 transition-colors"
              >
                {t("pricing")}
              </Link>
            </div>
            <div className="text-center text-sm text-gray-500 dark:text-dark-400">
              <p>WinRate AI</p>
              <p className="text-xs mt-1">{t("disclaimer")}</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
