"use client";

import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  confidence: number;
  valueScore?: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  animated?: boolean;
}

export function ConfidenceBadge({
  confidence,
  valueScore = 0,
  size = "md",
  showLabel = true,
  animated = true,
}: ConfidenceBadgeProps) {
  const confidencePercent = Math.round(confidence * 100);

  // Determine tier
  let tier = "Bas";
  let tierColor = "from-orange-500 to-red-500";
  let tierBg = "bg-orange-500/20";
  let tierBorder = "border-orange-500/50";
  let icon = "📊";

  if (confidence >= 0.75) {
    tier = "Très Haut";
    tierColor = "from-primary-500 to-emerald-500";
    tierBg = "bg-primary-500/20";
    tierBorder = "border-primary-500/50";
    icon = "🔥";
  } else if (confidence >= 0.65) {
    tier = "Haut";
    tierColor = "from-primary-400 to-blue-400";
    tierBg = "bg-blue-500/20";
    tierBorder = "border-blue-500/50";
    icon = "⚡";
  } else if (confidence >= 0.55) {
    tier = "Moyen";
    tierColor = "from-yellow-400 to-orange-400";
    tierBg = "bg-yellow-500/20";
    tierBorder = "border-yellow-500/50";
    icon = "⚠️";
  }

  // Circular progress
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (confidencePercent / 100) * circumference;

  if (size === "sm") {
    return (
      <div className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded-full border",
        tierBg,
        tierBorder
      )}>
        <span className="text-xs font-bold">{icon}</span>
        <span className="text-xs font-bold">{confidencePercent}%</span>
      </div>
    );
  }

  if (size === "lg") {
    return (
      <div className="space-y-3">
        {/* Circular Progress */}
        <div className="flex flex-col items-center gap-3">
          <div className="relative w-32 h-32">
            <svg className="w-full h-full -rotate-90">
              {/* Background circle */}
              <circle
                cx="64"
                cy="64"
                r="45"
                fill="none"
                stroke="rgb(53, 63, 85)"
                strokeWidth="8"
              />

              {/* Progress circle */}
              <circle
                cx="64"
                cy="64"
                r="45"
                fill="none"
                stroke={confidence >= 0.75 ? "rgb(34, 197, 94)" : confidence >= 0.65 ? "rgb(96, 165, 250)" : "rgb(250, 204, 21)"}
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className={cn(
                  "transition-all duration-700",
                  animated && "ease-out"
                )}
              />
            </svg>

            {/* Center content */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl">{icon}</span>
              <div className="text-center">
                <p className="text-3xl font-bold text-white">{confidencePercent}%</p>
                <p className="text-xs text-dark-400 mt-1">{tier}</p>
              </div>
            </div>
          </div>

          {/* Value Score */}
          {valueScore > 0 && (
            <div className="w-full text-center p-3 bg-dark-700/30 border border-dark-600/50 rounded-lg">
              <p className="text-xs text-dark-400">Value Score</p>
              <p className="text-lg font-bold text-accent-400">+{Math.round(valueScore * 100)}%</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Default: md size
  return (
    <div className={cn(
      "flex items-center gap-3 p-4 rounded-xl border-2 transition-smooth",
      "bg-gradient-to-br",
      tierBg,
      tierBorder
    )}>
      {/* Icon and percentage */}
      <div className="flex-shrink-0">
        <div className="flex flex-col items-center gap-1">
          <span className="text-3xl">{icon}</span>
          <span className="text-2xl font-bold text-white">{confidencePercent}%</span>
        </div>
      </div>

      {/* Text info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-dark-400">Confiance</p>
        <p className="text-base font-bold text-white">{tier}</p>
        {valueScore > 0 && (
          <p className="text-xs text-accent-300 mt-1">
            Value: +{Math.round(valueScore * 100)}%
          </p>
        )}
      </div>

      {/* Indicator bar */}
      <div className="flex-shrink-0">
        <div className="w-1 h-16 rounded-full bg-dark-700 overflow-hidden">
          <div
            className={cn(
              "h-full w-full bg-gradient-to-t transition-all duration-700",
              tierColor
            )}
            style={{ height: `${confidencePercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}
