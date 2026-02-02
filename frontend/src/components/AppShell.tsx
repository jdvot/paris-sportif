"use client";

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
  return (
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
  );
}
