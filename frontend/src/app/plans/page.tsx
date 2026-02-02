"use client";

import Link from "next/link";
import { Check, Crown, Zap } from "lucide-react";

export default function PlansPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <Crown className="w-16 h-16 text-yellow-400 mx-auto mb-4" />
          <h1 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Passez à Premium
          </h1>
          <p className="text-slate-300 text-lg max-w-2xl mx-auto">
            Débloquez toutes les fonctionnalités et accédez aux prédictions détaillées
            de nos modèles IA.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mb-12">
          {/* Free Plan */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-white mb-2">Gratuit</h2>
            <p className="text-3xl font-bold text-white mb-6">
              0€ <span className="text-sm text-slate-400 font-normal">/mois</span>
            </p>
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-3 text-slate-300">
                <Check className="w-5 h-5 text-green-400" />
                Accès aux matchs
              </li>
              <li className="flex items-center gap-3 text-slate-300">
                <Check className="w-5 h-5 text-green-400" />
                Statistiques de base
              </li>
              <li className="flex items-center gap-3 text-slate-400 line-through">
                Prédictions détaillées
              </li>
              <li className="flex items-center gap-3 text-slate-400 line-through">
                Picks quotidiens
              </li>
            </ul>
            <Link
              href="/"
              className="block w-full text-center py-3 px-4 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-colors"
            >
              Plan actuel
            </Link>
          </div>

          {/* Premium Plan */}
          <div className="bg-gradient-to-b from-yellow-500/20 to-yellow-600/10 border-2 border-yellow-500/50 rounded-2xl p-8 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-yellow-500 text-black text-sm font-semibold px-4 py-1 rounded-full">
              Recommandé
            </div>
            <h2 className="text-xl font-semibold text-white mb-2 flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-400" />
              Premium
            </h2>
            <p className="text-3xl font-bold text-white mb-6">
              9.99€ <span className="text-sm text-slate-400 font-normal">/mois</span>
            </p>
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-3 text-slate-300">
                <Check className="w-5 h-5 text-green-400" />
                Tout le plan gratuit
              </li>
              <li className="flex items-center gap-3 text-slate-300">
                <Check className="w-5 h-5 text-green-400" />
                5 picks quotidiens IA
              </li>
              <li className="flex items-center gap-3 text-slate-300">
                <Check className="w-5 h-5 text-green-400" />
                Prédictions détaillées
              </li>
              <li className="flex items-center gap-3 text-slate-300">
                <Check className="w-5 h-5 text-green-400" />
                Analyse des modèles
              </li>
              <li className="flex items-center gap-3 text-slate-300">
                <Check className="w-5 h-5 text-green-400" />
                Support prioritaire
              </li>
            </ul>
            <button
              disabled
              className="block w-full text-center py-3 px-4 bg-yellow-500 text-black font-semibold rounded-lg opacity-50 cursor-not-allowed"
            >
              Bientôt disponible
            </button>
          </div>
        </div>

        <div className="text-center">
          <Link
            href="/"
            className="text-slate-400 hover:text-white transition-colors"
          >
            ← Retour à l'accueil
          </Link>
        </div>
      </div>
    </div>
  );
}
