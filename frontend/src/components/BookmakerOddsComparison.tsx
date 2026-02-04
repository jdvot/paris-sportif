"use client";

import { useMemo } from "react";
import { TrendingUp, Trophy, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

// Bookmaker configuration with display names and colors
const BOOKMAKERS: Record<string, { name: string; color: string; logo?: string }> = {
  bet365: { name: "Bet365", color: "bg-green-600" },
  unibet: { name: "Unibet", color: "bg-emerald-500" },
  winamax: { name: "Winamax", color: "bg-red-600" },
  betclic: { name: "Betclic", color: "bg-orange-500" },
  pinnacle: { name: "Pinnacle", color: "bg-blue-600" },
  bwin: { name: "Bwin", color: "bg-yellow-500" },
  williamhill: { name: "William Hill", color: "bg-blue-800" },
  betfair: { name: "Betfair", color: "bg-amber-500" },
  ladbrokes: { name: "Ladbrokes", color: "bg-red-700" },
  pokerstars: { name: "PokerStars", color: "bg-red-600" },
  // Default fallback
  default: { name: "Bookmaker", color: "bg-gray-600" },
};

export interface BookmakerOdds {
  bookmaker: string;
  home: number;
  draw: number;
  away: number;
  lastUpdate?: string;
}

export interface OddsComparisonProps {
  matchId?: number;
  odds: BookmakerOdds[];
  prediction?: {
    home: number;
    draw: number;
    away: number;
  };
  homeTeam: string;
  awayTeam: string;
}

/**
 * Get bookmaker info with fallback for unknown bookmakers
 */
function getBookmakerInfo(bookmakerKey: string) {
  const normalizedKey = bookmakerKey.toLowerCase().replace(/\s+/g, "");
  return BOOKMAKERS[normalizedKey] || { ...BOOKMAKERS.default, name: bookmakerKey };
}

/**
 * Calculate value percentage between prediction probability and bookmaker odds
 * Value = (odds * probability - 1) * 100
 */
function calculateValue(odds: number, probability: number): number {
  if (odds <= 0 || probability <= 0) return 0;
  return (odds * probability - 1) * 100;
}

/**
 * Check if odds represent a value bet (positive expected value)
 */
function isValueBet(odds: number, probability: number, threshold: number = 5): boolean {
  return calculateValue(odds, probability) >= threshold;
}

/**
 * Main BookmakerOddsComparison Component
 * Displays odds from multiple bookmakers in a responsive table with best odds highlighting
 */
export function BookmakerOddsComparison({
  odds,
  prediction,
  homeTeam,
  awayTeam,
}: OddsComparisonProps) {
  const t = useTranslations("bookmakerOdds");

  // Calculate best odds for each outcome
  const bestOdds = useMemo(() => {
    if (!odds || odds.length === 0) return { home: 0, draw: 0, away: 0 };

    return {
      home: Math.max(...odds.map((o) => o.home || 0)),
      draw: Math.max(...odds.map((o) => o.draw || 0)),
      away: Math.max(...odds.map((o) => o.away || 0)),
    };
  }, [odds]);

  // Calculate value for best odds if prediction is available
  const valueIndicators = useMemo(() => {
    if (!prediction) return null;

    return {
      home: {
        value: calculateValue(bestOdds.home, prediction.home),
        isValue: isValueBet(bestOdds.home, prediction.home),
      },
      draw: {
        value: calculateValue(bestOdds.draw, prediction.draw),
        isValue: isValueBet(bestOdds.draw, prediction.draw),
      },
      away: {
        value: calculateValue(bestOdds.away, prediction.away),
        isValue: isValueBet(bestOdds.away, prediction.away),
      },
    };
  }, [bestOdds, prediction]);

  if (!odds || odds.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            {t("title")}
          </h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400">
          {t("noOddsAvailable")}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 sm:p-6 border-b border-gray-200 dark:border-slate-700">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary-400" />
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              {t("title")}
            </h3>
          </div>
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {odds.length} {t("bookmakers")}
          </span>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          {t("description")}
        </p>
      </div>

      {/* Best Odds Summary */}
      <div className="p-4 sm:p-6 bg-gradient-to-r from-primary-50 to-accent-50 dark:from-primary-500/10 dark:to-accent-500/10 border-b border-gray-200 dark:border-slate-700">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-4 h-4 text-yellow-500" />
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t("bestOdds")}
          </h4>
        </div>

        <div className="grid grid-cols-3 gap-3">
          {/* Best Home Odds */}
          <BestOddsCard
            label={homeTeam}
            odds={bestOdds.home}
            valueInfo={valueIndicators?.home}
            color="primary"
          />

          {/* Best Draw Odds */}
          <BestOddsCard
            label={t("draw")}
            odds={bestOdds.draw}
            valueInfo={valueIndicators?.draw}
            color="gray"
          />

          {/* Best Away Odds */}
          <BestOddsCard
            label={awayTeam}
            odds={bestOdds.away}
            valueInfo={valueIndicators?.away}
            color="accent"
          />
        </div>
      </div>

      {/* Odds Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 dark:bg-slate-700/50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                {t("bookmaker")}
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wider">
                1
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                X
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-accent-600 dark:text-accent-400 uppercase tracking-wider">
                2
              </th>
              {odds[0]?.lastUpdate && (
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                  <Clock className="w-3 h-3 inline-block mr-1" />
                  {t("updated")}
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
            {odds.map((oddsRow, index) => (
              <OddsTableRow
                key={`${oddsRow.bookmaker}-${index}`}
                odds={oddsRow}
                bestOdds={bestOdds}
                prediction={prediction}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer with legend */}
      <div className="p-4 sm:p-6 bg-gray-50 dark:bg-slate-700/30 border-t border-gray-200 dark:border-slate-700">
        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 dark:text-slate-400">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-primary-500/20 border-2 border-primary-500" />
            <span>{t("legend.bestOdds")}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-emerald-500/20 border border-emerald-500" />
            <span>{t("legend.valueBet")}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Best Odds Card Component
 */
function BestOddsCard({
  label,
  odds,
  valueInfo,
  color,
}: {
  label: string;
  odds: number;
  valueInfo?: { value: number; isValue: boolean };
  color: "primary" | "gray" | "accent";
}) {
  const colorClasses = {
    primary: {
      bg: "bg-primary-100 dark:bg-primary-500/20",
      border: "border-primary-300 dark:border-primary-500/40",
      text: "text-primary-700 dark:text-primary-300",
      oddsText: "text-primary-600 dark:text-primary-400",
    },
    gray: {
      bg: "bg-gray-100 dark:bg-gray-500/20",
      border: "border-gray-300 dark:border-gray-500/40",
      text: "text-gray-700 dark:text-gray-300",
      oddsText: "text-gray-600 dark:text-gray-400",
    },
    accent: {
      bg: "bg-accent-100 dark:bg-accent-500/20",
      border: "border-accent-300 dark:border-accent-500/40",
      text: "text-accent-700 dark:text-accent-300",
      oddsText: "text-accent-600 dark:text-accent-400",
    },
  };

  const classes = colorClasses[color];

  return (
    <div
      className={cn(
        "relative rounded-lg p-3 text-center border",
        classes.bg,
        classes.border
      )}
    >
      <p className={cn("text-xs font-medium mb-1 truncate", classes.text)}>
        {label}
      </p>
      <p className={cn("text-xl font-bold", classes.oddsText)}>
        {odds > 0 ? odds.toFixed(2) : "-"}
      </p>
      {valueInfo?.isValue && (
        <div className="mt-1">
          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold rounded-full">
            +{valueInfo.value.toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Odds Table Row Component
 */
function OddsTableRow({
  odds,
  bestOdds,
  prediction,
}: {
  odds: BookmakerOdds;
  bestOdds: { home: number; draw: number; away: number };
  prediction?: { home: number; draw: number; away: number };
}) {
  const bookmakerInfo = getBookmakerInfo(odds.bookmaker);

  const isBestHome = odds.home === bestOdds.home && odds.home > 0;
  const isBestDraw = odds.draw === bestOdds.draw && odds.draw > 0;
  const isBestAway = odds.away === bestOdds.away && odds.away > 0;

  const homeValue = prediction ? calculateValue(odds.home, prediction.home) : 0;
  const drawValue = prediction ? calculateValue(odds.draw, prediction.draw) : 0;
  const awayValue = prediction ? calculateValue(odds.away, prediction.away) : 0;

  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors">
      {/* Bookmaker */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "w-6 h-6 rounded flex items-center justify-center text-white text-[10px] font-bold",
              bookmakerInfo.color
            )}
          >
            {bookmakerInfo.name.charAt(0)}
          </div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {bookmakerInfo.name}
          </span>
        </div>
      </td>

      {/* Home Odds */}
      <td className="px-4 py-3 text-center">
        <OddsCell
          value={odds.home}
          isBest={isBestHome}
          valuePercent={homeValue}
          color="primary"
        />
      </td>

      {/* Draw Odds */}
      <td className="px-4 py-3 text-center">
        <OddsCell
          value={odds.draw}
          isBest={isBestDraw}
          valuePercent={drawValue}
          color="gray"
        />
      </td>

      {/* Away Odds */}
      <td className="px-4 py-3 text-center">
        <OddsCell
          value={odds.away}
          isBest={isBestAway}
          valuePercent={awayValue}
          color="accent"
        />
      </td>

      {/* Last Update */}
      {odds.lastUpdate && (
        <td className="px-4 py-3 text-right">
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {odds.lastUpdate}
          </span>
        </td>
      )}
    </tr>
  );
}

/**
 * Individual Odds Cell Component
 */
function OddsCell({
  value,
  isBest,
  valuePercent,
  color,
}: {
  value: number;
  isBest: boolean;
  valuePercent: number;
  color: "primary" | "gray" | "accent";
}) {
  const isValue = valuePercent >= 5;

  const bestClasses = {
    primary: "bg-primary-100 dark:bg-primary-500/20 border-primary-500",
    gray: "bg-gray-100 dark:bg-gray-500/20 border-gray-400",
    accent: "bg-accent-100 dark:bg-accent-500/20 border-accent-500",
  };

  const textClasses = {
    primary: "text-primary-700 dark:text-primary-300",
    gray: "text-gray-700 dark:text-gray-400",
    accent: "text-accent-700 dark:text-accent-300",
  };

  if (value <= 0) {
    return <span className="text-gray-400 dark:text-slate-500">-</span>;
  }

  return (
    <div className="flex flex-col items-center gap-0.5">
      <span
        className={cn(
          "inline-flex items-center justify-center px-2 py-1 rounded font-bold text-sm min-w-[3.5rem] transition-all",
          isBest
            ? cn("border-2", bestClasses[color], textClasses[color])
            : "text-gray-900 dark:text-white"
        )}
      >
        {value.toFixed(2)}
      </span>
      {isValue && (
        <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
          +{valuePercent.toFixed(0)}%
        </span>
      )}
    </div>
  );
}

/**
 * Compact version of the odds comparison for use in cards/lists
 */
export function BookmakerOddsCompact({
  odds,
  homeTeam: _homeTeam,
  awayTeam: _awayTeam,
}: {
  odds: BookmakerOdds[];
  homeTeam: string;
  awayTeam: string;
}) {
  const t = useTranslations("bookmakerOdds");

  const bestOdds = useMemo(() => {
    if (!odds || odds.length === 0) return null;
    return {
      home: Math.max(...odds.map((o) => o.home || 0)),
      draw: Math.max(...odds.map((o) => o.draw || 0)),
      away: Math.max(...odds.map((o) => o.away || 0)),
    };
  }, [odds]);

  if (!bestOdds) return null;

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-500 dark:text-slate-400">{t("bestOdds")}:</span>
      <div className="flex items-center gap-1.5">
        <span className="px-1.5 py-0.5 bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300 rounded font-semibold">
          {bestOdds.home.toFixed(2)}
        </span>
        <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-500/20 text-gray-700 dark:text-gray-300 rounded font-semibold">
          {bestOdds.draw.toFixed(2)}
        </span>
        <span className="px-1.5 py-0.5 bg-accent-100 dark:bg-accent-500/20 text-accent-700 dark:text-accent-300 rounded font-semibold">
          {bestOdds.away.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

export default BookmakerOddsComparison;
