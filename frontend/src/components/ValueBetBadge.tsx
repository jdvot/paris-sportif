"use client";

import { TrendingUp, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { isValueBet, getValueTier, formatValue } from "@/lib/constants";

interface ValueBetBadgeProps {
  valueScore: number;
  showTier?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "compact" | "detailed";
  className?: string;
}

export function ValueBetBadge({
  valueScore,
  showTier = true,
  size = "md",
  variant = "default",
  className,
}: ValueBetBadgeProps) {
  const isValue = isValueBet(valueScore);
  const tier = getValueTier(valueScore);

  if (!isValue && variant !== "detailed") {
    return null;
  }

  const sizeClasses = {
    sm: "text-[10px] px-1.5 py-0.5 gap-1",
    md: "text-xs px-2 py-1 gap-1.5",
    lg: "text-sm px-3 py-1.5 gap-2",
  };

  const iconSizes = {
    sm: "w-3 h-3",
    md: "w-3.5 h-3.5",
    lg: "w-4 h-4",
  };

  if (variant === "compact") {
    return (
      <span
        className={cn(
          "inline-flex items-center font-bold rounded-full",
          sizeClasses[size],
          tier.bgClass,
          tier.textClass,
          className
        )}
      >
        <TrendingUp className={iconSizes[size]} />
        {formatValue(valueScore)}
      </span>
    );
  }

  if (variant === "detailed") {
    return (
      <div
        className={cn(
          "flex items-center justify-between p-2 sm:p-3 rounded-lg border",
          "bg-gray-50 dark:bg-dark-700/40 border-gray-200 dark:border-dark-600/50",
          className
        )}
      >
        <div className="flex items-center gap-1.5">
          <TrendingUp className={cn("text-cyan-600 dark:text-accent-400", iconSizes[size])} />
          <span className="text-xs sm:text-sm text-gray-600 dark:text-dark-300">Value</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs sm:text-sm font-bold text-cyan-600 dark:text-accent-400">
            {formatValue(valueScore)}
          </span>
          {showTier && (
            <span
              className={cn(
                "text-xs font-medium px-1.5 py-0.5 rounded-full",
                tier.bgClass,
                tier.textClass
              )}
            >
              {tier.label}
            </span>
          )}
        </div>
      </div>
    );
  }

  // Default variant
  return (
    <span
      className={cn(
        "inline-flex items-center font-semibold rounded-full border",
        sizeClasses[size],
        isValue ? tier.bgClass : "bg-gray-100 dark:bg-gray-500/20",
        isValue ? tier.textClass : "text-gray-500 dark:text-gray-400",
        isValue ? `border-${tier.color}-300 dark:border-${tier.color}-500/40` : "border-gray-300 dark:border-gray-500/40",
        className
      )}
    >
      {isValue && <Sparkles className={iconSizes[size]} />}
      <TrendingUp className={iconSizes[size]} />
      <span>{formatValue(valueScore)}</span>
      {showTier && (
        <span className="opacity-80">({tier.label})</span>
      )}
    </span>
  );
}

// Simplified badge for list views
export function ValueBetIndicator({ valueScore }: { valueScore: number }) {
  if (!isValueBet(valueScore)) return null;

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-100 dark:bg-emerald-500/20 border border-emerald-300 dark:border-emerald-500/40 rounded-full text-xs font-bold text-emerald-700 dark:text-emerald-300">
      <Sparkles className="w-3 h-3" />
      Value Bet
    </span>
  );
}
