"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-900 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <Link
          href="/auth/login"
          className="inline-flex items-center gap-2 text-gray-600 dark:text-dark-400 hover:text-primary-500 mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour
        </Link>

        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          Politique de Confidentialite
        </h1>

        <div className="prose dark:prose-invert max-w-none space-y-6 text-gray-700 dark:text-dark-300">
          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              1. Collecte des donnees
            </h2>
            <p>
              WinRate AI collecte uniquement les donnees necessaires au fonctionnement du service :
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Adresse email (pour l&apos;authentification)</li>
              <li>Preferences utilisateur (langue, theme, notifications)</li>
              <li>Historique des paris (pour le suivi de performance)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              2. Utilisation des donnees
            </h2>
            <p>Vos donnees sont utilisees pour :</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Fournir et ameliorer nos services de predictions</li>
              <li>Personnaliser votre experience</li>
              <li>Envoyer des notifications (si activees)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              3. Protection des donnees
            </h2>
            <p>
              Nous utilisons des mesures de securite standard pour proteger vos donnees,
              incluant le chiffrement SSL et l&apos;authentification securisee via Supabase.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              4. Vos droits
            </h2>
            <p>Conformement au RGPD, vous pouvez :</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Acceder a vos donnees personnelles</li>
              <li>Demander la rectification ou suppression de vos donnees</li>
              <li>Exporter vos donnees</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              5. Contact
            </h2>
            <p>
              Pour toute question concernant vos donnees, contactez-nous a :{" "}
              <a href="mailto:contact@winrate-ai.com" className="text-primary-500">
                contact@winrate-ai.com
              </a>
            </p>
          </section>

          <p className="text-sm text-gray-500 dark:text-dark-500 mt-8">
            Derniere mise a jour : Fevrier 2026
          </p>
        </div>
      </div>
    </div>
  );
}
