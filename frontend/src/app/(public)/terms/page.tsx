"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function TermsPage() {
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
          Conditions d&apos;Utilisation
        </h1>

        <div className="prose dark:prose-invert max-w-none space-y-6 text-gray-700 dark:text-dark-300">
          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              1. Acceptation des conditions
            </h2>
            <p>
              En utilisant WinRate AI, vous acceptez les presentes conditions d&apos;utilisation.
              Si vous n&apos;acceptez pas ces conditions, veuillez ne pas utiliser le service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              2. Description du service
            </h2>
            <p>
              WinRate AI fournit des predictions de paris sportifs basees sur l&apos;intelligence
              artificielle et des modeles statistiques. Ces predictions sont donnees a titre
              indicatif uniquement.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              3. Avertissement sur les paris
            </h2>
            <p className="font-semibold text-amber-600 dark:text-amber-400">
              Important : Les paris sportifs comportent des risques financiers.
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Ne pariez que ce que vous pouvez vous permettre de perdre</li>
              <li>Les predictions ne garantissent pas de gains</li>
              <li>Les performances passees ne presagent pas des resultats futurs</li>
              <li>Jouez de maniere responsable</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              4. Responsabilite
            </h2>
            <p>
              WinRate AI ne peut etre tenu responsable des pertes financieres resultant
              de l&apos;utilisation de nos predictions. L&apos;utilisateur est seul responsable
              de ses decisions de paris.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              5. Propriete intellectuelle
            </h2>
            <p>
              Tout le contenu de WinRate AI (algorithmes, predictions, interface) est protege
              par les droits d&apos;auteur. Toute reproduction non autorisee est interdite.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              6. Modification des conditions
            </h2>
            <p>
              Nous nous reservons le droit de modifier ces conditions a tout moment.
              Les utilisateurs seront informes des modifications importantes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              7. Contact
            </h2>
            <p>
              Pour toute question, contactez-nous a :{" "}
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
