"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle, Loader2, AlertCircle } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { fetchDailyPicks } from "@/lib/api";
import type { DailyPick } from "@/lib/types";

export function DailyPicks() {
  const { data: picks, isLoading, error } = useQuery({
    queryKey: ["dailyPicks"],
    queryFn: () => fetchDailyPicks(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <div className="grid gap-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 animate-pulse"
          >
            <div className="h-6 bg-dark-700 rounded w-1/3 mb-4" />
            <div className="h-4 bg-dark-700 rounded w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-dark-800/50 border border-red-500/30 rounded-xl p-8 text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <p className="text-dark-300">Impossible de charger les picks du jour</p>
        <p className="text-dark-500 text-sm mt-2">Verifiez que le backend est en cours d'execution</p>
      </div>
    );
  }

  if (!picks || picks.length === 0) {
    return (
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8 text-center">
        <p className="text-dark-400">Aucun pick disponible pour aujourd'hui</p>
        <p className="text-dark-500 text-sm mt-2">Les picks seront disponibles quand des matchs sont programmes</p>
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
  const { match, prediction, keyFactors, explanation } = pick;

  const homeTeam = match.homeTeam;
  const awayTeam = match.awayTeam;

  const betLabel = {
    home: `Victoire ${homeTeam}`,
    home_win: `Victoire ${homeTeam}`,
    draw: "Match nul",
    away: `Victoire ${awayTeam}`,
    away_win: `Victoire ${awayTeam}`,
  }[prediction.recommendedBet] || prediction.recommendedBet;

  const confidence = prediction.confidence || 0;
  const confidenceColor =
    confidence >= 0.7
      ? "text-primary-400"
      : confidence >= 0.6
      ? "text-yellow-400"
      : "text-orange-400";

  const homeProb = prediction.homeProb || prediction.probabilities?.homeWin || 0;
  const drawProb = prediction.drawProb || prediction.probabilities?.draw || 0;
  const awayProb = prediction.awayProb || prediction.probabilities?.awayWin || 0;

  return (
    <Link
      href={`/match/${match.id}`}
      className="block bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden hover:border-primary-500/50 transition-colors"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between px-4 sm:px-6 py-4 border-b border-dark-700 gap-3 sm:gap-0">
        <div className="flex items-center gap-3 sm:gap-4">
          <span className="flex items-center justify-center w-8 h-8 bg-primary-500 rounded-full text-white font-bold text-sm shrink-0">
            {pick.rank}
          </span>
          <div className="min-w-0">
            <h3 className="font-semibold text-white text-sm sm:text-base truncate">
              {homeTeam} vs {awayTeam}
            </h3>
            <p className="text-xs sm:text-sm text-dark-400">{match.competition}</p>
          </div>
        </div>
        <div className="text-left sm:text-right flex sm:flex-col gap-3 sm:gap-0 shrink-0">
          <p className={cn("font-semibold text-sm sm:text-base", confidenceColor)}>
            {Math.round(confidence * 100)}% confiance
          </p>
          <p className="text-xs sm:text-sm text-dark-400">
            Value: +{Math.round((prediction.valueScore || 0) * 100)}%
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
            isRecommended={prediction.recommendedBet === "home" || prediction.recommendedBet === "home_win"}
          />
          <ProbBar
            label="Nul"
            prob={drawProb}
            isRecommended={prediction.recommendedBet === "draw"}
          />
          <ProbBar
            label={awayTeam}
            prob={awayProb}
            isRecommended={prediction.recommendedBet === "away" || prediction.recommendedBet === "away_win"}
          />
        </div>

        {/* Recommendation */}
        <div className="flex items-center gap-2 mb-4 p-2 sm:p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg">
          <CheckCircle className="w-4 sm:w-5 h-4 sm:h-5 text-primary-400 shrink-0" />
          <span className="font-medium text-primary-400 text-sm sm:text-base">{betLabel}</span>
        </div>

        {/* Explanation */}
        {explanation && (
          <p className="text-dark-300 text-xs sm:text-sm mb-4 line-clamp-2 sm:line-clamp-none">{explanation}</p>
        )}

        {/* Key Factors */}
        {keyFactors && keyFactors.length > 0 && (
          <div className="flex flex-wrap gap-1 sm:gap-2">
            {keyFactors.slice(0, 3).map((factor, i) => (
              <span
                key={i}
                className="px-2 py-1 bg-dark-700 rounded text-xs text-dark-300 truncate max-w-[150px] sm:max-w-none"
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
        <span className={isRecommended ? "text-primary-400" : "text-dark-400"}>
          {displayLabel}
        </span>
        <span className={isRecommended ? "text-primary-400" : "text-dark-400"}>
          {percentage}%
        </span>
      </div>
      <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            isRecommended ? "bg-primary-500" : "bg-dark-500"
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
