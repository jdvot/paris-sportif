import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white dark:bg-slate-900">
      <div className="flex flex-col items-center gap-6">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
            <span className="text-white text-xl font-bold">PS</span>
          </div>
          <span className="text-2xl font-bold text-gray-900 dark:text-white">
            Paris Sportif
          </span>
        </div>

        {/* Spinner */}
        <Loader2 className="h-10 w-10 animate-spin text-primary-500" />

        {/* Loading text */}
        <div className="text-center">
          <p className="text-gray-600 dark:text-slate-400 text-base">
            Chargement en cours...
          </p>
          <p className="text-gray-400 dark:text-slate-500 text-sm mt-1">
            Preparation de vos predictions
          </p>
        </div>
      </div>
    </div>
  );
}
