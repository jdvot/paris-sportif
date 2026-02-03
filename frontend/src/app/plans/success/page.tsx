"use client";

import Link from "next/link";
import { CheckCircle, Crown, ArrowRight, Sparkles } from "lucide-react";
import { useEffect } from "react";
import confetti from "canvas-confetti";

export default function PaymentSuccessPage() {
  useEffect(() => {
    // Celebrate with confetti!
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 },
      colors: ["#eab308", "#fbbf24", "#fef08a"],
    });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gradient-to-b dark:from-dark-900 dark:to-dark-950 flex items-center justify-center py-12 px-4">
      <div className="max-w-md w-full text-center">
        {/* Success Icon */}
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 dark:bg-green-500/20 mb-6">
          <CheckCircle className="w-10 h-10 text-green-500" />
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          Bienvenue dans Premium!
        </h1>

        {/* Description */}
        <p className="text-gray-600 dark:text-dark-300 text-lg mb-8">
          Votre abonnement a ete active avec succes. Vous avez maintenant acces a toutes les fonctionnalites Premium.
        </p>

        {/* Features unlocked */}
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-6 mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Crown className="w-5 h-5 text-yellow-500" />
            <span className="font-semibold text-gray-900 dark:text-white">
              Fonctionnalites debloquees
            </span>
          </div>
          <ul className="space-y-3 text-left">
            <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
              <Sparkles className="w-4 h-4 text-yellow-500 flex-shrink-0" />
              Picks illimites chaque jour
            </li>
            <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
              <Sparkles className="w-4 h-4 text-yellow-500 flex-shrink-0" />
              Predictions detaillees avec analyse IA
            </li>
            <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
              <Sparkles className="w-4 h-4 text-yellow-500 flex-shrink-0" />
              Historique complet des performances
            </li>
            <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
              <Sparkles className="w-4 h-4 text-yellow-500 flex-shrink-0" />
              Support prioritaire
            </li>
          </ul>
        </div>

        {/* CTA */}
        <Link
          href="/picks"
          className="inline-flex items-center gap-2 px-6 py-3 bg-yellow-500 text-black font-semibold rounded-lg hover:bg-yellow-400 transition-colors"
        >
          Voir les picks du jour
          <ArrowRight className="w-4 h-4" />
        </Link>

        {/* Secondary link */}
        <div className="mt-4">
          <Link
            href="/"
            className="text-gray-600 dark:text-dark-400 hover:text-gray-900 dark:hover:text-white transition-colors text-sm"
          >
            Retour a l'accueil
          </Link>
        </div>
      </div>
    </div>
  );
}
