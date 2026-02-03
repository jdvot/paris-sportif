"use client";

import { Flame, Zap, AlertTriangle, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { getConfidenceTier, formatConfidence, CONFIDENCE_TIERS } from "@/lib/constants";

interface ConfidenceScoreProps {
  confidence: number;
  showLabel?: boolean;
  showPercentage?: boolean;
  size?: "sm" | "md" | "lg";
  variant?: "badge" | "inline" | "detailed";
  className?: string;
}

const iconMap = {
  flame: Flame,
  zap: Zap,
  alertTriangle: AlertTriangle,
  barChart: BarChart3,
};

export function ConfidenceScore({
  confidence,
  showLabel = true,
  showPercentage = true,
  size = "md",
  variant = "badge",
  className,
}: ConfidenceScoreProps) {
  const tier = getConfidenceTier(confidence);
  const IconComponent = iconMap[tier.icon as keyof typeof iconMap] || BarChart3;

  const sizeClasses = {
    sm: {
      container: "text-[10px] px-1.5 py-0.5 gap-1",
      icon: "w-3 h-3",
    },
    md: {
      container: "text-xs px-2 py-1 gap-1.5",
      icon: "w-3.5 h-3.5",
    },
    lg: {
      container: "text-sm px-3 py-1.5 gap-2",
      icon: "w-4 h-4",
    },
  };

  if (variant === "inline") {
    return (
      <span className={cn("inline-flex items-center gap-1", className)}>
        <IconComponent className={cn(sizeClasses[size].icon, tier.textClass)} />
        {showPercentage && (
          <span className={cn("font-semibold", tier.textClass)}>
            {formatConfidence(confidence)}
          </span>
        )}
        {showLabel && (
          <span className={cn("opacity-80", tier.textClass)}>
            ({tier.label})
          </span>
        )}
      </span>
    );
  }

  if (variant === "detailed") {
    return (
      <div
        className={cn(
          "flex items-center justify-between p-2 sm:p-3 rounded-lg border",
          tier.bgClass,
          tier.borderClass,
          className
        )}
      >
        <div className="flex items-center gap-2">
          <IconComponent className={cn(sizeClasses[size].icon, tier.textClass)} />
          <span className={cn("font-medium", tier.textClass)}>
            Confiance
          </span>
        </div>
        <div className="flex items-center gap-2">
          {showPercentage && (
            <span className={cn("font-bold", tier.textClass)}>
              {formatConfidence(confidence)}
            </span>
          )}
          {showLabel && (
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

  // Default badge variant
  return (
    <span
      className={cn(
        "inline-flex items-center font-semibold rounded-full border",
        sizeClasses[size].container,
        tier.bgClass,
        tier.textClass,
        tier.borderClass,
        className
      )}
    >
      <IconComponent className={sizeClasses[size].icon} />
      {showPercentage && <span>{formatConfidence(confidence)}</span>}
      {showLabel && <span className="opacity-80">{tier.label}</span>}
    </span>
  );
}

// Compact indicator for list views
export function ConfidenceIndicator({
  confidence,
  size = "md",
}: {
  confidence: number;
  size?: "sm" | "md" | "lg";
}) {
  const tier = getConfidenceTier(confidence);
  const IconComponent = iconMap[tier.icon as keyof typeof iconMap] || BarChart3;

  const iconSizes = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5",
  };

  return (
    <div className="flex items-center gap-1">
      <IconComponent className={cn(iconSizes[size], tier.textClass)} />
      <span className={cn("font-bold text-sm", tier.textClass)}>
        {formatConfidence(confidence)}
      </span>
    </div>
  );
}
