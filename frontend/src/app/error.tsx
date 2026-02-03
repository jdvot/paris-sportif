"use client";

import { useEffect } from "react";
import { AlertOctagon, RefreshCw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("Global error:", error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-b from-gray-50 to-gray-100 dark:from-slate-900 dark:to-slate-800">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Error Icon */}
        <div className="flex justify-center">
          <div className="p-4 bg-red-100 dark:bg-red-500/20 rounded-full animate-pulse">
            <AlertOctagon className="w-16 h-16 text-red-500 dark:text-red-400" />
          </div>
        </div>

        {/* Error Message */}
        <div className="space-y-3">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Oops! Quelque chose s'est mal passe
          </h1>
          <p className="text-gray-600 dark:text-slate-400 text-lg">
            Une erreur inattendue est survenue. Notre equipe a ete notifiee.
          </p>
        </div>

        {/* Error Details (dev only) */}
        {process.env.NODE_ENV === "development" && (
          <div className="p-4 bg-gray-100 dark:bg-slate-800 rounded-lg text-left border border-gray-200 dark:border-slate-700">
            <p className="text-xs font-semibold text-gray-700 dark:text-slate-300 mb-2">
              Details de l'erreur:
            </p>
            <p className="text-xs font-mono text-gray-600 dark:text-slate-400 break-all">
              {error.message}
            </p>
            {error.digest && (
              <p className="text-xs font-mono text-gray-500 dark:text-slate-500 mt-2">
                Digest: {error.digest}
              </p>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
          <Button onClick={reset} size="lg" className="gap-2">
            <RefreshCw className="w-5 h-5" />
            Recharger la page
          </Button>
          <Button variant="outline" size="lg" asChild>
            <Link href="/" className="gap-2">
              <Home className="w-5 h-5" />
              Retour a l'accueil
            </Link>
          </Button>
        </div>

        {/* Help Text */}
        <p className="text-sm text-gray-500 dark:text-slate-500">
          Si le probleme persiste, contactez le support.
        </p>
      </div>
    </div>
  );
}
