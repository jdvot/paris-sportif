"use client";

import { useState } from "react";
import { format, subDays } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { History, CheckCircle, XCircle, Clock, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useTranslations, useLocale } from "next-intl";
import { cn } from "@/lib/utils";
import { useGetDailyPicks } from "@/lib/api/endpoints/predictions/predictions";
import type { DailyPick } from "@/lib/api/models";
import { StreakTracker } from "@/components/StreakTracker";
import { ExportCSV } from "@/components/ExportCSV";
import { getConfidenceTier } from "@/lib/constants";

export default function HistoryPage() {
  const t = useTranslations("history");
  const tCommon = useTranslations("common");
  const tDailyPicks = useTranslations("dailyPicks");
  const locale = useLocale();
  const dateLocale = locale === "fr" ? fr : enUS;
  const [daysBack, setDaysBack] = useState(7);

  // Fetch predictions for multiple past days
  const dates = Array.from({ length: daysBack }, (_, i) =>
    format(subDays(new Date(), i + 1), "yyyy-MM-dd")
  );

  // We'll use the first date's query for now (a real implementation would aggregate)
  const { data: response, isLoading } = useGetDailyPicks(
    { date: dates[0] },
    { query: { staleTime: 5 * 60 * 1000 } }
  );

  const picks = (response?.data as { picks?: DailyPick[] } | undefined)?.picks || [];

  // NOTE: Result tracking requires PAR-168 (user bet tracking feature)
  // For now, all picks show as pending - no simulated data
  const historicalPicks = picks.map((pick) => ({
    ...pick,
    result: "pending" as "pending" | "won" | "lost",
    actualScore: null as string | null,
  }));

  const wonCount = 0;
  const lostCount = 0;
  const pendingCount = historicalPicks.length;
  const winRate = 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <History className="w-8 h-8 text-primary-500" />
            {t("title")}
          </h1>
          <p className="text-gray-600 dark:text-dark-400 mt-1">
            {t("subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={daysBack}
            onChange={(e) => setDaysBack(Number(e.target.value))}
            className="px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg text-sm text-gray-900 dark:text-white"
          >
            <option value={7}>{t("filters.last7Days")}</option>
            <option value={14}>{t("filters.last14Days")}</option>
            <option value={30}>{t("filters.last30Days")}</option>
          </select>
          <ExportCSV picks={picks} filename="historique" />
        </div>
      </div>

      {/* Streak Tracker */}
      <StreakTracker variant="full" />

      {/* Stats Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded-xl p-4 text-center">
          <CheckCircle className="w-6 h-6 text-green-500 mx-auto mb-2" />
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{wonCount}</p>
          <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.won")}</p>
        </div>
        <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl p-4 text-center">
          <XCircle className="w-6 h-6 text-red-500 mx-auto mb-2" />
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">{lostCount}</p>
          <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.lost")}</p>
        </div>
        <div className="bg-yellow-50 dark:bg-yellow-500/10 border border-yellow-200 dark:border-yellow-500/30 rounded-xl p-4 text-center">
          <Clock className="w-6 h-6 text-yellow-500 mx-auto mb-2" />
          <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{pendingCount}</p>
          <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.pending")}</p>
        </div>
        <div className="bg-primary-50 dark:bg-primary-500/10 border border-primary-200 dark:border-primary-500/30 rounded-xl p-4 text-center">
          <TrendingUp className="w-6 h-6 text-primary-500 mx-auto mb-2" />
          <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">{winRate.toFixed(0)}%</p>
          <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.winRate")}</p>
        </div>
      </div>

      {/* History List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-24 bg-gray-100 dark:bg-dark-700 rounded-xl animate-pulse"
            />
          ))}
        </div>
      ) : historicalPicks.length === 0 ? (
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-8 text-center">
          <History className="w-12 h-12 text-gray-400 dark:text-dark-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {t("empty")}
          </h3>
          <p className="text-gray-600 dark:text-dark-400 mb-4">
            {t("emptyHint")}
          </p>
          <Link
            href="/picks"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            {tCommon("viewPicks")}
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {historicalPicks.map((pick) => {
            const prediction = pick.prediction;
            const confidence = prediction.confidence || 0;
            const confidenceTier = getConfidenceTier(confidence);
            const betLabel = {
              home: tDailyPicks("homeWin", { team: prediction.home_team }),
              home_win: tDailyPicks("homeWin", { team: prediction.home_team }),
              draw: tDailyPicks("draw"),
              away: tDailyPicks("awayWin", { team: prediction.away_team }),
              away_win: tDailyPicks("awayWin", { team: prediction.away_team }),
            }[prediction.recommended_bet] || prediction.recommended_bet;

            return (
              <Link
                key={pick.rank}
                href={`/match/${prediction.match_id}`}
                className={cn(
                  "block bg-white dark:bg-dark-800/50 border rounded-xl p-4 transition-all hover:border-primary-400 dark:hover:border-primary-500/50",
                  pick.result === "won"
                    ? "border-green-300 dark:border-green-500/30"
                    : pick.result === "lost"
                    ? "border-red-300 dark:border-red-500/30"
                    : "border-gray-200 dark:border-dark-700"
                )}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    {/* Result Icon */}
                    <div
                      className={cn(
                        "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0",
                        pick.result === "won"
                          ? "bg-green-100 dark:bg-green-500/20"
                          : pick.result === "lost"
                          ? "bg-red-100 dark:bg-red-500/20"
                          : "bg-yellow-100 dark:bg-yellow-500/20"
                      )}
                    >
                      {pick.result === "won" ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : pick.result === "lost" ? (
                        <XCircle className="w-5 h-5 text-red-500" />
                      ) : (
                        <Clock className="w-5 h-5 text-yellow-500" />
                      )}
                    </div>

                    {/* Match Info */}
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 dark:text-white truncate">
                        {prediction.home_team} vs {prediction.away_team}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-dark-400">
                        <span>{betLabel}</span>
                        <span className={cn("px-1.5 py-0.5 rounded-full", confidenceTier.bgClass, confidenceTier.textClass)}>
                          {Math.round(confidence * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Score/Status */}
                  <div className="text-right flex-shrink-0">
                    {pick.actualScore ? (
                      <p className="text-lg font-bold text-gray-900 dark:text-white">
                        {pick.actualScore}
                      </p>
                    ) : (
                      <p className="text-sm text-yellow-600 dark:text-yellow-400">{t("inProgress")}</p>
                    )}
                    <p className="text-xs text-gray-500 dark:text-dark-400">
                      {prediction.match_date
                        ? format(new Date(prediction.match_date), "d MMM", { locale: dateLocale })
                        : ""}
                    </p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Info Banner */}
      <div className="bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30 rounded-xl p-4">
        <p className="text-sm text-blue-800 dark:text-blue-300">
          {t("infoBanner")}
        </p>
      </div>
    </div>
  );
}
