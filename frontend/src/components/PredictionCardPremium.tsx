"use client";

import Link from "next/link";
import { CheckCircle, TrendingUp, AlertCircle, Zap } from "lucide-react";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { cn } from "@/lib/utils";
import type { DailyPick } from "@/lib/api/models";
import { RAGContext } from "./RAGContext";
import { ValueBetIndicator } from "./ValueBetBadge";
import { FavoriteButton } from "./FavoriteButton";
import {
  getConfidenceTier as getConfidenceTierFromConstants,
  getValueTier as getValueTierFromConstants,
  isValueBet,
  formatConfidence,
  formatValue,
  CONFIDENCE_TIERS,
} from "@/lib/constants";

interface PredictionCardPremiumProps {
  pick: DailyPick;
  index?: number;
  isTopPick?: boolean;
}

export function PredictionCardPremium({
  pick,
  index = 0,
  isTopPick = false,
}: PredictionCardPremiumProps) {
  const { prediction } = pick;
  const confidence = prediction.confidence || 0;
  const valueScore = prediction.value_score || 0;

  const matchDate = prediction.match_date ? new Date(prediction.match_date) : new Date();

  // Use centralized constants for tiers
  const confidenceTier = getConfidenceTierFromConstants(confidence);
  const valueTier = getValueTierFromConstants(valueScore);

  // Bet label
  const betLabels: Record<string, string> = {
    home: `Victoire ${prediction.home_team}`,
    home_win: `Victoire ${prediction.home_team}`,
    draw: "Match nul",
    away: `Victoire ${prediction.away_team}`,
    away_win: `Victoire ${prediction.away_team}`,
  };
  const betLabel = betLabels[prediction.recommended_bet] || prediction.recommended_bet;

  // Short bet label for mobile
  const shortBetLabels: Record<string, string> = {
    home: prediction.home_team.split(" ")[0],
    home_win: prediction.home_team.split(" ")[0],
    draw: "Nul",
    away: prediction.away_team.split(" ")[0],
    away_win: prediction.away_team.split(" ")[0],
  };
  const shortBetLabel = shortBetLabels[prediction.recommended_bet] || prediction.recommended_bet;

  const isRecommendedBet = (bet: string) =>
    prediction.recommended_bet === bet ||
    prediction.recommended_bet === (bet === "home" ? "home_win" : bet === "away" ? "away_win" : bet);

  const matchId = prediction.match_id;

  return (
    <Link href={`/match/${matchId}`} className="block">
      <div
        className={cn(
          "group relative overflow-hidden rounded-xl border transition-smooth cursor-pointer",
          "bg-white dark:bg-gradient-to-br dark:from-slate-800/90 dark:to-slate-900/80",
          "border-gray-200 dark:border-slate-700 hover:border-primary-400 dark:hover:border-primary-500/50",
          "animate-stagger-in",
          isTopPick && "border-primary-400 dark:border-primary-500/50 bg-gradient-to-br from-primary-50 dark:from-primary-950/40 to-white dark:to-slate-900/80"
        )}
        style={{ animationDelay: `${index * 50}ms` } as React.CSSProperties}
      >
      {/* Background glow effect on hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-10 bg-gradient-to-br from-primary-500 to-transparent transition-opacity duration-300 pointer-events-none" />

      {/* Main Content */}
      <div className="relative z-10">
        {/* Header with rank and match info */}
        <div className="px-3 sm:px-6 py-3 sm:py-4 border-b border-gray-200 dark:border-slate-700/50">
          <div className="flex items-start justify-between gap-3">
            {/* Left: Rank and Match Info */}
            <div className="flex items-start gap-2 sm:gap-4 flex-1 min-w-0">
              {/* Rank Badge */}
              <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
                <span className="text-white font-bold text-xs sm:text-sm">{pick.rank}</span>
              </div>

              {/* Match Details */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-bold text-gray-900 dark:text-white leading-tight text-sm sm:text-base">
                    <span className="hidden sm:inline">{prediction.home_team} vs {prediction.away_team}</span>
                    <span className="sm:hidden">
                      {prediction.home_team.split(" ")[0]} vs {prediction.away_team.split(" ")[0]}
                    </span>
                  </h3>
                  {isTopPick && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gradient-to-r from-primary-500 to-emerald-500 rounded-full text-xs font-bold text-white whitespace-nowrap">
                      <Zap className="w-3 h-3" />
                      Top Pick
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5 mt-1 text-[10px] sm:text-xs text-gray-500 dark:text-slate-400 flex-wrap">
                  <span>•</span>
                  <span>{format(matchDate, "d MMM, HH:mm", { locale: fr })}</span>
                </div>
              </div>
            </div>

            {/* Right: Confidence Score + Favorite */}
            <div className="flex items-start gap-2">
              <div className={cn(
                "inline-flex flex-col items-center gap-1 px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg",
                "bg-gradient-to-br",
                confidence >= 0.7 ? "from-primary-100 dark:from-primary-500/20 to-primary-200 dark:to-primary-600/10" :
                confidence >= 0.6 ? "from-yellow-100 dark:from-yellow-500/20 to-yellow-200 dark:to-yellow-600/10" :
                "from-orange-100 dark:from-orange-500/20 to-orange-200 dark:to-orange-600/10"
              )}>
                <span className="text-xs sm:text-xs font-bold text-primary-700 dark:text-primary-300">
                  {Math.round(confidence * 100)}%
                </span>
                <span className="text-[10px] text-gray-500 dark:text-slate-400">confiance</span>
              </div>
              <FavoriteButton
                match={{
                  matchId: prediction.match_id,
                  homeTeam: prediction.home_team,
                  awayTeam: prediction.away_team,
                  matchDate: prediction.match_date || new Date().toISOString(),
                  competition: (prediction as { competition?: string }).competition,
                }}
                size="sm"
              />
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-3 sm:px-6 py-3 sm:py-4 space-y-3 sm:space-y-4">
          {/* Probability Bars */}
          <div className="space-y-2">
            <div className="flex gap-1.5 sm:gap-2">
              <ProbBarEnhanced
                label={prediction.home_team}
                prob={prediction.probabilities?.home_win ?? 0}
                isRecommended={isRecommendedBet("home")}
              />
              <ProbBarEnhanced
                label="Nul"
                prob={prediction.probabilities?.draw ?? 0}
                isRecommended={isRecommendedBet("draw")}
              />
              <ProbBarEnhanced
                label={prediction.away_team}
                prob={prediction.probabilities?.away_win ?? 0}
                isRecommended={isRecommendedBet("away")}
              />
            </div>
          </div>

          {/* Recommended Bet - Enhanced */}
          <div className={cn(
            "flex items-center gap-2 p-2 sm:p-3 rounded-lg border-2 transition-smooth",
            "bg-gradient-to-r",
            confidence >= 0.7 ? "from-primary-100 dark:from-primary-500/15 to-emerald-100 dark:to-emerald-500/10 border-primary-400 dark:border-primary-500/50" :
            confidence >= 0.6 ? "from-yellow-100 dark:from-yellow-500/15 to-orange-100 dark:to-orange-500/10 border-yellow-400 dark:border-yellow-500/50" :
            "from-orange-100 dark:from-orange-500/15 to-red-100 dark:to-red-500/10 border-orange-400 dark:border-orange-500/50"
          )}>
            <CheckCircle className={cn(
              "w-4 sm:w-5 h-4 sm:h-5 flex-shrink-0",
              confidence >= 0.7 ? "text-primary-600 dark:text-primary-400" :
              confidence >= 0.6 ? "text-yellow-600 dark:text-yellow-400" :
              "text-orange-600 dark:text-orange-400"
            )} />
            <div className="flex-1 min-w-0">
              <span className={cn(
                "font-semibold text-xs sm:text-sm block",
                confidence >= 0.7 ? "text-primary-700 dark:text-primary-300" :
                confidence >= 0.6 ? "text-yellow-700 dark:text-yellow-300" :
                "text-orange-700 dark:text-orange-300"
              )}>
                <span className="hidden sm:inline">{betLabel}</span>
                <span className="sm:hidden">{shortBetLabel}</span>
              </span>
            </div>
            <div className="flex-shrink-0 text-right">
              <span className="text-[10px] sm:text-xs font-bold text-primary-600 dark:text-primary-400">
                {confidence >= 0.75 && "🔥"}
                {confidence >= 0.65 && confidence < 0.75 && "⚡"}
                {confidence < 0.65 && "📊"}
              </span>
            </div>
          </div>

          {/* Explanation */}
          {prediction.explanation && (
            <p className="text-gray-700 dark:text-slate-300 text-[11px] sm:text-sm leading-relaxed line-clamp-2 sm:line-clamp-none">
              {prediction.explanation}
            </p>
          )}

          {/* Value Score & Pick Score Indicators */}
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center justify-between p-2 sm:p-3 rounded-lg bg-gray-200 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-700">
              <div className="flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-cyan-700 dark:text-cyan-400 flex-shrink-0" />
                <span className="text-xs sm:text-sm text-gray-700 dark:text-slate-300">Value</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-xs sm:text-sm font-bold text-cyan-700 dark:text-cyan-400">
                  {formatValue(valueScore)}
                </span>
                <span className={cn(
                  "text-xs font-medium px-1.5 py-0.5 rounded-full",
                  valueTier.bgClass,
                  valueTier.textClass
                )}>
                  {valueTier.label}
                </span>
                {isValueBet(valueScore) && (
                  <ValueBetIndicator valueScore={valueScore} />
                )}
              </div>
            </div>

            {/* Pick Score */}
            {pick.pick_score !== undefined && (
              <div className="flex items-center justify-between p-2 sm:p-3 rounded-lg bg-gray-200 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-700">
                <div className="flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                  <span className="text-xs sm:text-sm text-gray-700 dark:text-slate-300">Score</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-xs sm:text-sm font-bold text-amber-600 dark:text-amber-400">
                    {pick.pick_score.toFixed(2)}
                  </span>
                  <span className={cn(
                    "text-xs font-medium px-1.5 py-0.5 rounded-full",
                    pick.pick_score >= 0.8 ? "bg-amber-200 dark:bg-amber-500/30 text-amber-700 dark:text-amber-300" :
                    pick.pick_score >= 0.6 ? "bg-yellow-200 dark:bg-yellow-500/30 text-yellow-700 dark:text-yellow-300" :
                    "bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-slate-300"
                  )}>
                    {pick.pick_score >= 0.8 ? "Top" : pick.pick_score >= 0.6 ? "Bon" : "Moyen"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Key Factors */}
          {prediction.key_factors && prediction.key_factors.length > 0 && (
            <div>
              <p className="text-[10px] sm:text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 sm:mb-2 flex items-center gap-1">
                <span>✓ Points positifs</span>
              </p>
              <div className="flex flex-wrap gap-1 sm:gap-2">
                {prediction.key_factors.slice(0, 4).map((factor, i) => (
                  <span
                    key={i}
                    className="px-1.5 sm:px-2 py-0.5 sm:py-1 bg-primary-100 dark:bg-primary-500/20 border border-primary-300 dark:border-primary-500/40 rounded text-[10px] sm:text-xs text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-500/30 transition-smooth"
                  >
                    +{factor}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Risk Factors */}
          {prediction.risk_factors && prediction.risk_factors.length > 0 && (
            <div>
              <p className="text-[10px] sm:text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 sm:mb-2 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                <span>Risques à surveiller</span>
              </p>
              <div className="flex flex-wrap gap-1 sm:gap-2">
                {prediction.risk_factors.slice(0, 3).map((factor, i) => (
                  <span
                    key={i}
                    className="px-1.5 sm:px-2 py-0.5 sm:py-1 bg-orange-100 dark:bg-orange-500/20 border border-orange-300 dark:border-orange-500/40 rounded text-[10px] sm:text-xs text-orange-700 dark:text-orange-300 hover:bg-orange-200 dark:hover:bg-orange-500/30 transition-smooth"
                  >
                    ⚠ {factor}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* RAG Context - News, Injuries, Sentiment */}
          <div className="border-t border-gray-200 dark:border-slate-700/50 pt-3">
            <RAGContext
              homeTeam={prediction.home_team}
              awayTeam={prediction.away_team}
              competition={(prediction as { competition?: string }).competition || "PL"}
              matchDate={matchDate}
            />
          </div>
        </div>

        {/* Footer with confidence tier info */}
        <div className={cn(
          "px-3 sm:px-6 py-2 sm:py-3 border-t border-slate-200 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-800/50 text-[10px] sm:text-xs",
          "flex items-center justify-between"
        )}>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-600 dark:text-slate-400">Confiance:</span>
            <span className={cn(
              "font-bold px-1.5 py-0.5 rounded-full",
              confidenceTier.bgClass,
              confidenceTier.textClass
            )}>
              {confidenceTier.label}
            </span>
          </div>
          <div className="text-slate-600 dark:text-slate-500">
            Pick #{pick.rank}
          </div>
        </div>
      </div>
    </div>
    </Link>
  );
}

function ProbBarEnhanced({
  label,
  prob,
  isRecommended,
}: {
  label: string;
  prob: number;
  isRecommended?: boolean;
}) {
  const getShortLabel = (name: string) => {
    if (name === "Nul") return name;
    if (name.length <= 8) return name;
    const firstWord = name.split(" ")[0];
    if (firstWord.length <= 8) return firstWord;
    return name.slice(0, 7) + "…";
  };

  return (
    <div className="flex-1 min-w-0">
      <div className="flex justify-between text-[10px] sm:text-xs mb-1 gap-1">
        <span className={cn(
          "truncate font-medium",
          isRecommended ? "text-primary-700 dark:text-primary-400" : "text-slate-600 dark:text-slate-400"
        )}>
          <span className="hidden sm:inline">{label.length > 12 ? label.slice(0, 12) + "…" : label}</span>
          <span className="sm:hidden">{getShortLabel(label)}</span>
        </span>
        <span className={cn(
          "flex-shrink-0 font-bold",
          isRecommended ? "text-primary-700 dark:text-primary-400" : "text-slate-600 dark:text-slate-400"
        )}>
          {Math.round(prob * 100)}%
        </span>
      </div>
      <div className="h-1.5 sm:h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            isRecommended ? "bg-gradient-to-r from-primary-500 to-emerald-500" : "bg-slate-300 dark:bg-slate-600"
          )}
          style={{ width: `${prob * 100}%` }}
        />
      </div>
    </div>
  );
}
