"use client";

import { useEffect } from "react";
import { ShieldAlert, RefreshCw, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("Auth route error:", error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-b from-gray-50 to-gray-100 dark:from-slate-900 dark:to-slate-800">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Error Icon */}
        <div className="flex justify-center">
          <div className="p-4 bg-orange-100 dark:bg-orange-500/20 rounded-full">
            <ShieldAlert className="w-12 h-12 text-orange-500 dark:text-orange-400" />
          </div>
        </div>

        {/* Error Message */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Erreur d&apos;authentification
          </h1>
          <p className="text-gray-600 dark:text-slate-400">
            Un probleme est survenu lors de l&apos;authentification. Veuillez reessayer.
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
            <Link href="/auth/login" className="gap-2">
              <ArrowLeft className="w-4 h-4" />
              Retour connexion
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
