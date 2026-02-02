import Link from "next/link";
import { Home, Search } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
      {/* 404 Number */}
      <div className="relative">
        <h1 className="text-8xl sm:text-9xl font-bold bg-gradient-to-r from-primary-500 to-emerald-500 bg-clip-text text-transparent">
          404
        </h1>
        <div className="absolute -top-2 -right-2 w-6 h-6 bg-primary-500 rounded-full animate-ping opacity-75" />
      </div>

      {/* Message */}
      <h2 className="text-2xl sm:text-3xl font-semibold text-gray-900 dark:text-white mt-6">
        Page non trouvee
      </h2>
      <p className="text-gray-600 dark:text-slate-400 mt-3 max-w-md text-sm sm:text-base">
        La page que vous recherchez n&apos;existe pas ou a ete deplacee.
        Verifiez l&apos;URL ou retournez a l&apos;accueil.
      </p>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3 mt-8">
        <Link
          href="/"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-emerald-500 hover:from-primary-600 hover:to-emerald-600 text-white font-medium rounded-xl transition-all shadow-lg shadow-primary-500/25"
        >
          <Home className="w-5 h-5" />
          Accueil
        </Link>
        <Link
          href="/matches"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 text-gray-900 dark:text-white font-medium rounded-xl transition-all border border-gray-200 dark:border-slate-700"
        >
          <Search className="w-5 h-5" />
          Voir les matchs
        </Link>
      </div>
    </div>
  );
}
