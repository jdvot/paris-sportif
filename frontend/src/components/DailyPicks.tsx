"use client";

import { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, CalendarDays } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { cn, isAuthError } from "@/lib/utils";
import { LoadingState } from "@/components/LoadingState";
import { useGetDailyPicks } from "@/lib/api/endpoints/predictions/predictions";
import type { DailyPick } from "@/lib/api/models";
import { ValueBetIndicator } from "@/components/ValueBetBadge";
import { getConfidenceTier, formatConfidence, isValueBet, formatValue } from "@/lib/constants";

// Helper to format date as YYYY-MM-DD
function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

// Get dates for fallback (today, yesterday, 2 days ago, etc.)
function getFallbackDates(): string[] {
  const dates: string[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    dates.push(formatDate(d));
  }
  return dates;
}

export function DailyPicks() {
  const t = useTranslations("dailyPicks");
  const [fallbackDateIndex, setFallbackDateIndex] = useState(0);
  const [displayDate, setDisplayDate] = useState<string | null>(null);

  const fallbackDates = getFallbackDates();
  const currentDate = fallbackDates[fallbackDateIndex];

  // Only pass date param if we're looking at a past date
  const dateParam = fallbackDateIndex > 0 ? currentDate : undefined;

  const { data: response, isLoading, error } = useGetDailyPicks(
    dateParam ? { date: dateParam } : undefined,
    { query: { staleTime: 5 * 60 * 1000 } }
  );

  // Extract picks from response - API returns { data: { picks: [...] }, status: number }
  const picks = (response?.data as { picks?: DailyPick[]; date?: string } | undefined)?.picks || [];
  const responseDate = (response?.data as { date?: string } | undefined)?.date;

  // If no picks for today, try previous days
  useEffect(() => {
    if (!isLoading && picks.length === 0 && fallbackDateIndex < 6) {
      // No picks, try previous day
      const timer = setTimeout(() => {
        setFallbackDateIndex(prev => prev + 1);
      }, 500);
      return () => clearTimeout(timer);
    }
    if (picks.length > 0) {
      setDisplayDate(responseDate || currentDate);
    }
  }, [isLoading, picks.length, fallbackDateIndex, responseDate, currentDate]);

  if (isLoading) {
    return (
      <LoadingState
        variant="picks"
        count={5}
        message={t("loading")}
      />
    );
  }

  // Skip error UI for auth errors (global handler will redirect)
  if (error && !isAuthError(error)) {
    return (
      <div className="bg-white dark:bg-dark-800/50 border border-red-200 dark:border-red-500/30 rounded-xl p-8 text-center">
        <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mx-auto mb-4" />
        <p className="text-gray-700 dark:text-dark-300">{t("loadError")}</p>
        <p className="text-gray-500 dark:text-dark-500 text-sm mt-2">{t("checkBackend")}</p>
      </div>
    );
  }

  // Auth error - let global handler redirect, show loading state
  if (error && isAuthError(error)) {
    return (
      <LoadingState
        variant="picks"
        count={5}
        message={t("redirecting")}
      />
    );
  }

  // Still searching for picks in previous days
  if (!picks || picks.length === 0) {
    if (fallbackDateIndex < 6) {
      return (
        <LoadingState
          variant="picks"
          count={3}
          message={t("searchingPreviousDays") || "Recherche des picks récents..."}
        />
      );
    }
    return (
      <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-8 text-center">
        <p className="text-gray-600 dark:text-dark-400">{t("empty")}</p>
        <p className="text-gray-500 dark:text-dark-500 text-sm mt-2">{t("emptyHint")}</p>
      </div>
    );
  }

  // Show banner if showing past picks
  const isShowingPastPicks = fallbackDateIndex > 0;

  return (
    <div className="space-y-4">
      {/* Banner for past picks */}
      {isShowingPastPicks && displayDate && (
        <div className="flex items-center gap-2 p-3 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 rounded-lg">
          <CalendarDays className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
          <p className="text-sm text-amber-700 dark:text-amber-300">
            {t("showingPicksFrom") || "Affichage des picks du"}{" "}
            <span className="font-semibold">
              {new Date(displayDate).toLocaleDateString("fr-FR", {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </span>
          </p>
        </div>
      )}

      <div className="grid gap-4">
        {picks.map((pick) => (
          <PickCard key={pick.rank} pick={pick} />
        ))}
      </div>
    </div>
  );
}

function PickCard({ pick }: { pick: DailyPick }) {
  const t = useTranslations("dailyPicks");
  const { prediction } = pick;

  // Use snake_case properties from Orval types
  const homeTeam = prediction.home_team;
  const awayTeam = prediction.away_team;
  const matchId = prediction.match_id;

  const getBetLabel = (bet: string) => {
    if (bet === "home" || bet === "home_win") return t("homeWin", { team: homeTeam });
    if (bet === "draw") return t("draw");
    if (bet === "away" || bet === "away_win") return t("awayWin", { team: awayTeam });
    return bet;
  };
  const betLabel = getBetLabel(prediction.recommended_bet);

  const confidence = prediction.confidence || 0;
  const valueScore = prediction.value_score || 0;
  const confidenceTier = getConfidenceTier(confidence);
  const confidenceColor = confidenceTier.textClass;

  // Use snake_case probabilities from Orval types
  const homeProb = prediction.probabilities?.home_win || 0;
  const drawProb = prediction.probabilities?.draw || 0;
  const awayProb = prediction.probabilities?.away_win || 0;

  // Get competition from match_date context or default
  const competition = t("sport");

  return (
    <Link
      href={`/match/${matchId}`}
      className="block bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden hover:border-primary-500/50 transition-colors"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-200 dark:border-dark-700 gap-3 sm:gap-0">
        <div className="flex items-center gap-3 sm:gap-4">
          <span className="flex items-center justify-center w-8 h-8 bg-primary-500 rounded-full text-white font-bold text-sm shrink-0">
            {pick.rank}
          </span>
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base truncate">
              {homeTeam} vs {awayTeam}
            </h3>
            <p className="text-xs sm:text-sm text-gray-600 dark:text-dark-400">{competition}</p>
          </div>
        </div>
        <div className="text-left sm:text-right flex sm:flex-col gap-3 sm:gap-1 shrink-0">
          <div className="flex items-center gap-2">
            <p className={cn("font-semibold text-sm sm:text-base", confidenceColor)}>
              {formatConfidence(confidence)} {t("confidence")}
            </p>
            <span className={cn(
              "hidden sm:inline-flex text-xs font-medium px-1.5 py-0.5 rounded-full",
              confidenceTier.bgClass,
              confidenceTier.textClass
            )}>
              {confidenceTier.label}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <p className="text-xs sm:text-sm text-gray-600 dark:text-dark-400">
              Value: {formatValue(valueScore)}
            </p>
            {isValueBet(valueScore) && <ValueBetIndicator valueScore={valueScore} />}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 sm:px-6 py-4">
        {/* Probabilities */}
        <div className="flex flex-col sm:flex-row gap-2 mb-4">
          <ProbBar
            label={homeTeam}
            prob={homeProb}
            isRecommended={prediction.recommended_bet === "home" || prediction.recommended_bet === "home_win"}
          />
          <ProbBar
            label={t("drawShort")}
            prob={drawProb}
            isRecommended={prediction.recommended_bet === "draw"}
          />
          <ProbBar
            label={awayTeam}
            prob={awayProb}
            isRecommended={prediction.recommended_bet === "away" || prediction.recommended_bet === "away_win"}
          />
        </div>

        {/* Recommendation */}
        <div className="flex items-center gap-2 mb-4 p-2 sm:p-3 bg-primary-100 dark:bg-primary-500/10 border border-primary-300 dark:border-primary-500/30 rounded-lg">
          <CheckCircle className="w-4 sm:w-5 h-4 sm:h-5 text-primary-600 dark:text-primary-400 shrink-0" />
          <span className="font-medium text-primary-600 dark:text-primary-400 text-sm sm:text-base">{betLabel}</span>
        </div>

        {/* Explanation */}
        {prediction.explanation && (
          <p className="text-gray-700 dark:text-dark-300 text-xs sm:text-sm mb-4 line-clamp-2 sm:line-clamp-none">{prediction.explanation}</p>
        )}

        {/* Key Factors */}
        {prediction.key_factors && prediction.key_factors.length > 0 && (
          <div className="flex flex-wrap gap-1 sm:gap-2">
            {prediction.key_factors.slice(0, 3).map((factor, i) => (
              <span
                key={i}
                className="px-2 py-1 bg-gray-100 dark:bg-dark-700 rounded text-xs text-gray-700 dark:text-dark-300 truncate max-w-[150px] sm:max-w-none"
              >
                {factor}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}

function ProbBar({
  label,
  prob,
  isRecommended,
}: {
  label: string;
  prob: number;
  isRecommended: boolean;
}) {
  const displayLabel = label.length > 12 ? label.slice(0, 12) + "..." : label;
  const percentage = Math.round(prob * 100);

  return (
    <div className="flex-1">
      <div className="flex justify-between text-xs mb-1">
        <span className={isRecommended ? "text-primary-600 dark:text-primary-400" : "text-gray-600 dark:text-dark-400"}>
          {displayLabel}
        </span>
        <span className={isRecommended ? "text-primary-600 dark:text-primary-400" : "text-gray-600 dark:text-dark-400"}>
          {percentage}%
        </span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-dark-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            isRecommended ? "bg-primary-500" : "bg-gray-300 dark:bg-dark-500"
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
