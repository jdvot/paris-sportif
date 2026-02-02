"use client";

import Link from "next/link";
import { AlertTriangle, ArrowLeft, RefreshCw } from "lucide-react";

export default function AuthErrorPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-dark-900 px-4">
      <div className="max-w-md w-full text-center">
        {/* Error Icon */}
        <div className="mx-auto w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mb-6">
          <AlertTriangle className="w-10 h-10 text-red-500" />
        </div>

        {/* Error Message */}
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-4">
          Erreur d&apos;authentification
        </h1>
        <p className="text-gray-600 dark:text-dark-400 mb-8">
          Une erreur s&apos;est produite lors de la connexion. Cela peut arriver si le lien a expire
          ou si la connexion a ete annulee.
        </p>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/auth/login"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-emerald-500 hover:from-primary-600 hover:to-emerald-600 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-primary-500/25"
          >
            <RefreshCw className="w-5 h-5" />
            Reessayer
          </Link>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-100 dark:bg-dark-800 hover:bg-gray-200 dark:hover:bg-dark-700 text-gray-700 dark:text-dark-300 font-medium rounded-xl transition-all duration-200"
          >
            <ArrowLeft className="w-5 h-5" />
            Retour
          </Link>
        </div>

        {/* Help Text */}
        <p className="mt-8 text-sm text-gray-500 dark:text-dark-500">
          Si le probleme persiste, contactez le support a{" "}
          <a href="mailto:support@paris-sportif.com" className="text-primary-400 hover:underline">
            support@paris-sportif.com
          </a>
        </p>
      </div>
    </div>
  );
}
