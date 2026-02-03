"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function ProtectedError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("Protected route error:", error);
  }, [error]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Error Icon */}
        <div className="flex justify-center">
          <div className="p-4 bg-red-100 dark:bg-red-500/20 rounded-full">
            <AlertTriangle className="w-12 h-12 text-red-500 dark:text-red-400" />
          </div>
        </div>

        {/* Error Message */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Une erreur est survenue
          </h1>
          <p className="text-gray-600 dark:text-slate-400">
            Nous n'avons pas pu charger cette page. Veuillez reessayer ou retourner a l'accueil.
          </p>
        </div>

        {/* Error Details (dev only) */}
        {process.env.NODE_ENV === "development" && (
          <div className="p-4 bg-gray-100 dark:bg-slate-800 rounded-lg text-left">
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
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={reset} variant="default" className="gap-2">
            <RefreshCw className="w-4 h-4" />
            Reessayer
          </Button>
          <Button variant="outline" asChild>
            <Link href="/" className="gap-2">
              <Home className="w-4 h-4" />
              Accueil
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
