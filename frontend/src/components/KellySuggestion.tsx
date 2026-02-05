"use client";

import { useState } from "react";
import { Calculator, TrendingUp, Info } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useGetKellySuggestionApiV1BetsKellyGet } from "@/lib/api/endpoints/bets-bankroll/bets-bankroll";
import type { KellySuggestion as KellySuggestionType } from "@/lib/api/models";

interface KellySuggestionProps {
  odds: number;
  confidence: number; // 0-1 range
  recommendedBet?: string; // Optional, for future use
  className?: string;
}

export function KellySuggestion({
  odds,
  confidence,
  recommendedBet: _recommendedBet,
  className,
}: KellySuggestionProps) {
  const t = useTranslations("odds.kelly");
  const [showDetails, setShowDetails] = useState(false);

  // Convert confidence from 0-1 to 0-100 for API
  const confidencePercent = Math.round(confidence * 100);

  const { data: kellyResponse, isLoading } = useGetKellySuggestionApiV1BetsKellyGet(
    { odds, confidence: confidencePercent },
    { query: { enabled: odds > 1.01 && confidencePercent > 0 } }
  );

  const kelly = kellyResponse?.data as KellySuggestionType | undefined;

  // Don't render if no valid odds
  if (!odds || odds <= 1.01) {
    return null;
  }

  // Calculate Expected Value
  const ev = (odds * confidence) - 1;
  const evPercent = ev * 100;
  const hasPositiveEV = ev > 0;

  return (
    <div
      className={cn(
        "border rounded-xl p-4 transition-all",
        hasPositiveEV
          ? "bg-gradient-to-br from-emerald-50 to-primary-50 dark:from-emerald-500/10 dark:to-primary-500/10 border-emerald-200 dark:border-emerald-500/30"
          : "bg-gray-50 dark:bg-dark-800/50 border-gray-200 dark:border-dark-700",
        className
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Calculator className="w-4 h-4 text-primary-500" />
          {t("title")}
        </h4>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-xs text-primary-500 hover:text-primary-600 transition-colors"
        >
          {showDetails ? "−" : "+"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Expected Value */}
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-dark-400 mb-1">EV</p>
          <p
            className={cn(
              "text-lg font-bold",
              hasPositiveEV
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400"
            )}
          >
            {hasPositiveEV ? "+" : ""}
            {evPercent.toFixed(1)}%
          </p>
        </div>

        {/* Kelly Stake */}
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-dark-400 mb-1">{t("optimalStake")}</p>
          {isLoading ? (
            <div className="h-7 w-16 bg-gray-200 dark:bg-dark-600 rounded animate-pulse mx-auto" />
          ) : kelly ? (
            <p className="text-lg font-bold text-primary-600 dark:text-primary-400">
              {kelly.suggested_stake_pct.toFixed(1)}%
            </p>
          ) : (
            <p className="text-lg font-bold text-gray-400">-</p>
          )}
        </div>
      </div>

      {showDetails && kelly && (
        <div className="mt-4 pt-3 border-t border-gray-200 dark:border-dark-700 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-dark-400">{t("edge")}</span>
            <span
              className={cn(
                "font-medium",
                kelly.edge > 0
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-red-600 dark:text-red-400"
              )}
            >
              {kelly.edge > 0 ? "+" : ""}
              {(kelly.edge * 100).toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-dark-400">{t("fraction")}</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {(kelly.kelly_fraction * 100).toFixed(2)}%
            </span>
          </div>
          {kelly.bankroll > 0 && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-dark-400">Mise suggérée</span>
              <span className="font-bold text-primary-600 dark:text-primary-400">
                {kelly.suggested_stake.toFixed(2)}€
              </span>
            </div>
          )}
        </div>
      )}

      {/* Info note */}
      {hasPositiveEV && (
        <div className="mt-3 flex items-start gap-2 text-xs text-emerald-600 dark:text-emerald-400">
          <TrendingUp className="w-3 h-3 flex-shrink-0 mt-0.5" />
          <span>Espérance positive détectée. Pari recommandé selon Kelly.</span>
        </div>
      )}
      {!hasPositiveEV && (
        <div className="mt-3 flex items-start gap-2 text-xs text-gray-500 dark:text-dark-400">
          <Info className="w-3 h-3 flex-shrink-0 mt-0.5" />
          <span>Espérance négative. Mise déconseillée.</span>
        </div>
      )}
    </div>
  );
}

/**
 * Simplified EV display for prediction cards
 */
export function EVIndicator({
  odds,
  confidence,
  compact = false,
}: {
  odds: number;
  confidence: number;
  compact?: boolean;
}) {
  if (!odds || odds <= 1.01) return null;

  const ev = (odds * confidence) - 1;
  const evPercent = ev * 100;
  const hasPositiveEV = ev > 0;

  if (compact) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
          hasPositiveEV
            ? "bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300"
            : "bg-gray-100 dark:bg-dark-700 text-gray-600 dark:text-dark-400"
        )}
      >
        EV: {hasPositiveEV ? "+" : ""}
        {evPercent.toFixed(0)}%
      </span>
    );
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg",
        hasPositiveEV
          ? "bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30"
          : "bg-gray-50 dark:bg-dark-800 border border-gray-200 dark:border-dark-700"
      )}
    >
      <Calculator className="w-4 h-4 text-gray-500" />
      <div>
        <p className="text-xs text-gray-500 dark:text-dark-400">Expected Value</p>
        <p
          className={cn(
            "font-bold",
            hasPositiveEV
              ? "text-emerald-600 dark:text-emerald-400"
              : "text-gray-600 dark:text-dark-400"
          )}
        >
          {hasPositiveEV ? "+" : ""}
          {evPercent.toFixed(1)}%
        </p>
      </div>
    </div>
  );
}
