"use client";

import { useEffect } from "react";

/**
 * Global error boundary that catches errors in the root layout.
 * This component CANNOT use providers (next-intl, shadcn, etc.)
 * because it replaces the entire <html> when triggered.
 * Must provide its own <html> and <body> tags.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Report to Sentry
    console.error("Root layout error:", error);
  }, [error]);

  return (
    <html lang="fr">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#0f172a", color: "#f1f5f9" }}>
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem" }}>
          <div style={{ maxWidth: "28rem", textAlign: "center" }}>
            <div style={{ fontSize: "4rem", marginBottom: "1rem" }}>
              &#x26A0;
            </div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: "bold", marginBottom: "0.5rem" }}>
              Une erreur critique est survenue
            </h1>
            <p style={{ color: "#94a3b8", marginBottom: "1.5rem" }}>
              L&apos;application a rencontré un problème inattendu.
            </p>
            {process.env.NODE_ENV === "development" && (
              <pre style={{ textAlign: "left", fontSize: "0.75rem", background: "#1e293b", padding: "1rem", borderRadius: "0.5rem", overflow: "auto", marginBottom: "1.5rem" }}>
                {error.message}
              </pre>
            )}
            <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
              <button
                onClick={reset}
                style={{ padding: "0.75rem 1.5rem", background: "#3b82f6", color: "white", border: "none", borderRadius: "0.5rem", cursor: "pointer", fontWeight: 500 }}
              >
                Réessayer
              </button>
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- global-error replaces root layout, Next.js Link unavailable */}
              <a
                href="/"
                style={{ padding: "0.75rem 1.5rem", background: "#334155", color: "white", borderRadius: "0.5rem", textDecoration: "none", fontWeight: 500 }}
              >
                Accueil
              </a>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
