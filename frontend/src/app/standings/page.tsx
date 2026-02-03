"use client";

import { useState } from "react";
import { Trophy, AlertCircle } from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { useGetStandings } from "@/lib/api/endpoints/matches/matches";
import type { StandingsResponse } from "@/lib/api/models";
import { LeagueStandings } from "@/components/LeagueStandings";
import { getErrorMessage } from "@/lib/errors";

const COMPETITIONS = [
  { code: "PL", label: "Premier League", flag: "🇬🇧" },
  { code: "PD", label: "La Liga", flag: "🇪🇸" },
  { code: "BL1", label: "Bundesliga", flag: "🇩🇪" },
  { code: "SA", label: "Serie A", flag: "🇮🇹" },
  { code: "FL1", label: "Ligue 1", flag: "🇫🇷" },
];

export default function StandingsPage() {
  const t = useTranslations("standings");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const [selectedCompetition, setSelectedCompetition] = useState("PL");

  const { data: response, isLoading, error } = useGetStandings(
    selectedCompetition,
    { query: { staleTime: 5 * 60 * 1000 } }
  );

  // Extract standings from response - API returns { data: {...}, status: number }
  const standings = response?.data as StandingsResponse | undefined;

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <section className="text-center py-6 sm:py-8 px-4">
        <div className="flex items-center justify-center gap-2 sm:gap-3 mb-2 sm:mb-3">
          <Trophy className="w-8 sm:w-10 h-8 sm:h-10 text-primary-400" />
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 dark:text-white">
            {t("title")}
          </h1>
        </div>
        <p className="text-gray-600 dark:text-slate-300 text-sm sm:text-base">
          {t("subtitle")}
        </p>
      </section>

      {/* Competition Selector */}
      <section className="px-4 sm:px-0">
        <div className="flex flex-wrap gap-2 sm:gap-3">
          {COMPETITIONS.map((comp) => (
            <button
              key={comp.code}
              onClick={() => setSelectedCompetition(comp.code)}
              className={`px-3 sm:px-4 py-2 rounded-lg font-medium text-sm sm:text-base transition-all ${
                selectedCompetition === comp.code
                  ? "bg-primary-500 text-white shadow-lg shadow-primary-500/30"
                  : "bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700 border border-gray-200 dark:border-slate-700"
              }`}
            >
              <span className="mr-2">{comp.flag}</span>
              {comp.label}
            </button>
          ))}
        </div>
      </section>

      {/* Error State */}
      {error ? (
        <section className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 sm:p-8 mx-4 sm:mx-0 flex items-start gap-3 sm:gap-4">
          <AlertCircle className="w-5 sm:w-6 h-5 sm:h-6 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{tCommon("errorLoading")}</h3>
            <p className="text-gray-500 dark:text-slate-400 text-sm">
              {getErrorMessage(error, t("loadError"))}
            </p>
          </div>
        </section>
      ) : null}

      {/* Standings Table */}
      {!error && standings ? (
        <section className="px-4 sm:px-0 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
              {standings.competition_name}
            </h2>
            {standings.last_updated ? (
              <p className="text-xs sm:text-sm text-gray-500 dark:text-slate-400">
                {t("lastUpdated")}: {new Date(standings.last_updated).toLocaleDateString(locale === "fr" ? "fr-FR" : "en-US")}
              </p>
            ) : null}
          </div>
          <LeagueStandings standings={standings} isLoading={isLoading} />
        </section>
      ) : null}

      {/* Loading State */}
      {isLoading && standings === undefined ? (
        <section className="px-4 sm:px-0">
          <LeagueStandings standings={{ competition_code: selectedCompetition, competition_name: "", standings: [] }} isLoading={true} />
        </section>
      ) : null}

      {/* Info Section */}
      <section className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-6 sm:p-8 mx-4 sm:mx-0 space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white text-base sm:text-lg">{t("aboutTitle")}</h3>
        <div className="space-y-3 text-sm text-gray-600 dark:text-slate-300">
          <p>
            <span className="font-medium text-primary-400">Top 4:</span> {t("championsLeague")}
          </p>
          <p>
            <span className="font-medium text-purple-400">{t("positions56")}:</span> {t("europaLeague")}
          </p>
          <p>
            <span className="font-medium text-red-400">{t("lastPositions")}:</span> {t("relegation")}
          </p>
          <p className="text-gray-500 dark:text-slate-400 text-xs">
            {t("dataSource")}
          </p>
        </div>
      </section>
    </div>
  );
}
