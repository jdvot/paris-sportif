"use client";

import { AlertCircle, CheckCircle } from "lucide-react";
import Link from "next/link";
import { cn, isAuthError } from "@/lib/utils";
import { LoadingState } from "@/components/LoadingState";
import { useGetDailyPicks } from "@/lib/api/endpoints/predictions/predictions";
import type { DailyPick, Prediction } from "@/lib/api/models";

export function DailyPicks() {
  const { data: response, isLoading, error } = useGetDailyPicks(
    undefined,
    { query: { staleTime: 5 * 60 * 1000 } }
  );

  // Extract picks from response - API returns { data: { picks: [...] }, status: number }
  const picks = (response?.data as { picks?: DailyPick[] } | undefined)?.picks || [];

  if (isLoading) {
    return (
      <LoadingState
        variant="picks"
        count={5}
        message="Analyse des matchs en cours..."
      />
    );
  }

  // Skip error UI for auth errors (global handler will redirect)
  if (error && !isAuthError(error)) {
    return (
      <div className="bg-white dark:bg-slate-800/50 border border-red-200 dark:border-red-500/30 rounded-xl p-8 text-center">
        <AlertCircle className="w-12 h-12 text-red-500 dark:text-red-400 mx-auto mb-4" />
        <p className="text-gray-700 dark:text-slate-300">Impossible de charger les picks du jour</p>
        <p className="text-gray-500 dark:text-slate-500 text-sm mt-2">Verifiez que le backend est en cours d'execution</p>
      </div>
    );
  }

  // Auth error - let global handler redirect, show loading state
  if (error && isAuthError(error)) {
    return (
      <LoadingState
        variant="picks"
        count={5}
        message="Redirection en cours..."
      />
    );
  }

  if (!picks || picks.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-8 text-center">
        <p className="text-gray-600 dark:text-slate-400">Aucun pick disponible pour aujourd'hui</p>
        <p className="text-gray-500 dark:text-slate-500 text-sm mt-2">Les picks seront disponibles quand des matchs sont programmes</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {picks.map((pick) => (
        <PickCard key={pick.rank} pick={pick} />
      ))}
    </div>
  );
}

function PickCard({ pick }: { pick: DailyPick }) {
  const { prediction } = pick;

  // Use snake_case properties from Orval types
  const homeTeam = prediction.home_team;
  const awayTeam = prediction.away_team;
  const matchId = prediction.match_id;

  const betLabel = {
    home: `Victoire ${homeTeam}`,
    home_win: `Victoire ${homeTeam}`,
    draw: "Match nul",
    away: `Victoire ${awayTeam}`,
    away_win: `Victoire ${awayTeam}`,
  }[prediction.recommended_bet] || prediction.recommended_bet;

  const confidence = prediction.confidence || 0;
  const confidenceColor =
    confidence >= 0.7
      ? "text-primary-600 dark:text-primary-400"
      : confidence >= 0.6
      ? "text-yellow-600 dark:text-yellow-400"
      : "text-orange-600 dark:text-orange-400";

  // Use snake_case probabilities from Orval types
  const homeProb = prediction.probabilities?.home_win || 0;
  const drawProb = prediction.probabilities?.draw || 0;
  const awayProb = prediction.probabilities?.away_win || 0;

  // Get competition from match_date context or default
  const competition = "Football";

  return (
    <Link
      href={`/match/${matchId}`}
      className="block bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden hover:border-primary-500/50 transition-colors"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-200 dark:border-slate-700 gap-3 sm:gap-0">
        <div className="flex items-center gap-3 sm:gap-4">
          <span className="flex items-center justify-center w-8 h-8 bg-primary-500 rounded-full text-white font-bold text-sm shrink-0">
            {pick.rank}
          </span>
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base truncate">
              {homeTeam} vs {awayTeam}
            </h3>
            <p className="text-xs sm:text-sm text-gray-600 dark:text-slate-400">{competition}</p>
          </div>
        </div>
        <div className="text-left sm:text-right flex sm:flex-col gap-3 sm:gap-0 shrink-0">
          <p className={cn("font-semibold text-sm sm:text-base", confidenceColor)}>
            {Math.round(confidence * 100)}% confiance
          </p>
          <p className="text-xs sm:text-sm text-gray-600 dark:text-slate-400">
            Value: +{Math.round((prediction.value_score || 0) * 100)}%
          </p>
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
            label="Nul"
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
          <p className="text-gray-700 dark:text-slate-300 text-xs sm:text-sm mb-4 line-clamp-2 sm:line-clamp-none">{prediction.explanation}</p>
        )}

        {/* Key Factors */}
        {prediction.key_factors && prediction.key_factors.length > 0 && (
          <div className="flex flex-wrap gap-1 sm:gap-2">
            {prediction.key_factors.slice(0, 3).map((factor, i) => (
              <span
                key={i}
                className="px-2 py-1 bg-gray-100 dark:bg-slate-700 rounded text-xs text-gray-700 dark:text-slate-300 truncate max-w-[150px] sm:max-w-none"
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
        <span className={isRecommended ? "text-primary-600 dark:text-primary-400" : "text-gray-600 dark:text-slate-400"}>
          {displayLabel}
        </span>
        <span className={isRecommended ? "text-primary-600 dark:text-primary-400" : "text-gray-600 dark:text-slate-400"}>
          {percentage}%
        </span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            isRecommended ? "bg-primary-500" : "bg-gray-300 dark:bg-slate-500"
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
