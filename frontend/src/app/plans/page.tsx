"use client";

import Link from "next/link";
import { Check, Crown, Zap, X, Sparkles, ArrowLeft, Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

export default function PlansPage() {
  const { isPremium, isAdmin, loading, isAuthenticated } = useAuth();

  const currentPlan = isAdmin ? "admin" : isPremium ? "premium" : "free";

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-dark-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gradient-to-b dark:from-dark-900 dark:to-dark-950 py-12 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-yellow-100 dark:bg-yellow-500/20 mb-6">
            <Crown className="w-10 h-10 text-yellow-500" />
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-4">
            {isPremium || isAdmin ? "Gerez votre abonnement" : "Passez a Premium"}
          </h1>
          <p className="text-gray-600 dark:text-dark-300 text-lg max-w-2xl mx-auto">
            {isPremium || isAdmin
              ? "Vous beneficiez de toutes les fonctionnalites Premium."
              : "Debloquez toutes les fonctionnalites et accedez aux predictions detaillees de nos modeles IA."}
          </p>
        </div>

        {/* Current Plan Badge */}
        {isAuthenticated && (
          <div className="flex justify-center mb-8">
            <div className={cn(
              "inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium",
              currentPlan === "admin"
                ? "bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300"
                : currentPlan === "premium"
                ? "bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300"
                : "bg-gray-100 dark:bg-dark-700 text-gray-700 dark:text-dark-300"
            )}>
              <Sparkles className="w-4 h-4" />
              Votre plan actuel: {currentPlan === "admin" ? "Administrateur" : currentPlan === "premium" ? "Premium" : "Gratuit"}
            </div>
          </div>
        )}

        {/* Plans Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {/* Free Plan */}
          <div className={cn(
            "bg-white dark:bg-dark-800/50 border rounded-2xl p-6 transition-all",
            currentPlan === "free"
              ? "border-primary-500 ring-2 ring-primary-500/20"
              : "border-gray-200 dark:border-dark-700"
          )}>
            {currentPlan === "free" && (
              <div className="mb-4">
                <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300 rounded-full text-xs font-medium">
                  <Check className="w-3 h-3" />
                  Plan actuel
                </span>
              </div>
            )}
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Gratuit</h2>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
              0€ <span className="text-sm text-gray-500 dark:text-dark-400 font-normal">/mois</span>
            </p>
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Acces aux matchs
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Statistiques de base
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                3 picks par jour
              </li>
              <li className="flex items-center gap-3 text-gray-400 dark:text-dark-500 text-sm">
                <X className="w-5 h-5 flex-shrink-0" />
                <span className="line-through">Predictions detaillees</span>
              </li>
              <li className="flex items-center gap-3 text-gray-400 dark:text-dark-500 text-sm">
                <X className="w-5 h-5 flex-shrink-0" />
                <span className="line-through">Analyse IA RAG</span>
              </li>
              <li className="flex items-center gap-3 text-gray-400 dark:text-dark-500 text-sm">
                <X className="w-5 h-5 flex-shrink-0" />
                <span className="line-through">Historique complet</span>
              </li>
            </ul>
            {currentPlan === "free" ? (
              <div className="text-center py-3 px-4 bg-gray-100 dark:bg-dark-700 text-gray-600 dark:text-dark-300 rounded-lg text-sm">
                Votre plan actuel
              </div>
            ) : (
              <div className="text-center py-3 px-4 bg-gray-100 dark:bg-dark-700 text-gray-500 dark:text-dark-400 rounded-lg text-sm">
                Plan de base
              </div>
            )}
          </div>

          {/* Premium Plan */}
          <div className={cn(
            "relative bg-gradient-to-b from-yellow-50 to-orange-50 dark:from-yellow-500/10 dark:to-orange-500/5 border-2 rounded-2xl p-6 transition-all",
            currentPlan === "premium"
              ? "border-yellow-500 ring-2 ring-yellow-500/20"
              : "border-yellow-400/50 dark:border-yellow-500/30"
          )}>
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-yellow-500 text-black text-xs font-semibold px-3 py-1 rounded-full">
              Recommande
            </div>
            {currentPlan === "premium" && (
              <div className="mb-4">
                <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300 rounded-full text-xs font-medium">
                  <Sparkles className="w-3 h-3" />
                  Plan actuel
                </span>
              </div>
            )}
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              Premium
            </h2>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
              9.99€ <span className="text-sm text-gray-500 dark:text-dark-400 font-normal">/mois</span>
            </p>
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Tout le plan gratuit
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Picks illimites
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Predictions detaillees
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Analyse IA RAG
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Historique complet
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Support prioritaire
              </li>
            </ul>
            {currentPlan === "premium" ? (
              <div className="text-center py-3 px-4 bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300 rounded-lg text-sm font-medium">
                Votre plan actuel
              </div>
            ) : (
              <button
                disabled
                className="w-full text-center py-3 px-4 bg-yellow-500 text-black font-semibold rounded-lg opacity-60 cursor-not-allowed"
              >
                Bientot disponible
              </button>
            )}
          </div>

          {/* Enterprise/Admin Plan */}
          <div className={cn(
            "bg-white dark:bg-dark-800/50 border rounded-2xl p-6 transition-all md:col-span-2 lg:col-span-1",
            currentPlan === "admin"
              ? "border-red-500 ring-2 ring-red-500/20"
              : "border-gray-200 dark:border-dark-700"
          )}>
            {currentPlan === "admin" && (
              <div className="mb-4">
                <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300 rounded-full text-xs font-medium">
                  <Sparkles className="w-3 h-3" />
                  Plan actuel
                </span>
              </div>
            )}
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Enterprise</h2>
            <p className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
              Sur mesure
            </p>
            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Tout le plan Premium
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                API acces
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Webhooks personnalises
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                Support dedie
              </li>
              <li className="flex items-center gap-3 text-gray-700 dark:text-dark-300 text-sm">
                <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                SLA garanti
              </li>
            </ul>
            <a
              href="mailto:contact@paris-sportif.ai"
              className="block w-full text-center py-3 px-4 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-semibold rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors"
            >
              Nous contacter
            </a>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">Questions frequentes</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                Comment fonctionne Premium?
              </h3>
              <p className="text-sm text-gray-600 dark:text-dark-400">
                L'abonnement Premium vous donne acces a toutes les predictions detaillees, analyses IA, et picks quotidiens illimites.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                Puis-je annuler a tout moment?
              </h3>
              <p className="text-sm text-gray-600 dark:text-dark-400">
                Oui, vous pouvez annuler votre abonnement a tout moment. Vous conservez l'acces jusqu'a la fin de la periode payee.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                Quels moyens de paiement acceptez-vous?
              </h3>
              <p className="text-sm text-gray-600 dark:text-dark-400">
                Nous acceptons les cartes bancaires (Visa, Mastercard), PayPal, et les virements SEPA pour Enterprise.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                Y a-t-il une periode d'essai?
              </h3>
              <p className="text-sm text-gray-600 dark:text-dark-400">
                Oui, profitez de 7 jours d'essai gratuit Premium pour tester toutes les fonctionnalites.
              </p>
            </div>
          </div>
        </div>

        {/* Back Link */}
        <div className="text-center">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-gray-600 dark:text-dark-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Retour a l'accueil
          </Link>
        </div>
      </div>
    </div>
  );
}
