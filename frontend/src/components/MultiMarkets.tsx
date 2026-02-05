"use client";

import { TrendingUp, Target, Users, Percent } from "lucide-react";
import { cn } from "@/lib/utils";

interface MarketOdds {
  over?: number;
  under?: number;
  yes?: number;
  no?: number;
  home?: number;
  draw?: number;
  away?: number;
}

interface MultiMarketsProps {
  homeTeam: string;
  awayTeam: string;
  // Over/Under 2.5
  overUnder25?: { prob: number; odds: MarketOdds };
  // BTTS (Both Teams To Score)
  btts?: { prob: number; odds: MarketOdds };
  // Double Chance
  doubleChance?: {
    homeOrDraw: { prob: number; odds?: number };
    awayOrDraw: { prob: number; odds?: number };
    homeOrAway: { prob: number; odds?: number };
  };
  // Over/Under 1.5
  overUnder15?: { prob: number; odds: MarketOdds };
  className?: string;
}

export function MultiMarkets({
  homeTeam: _homeTeam,
  awayTeam: _awayTeam,
  overUnder25,
  btts,
  doubleChance,
  overUnder15,
  className,
}: MultiMarketsProps) {
  const markets = [
    overUnder25 && {
      id: "ou25",
      label: "Plus/Moins 2.5 Buts",
      icon: Target,
      options: [
        { label: "+2.5", prob: overUnder25.prob, odds: overUnder25.odds.over, recommended: overUnder25.prob > 0.5 },
        { label: "-2.5", prob: 1 - overUnder25.prob, odds: overUnder25.odds.under, recommended: overUnder25.prob <= 0.5 },
      ],
    },
    overUnder15 && {
      id: "ou15",
      label: "Plus/Moins 1.5 Buts",
      icon: Target,
      options: [
        { label: "+1.5", prob: overUnder15.prob, odds: overUnder15.odds.over, recommended: overUnder15.prob > 0.5 },
        { label: "-1.5", prob: 1 - overUnder15.prob, odds: overUnder15.odds.under, recommended: overUnder15.prob <= 0.5 },
      ],
    },
    btts && {
      id: "btts",
      label: "Les 2 Equipes Marquent",
      icon: Users,
      options: [
        { label: "Oui", prob: btts.prob, odds: btts.odds.yes, recommended: btts.prob > 0.5 },
        { label: "Non", prob: 1 - btts.prob, odds: btts.odds.no, recommended: btts.prob <= 0.5 },
      ],
    },
    doubleChance && {
      id: "dc",
      label: "Double Chance",
      icon: Percent,
      options: [
        { label: `1X`, prob: doubleChance.homeOrDraw.prob, odds: doubleChance.homeOrDraw.odds, recommended: doubleChance.homeOrDraw.prob >= Math.max(doubleChance.awayOrDraw.prob, doubleChance.homeOrAway.prob) },
        { label: `X2`, prob: doubleChance.awayOrDraw.prob, odds: doubleChance.awayOrDraw.odds, recommended: doubleChance.awayOrDraw.prob >= Math.max(doubleChance.homeOrDraw.prob, doubleChance.homeOrAway.prob) },
        { label: `12`, prob: doubleChance.homeOrAway.prob, odds: doubleChance.homeOrAway.odds, recommended: doubleChance.homeOrAway.prob >= Math.max(doubleChance.homeOrDraw.prob, doubleChance.awayOrDraw.prob) },
      ],
    },
  ].filter(Boolean) as Array<{
    id: string;
    label: string;
    icon: typeof Target;
    options: Array<{ label: string; prob: number; odds?: number; recommended: boolean }>;
  }>;

  if (markets.length === 0) {
    return null;
  }

  return (
    <div className={cn("space-y-3", className)}>
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-primary-500" />
        Autres Marches
      </h4>

      <div className="grid gap-3">
        {markets.map((market) => {
          const Icon = market.icon;
          return (
            <div
              key={market.id}
              className="bg-gray-50 dark:bg-dark-700/40 border border-gray-200 dark:border-dark-600/50 rounded-lg p-3 overflow-visible"
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4 text-gray-500 dark:text-dark-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-dark-300">
                  {market.label}
                </span>
              </div>

              <div className="grid gap-2 pt-4 overflow-visible" style={{ gridTemplateColumns: `repeat(${market.options.length}, 1fr)` }}>
                {market.options.map((option) => (
                  <div
                    key={option.label}
                    className={cn(
                      "relative p-2 rounded-lg border text-center transition-all overflow-visible",
                      option.recommended
                        ? "bg-primary-50 dark:bg-primary-500/10 border-primary-300 dark:border-primary-500/40"
                        : "bg-white dark:bg-dark-800/50 border-gray-200 dark:border-dark-600"
                    )}
                  >
                    {option.recommended && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-20">
                        <span className="px-2 py-0.5 bg-primary-500 text-white text-[9px] font-bold rounded-full whitespace-nowrap shadow-sm">
                          REC
                        </span>
                      </div>
                    )}
                    <p className={cn(
                      "text-xs font-semibold mb-1",
                      option.recommended
                        ? "text-primary-700 dark:text-primary-300"
                        : "text-gray-700 dark:text-dark-300"
                    )}>
                      {option.label}
                    </p>
                    <p className={cn(
                      "text-lg font-bold",
                      option.recommended
                        ? "text-primary-600 dark:text-primary-400"
                        : "text-gray-900 dark:text-white"
                    )}>
                      {Math.round(option.prob * 100)}%
                    </p>
                    {option.odds && (
                      <p className="text-[10px] text-gray-500 dark:text-dark-400">
                        @{option.odds.toFixed(2)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// NOTE: Simulated data generator removed - multi-market data should come from backend API
