"use client";

import { TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface OddsDisplayProps {
  probability: number;
  outcome: "home" | "draw" | "away";
  label: string;
  compact?: boolean;
}

/**
 * Calculate fair odds from probability
 */
function calculateFairOdds(probability: number): number {
  if (probability <= 0) return Infinity;
  return 1 / probability;
}

/**
 * Small OddsDisplay Component
 * Shows predicted probability, fair odds, and value indicator
 * Designed for match detail pages
 */
export function OddsDisplay({
  probability,
  outcome,
  label,
  compact = false,
}: OddsDisplayProps) {
  const fairOdds = calculateFairOdds(probability);

  const colorMap = {
    home: {
      bg: "bg-primary-500/10",
      border: "border-primary-500/30",
      text: "text-primary-400",
      darkText: "text-primary-300",
      bar: "bg-primary-500",
      icon: "text-primary-400",
    },
    draw: {
      bg: "bg-yellow-500/10",
      border: "border-yellow-500/30",
      text: "text-yellow-400",
      darkText: "text-yellow-300",
      bar: "bg-yellow-500",
      icon: "text-yellow-400",
    },
    away: {
      bg: "bg-accent-500/10",
      border: "border-accent-500/30",
      text: "text-accent-400",
      darkText: "text-accent-300",
      bar: "bg-accent-500",
      icon: "text-accent-400",
    },
  };

  const colors = colorMap[outcome];

  if (compact) {
    // Minimal inline display
    return (
      <div className={cn("rounded-lg border p-3", colors.bg, colors.border)}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <TrendingUp className={cn("w-4 h-4 flex-shrink-0", colors.icon)} />
            <span className="text-sm font-semibold text-white truncate">{label}</span>
          </div>
          <div className="text-right flex-shrink-0">
            <p className={cn("font-bold", colors.text)}>
              {Math.round(probability * 100)}%
            </p>
            <p className="text-xs text-dark-400">
              {fairOdds === Infinity ? "∞" : fairOdds.toFixed(2)}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Full display
  return (
    <div className={cn("rounded-lg border p-4", colors.bg, colors.border, "space-y-3")}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <TrendingUp className={cn("w-5 h-5 flex-shrink-0", colors.icon)} />
        <h4 className={cn("font-semibold text-white truncate")}>{label}</h4>
      </div>

      {/* Probability */}
      <div>
        <p className="text-xs text-dark-400 mb-1">Probabilite Predite</p>
        <div className="flex items-center justify-between">
          <p className={cn("text-2xl font-bold", colors.text)}>
            {Math.round(probability * 100)}%
          </p>
          <div className={cn("h-12 w-12 rounded-lg flex items-center justify-center", colors.bg, colors.border, "border")}>
            <span className={cn("font-bold text-sm", colors.text)}>
              {Math.round(probability * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Probability Bar */}
      <div>
        <div className={cn("h-3 rounded-full overflow-hidden bg-dark-700")}>
          <div
            className={cn("h-full rounded-full transition-all", colors.bar)}
            style={{ width: `${Math.min(probability * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Fair Odds */}
      <div className="bg-dark-800/50 rounded p-3">
        <p className="text-xs text-dark-400 mb-1">Cote Juste (Fair Odds)</p>
        <p className={cn("text-xl font-bold", colors.text)}>
          {fairOdds === Infinity ? "∞" : fairOdds.toFixed(2)}
        </p>
        <p className="text-xs text-dark-500 mt-1">
          Cette cote reflete exactement votre probabilite
        </p>
      </div>

      {/* Information */}
      <div className="bg-dark-900/30 rounded p-3">
        <p className="text-xs text-dark-400">
          <span className="font-semibold text-dark-300">Conseil:</span> Comparez avec les cotes des bookmakers. Si elles sont superieures,
          c'est une opportunite value.
        </p>
      </div>
    </div>
  );
}

/**
 * Compact OddsDisplay for inline use in tables or lists
 */
export function OddsDisplayInline({
  probability,
  outcome,
}: {
  probability: number;
  outcome: "home" | "draw" | "away";
}) {
  const fairOdds = calculateFairOdds(probability);

  const colorMap = {
    home: "text-primary-400",
    draw: "text-yellow-400",
    away: "text-accent-400",
  };

  const color = colorMap[outcome];

  return (
    <div className="flex items-center gap-1">
      <span className={cn("font-semibold", color)}>
        {Math.round(probability * 100)}%
      </span>
      <span className="text-xs text-dark-500">
        ({fairOdds === Infinity ? "∞" : fairOdds.toFixed(2)})
      </span>
    </div>
  );
}
