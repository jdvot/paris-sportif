/**
 * Application-wide constants for predictions, colors, and thresholds
 */

// Confidence thresholds (0-1 scale)
export const CONFIDENCE_THRESHOLDS = {
  VERY_HIGH: 0.75, // >= 75%
  HIGH: 0.65, // >= 65%
  MEDIUM: 0.55, // >= 55%
  // Below 55% = Low
} as const;

// Value score thresholds (0-1 scale)
export const VALUE_THRESHOLDS = {
  EXCELLENT: 0.15, // >= 15% value
  GOOD: 0.08, // >= 8% value
  ACCEPTABLE: 0.05, // >= 5% value
  // Below 5% = Faible
} as const;

// Value bet threshold - when value > 0, it's a value bet
export const VALUE_BET_THRESHOLD = 0.05; // 5% minimum for "Value Bet" badge

// Confidence tier configuration
export const CONFIDENCE_TIERS = {
  veryHigh: {
    threshold: CONFIDENCE_THRESHOLDS.VERY_HIGH,
    label: "Tres Haut",
    labelEn: "Very High",
    icon: "flame",
    color: "primary",
    bgClass: "bg-primary-100 dark:bg-primary-500/20",
    textClass: "text-primary-700 dark:text-primary-300",
    borderClass: "border-primary-300 dark:border-primary-500/30",
  },
  high: {
    threshold: CONFIDENCE_THRESHOLDS.HIGH,
    label: "Haut",
    labelEn: "High",
    icon: "zap",
    color: "blue",
    bgClass: "bg-blue-100 dark:bg-blue-500/20",
    textClass: "text-blue-700 dark:text-blue-300",
    borderClass: "border-blue-300 dark:border-blue-500/30",
  },
  medium: {
    threshold: CONFIDENCE_THRESHOLDS.MEDIUM,
    label: "Moyen",
    labelEn: "Medium",
    icon: "alertTriangle",
    color: "yellow",
    bgClass: "bg-yellow-100 dark:bg-yellow-500/20",
    textClass: "text-yellow-700 dark:text-yellow-300",
    borderClass: "border-yellow-300 dark:border-yellow-500/30",
  },
  low: {
    threshold: 0,
    label: "Bas",
    labelEn: "Low",
    icon: "barChart",
    color: "orange",
    bgClass: "bg-orange-100 dark:bg-orange-500/20",
    textClass: "text-orange-700 dark:text-orange-300",
    borderClass: "border-orange-300 dark:border-orange-500/30",
  },
} as const;

// Value tier configuration
export const VALUE_TIERS = {
  excellent: {
    threshold: VALUE_THRESHOLDS.EXCELLENT,
    label: "Excellent",
    color: "emerald",
    bgClass: "bg-emerald-100 dark:bg-emerald-500/20",
    textClass: "text-emerald-700 dark:text-emerald-300",
  },
  good: {
    threshold: VALUE_THRESHOLDS.GOOD,
    label: "Bon",
    color: "cyan",
    bgClass: "bg-cyan-100 dark:bg-cyan-500/20",
    textClass: "text-cyan-700 dark:text-cyan-300",
  },
  acceptable: {
    threshold: VALUE_THRESHOLDS.ACCEPTABLE,
    label: "Acceptable",
    color: "blue",
    bgClass: "bg-blue-100 dark:bg-blue-500/20",
    textClass: "text-blue-700 dark:text-blue-300",
  },
  weak: {
    threshold: 0,
    label: "Faible",
    color: "gray",
    bgClass: "bg-gray-100 dark:bg-gray-500/20",
    textClass: "text-gray-700 dark:text-gray-300",
  },
} as const;

// Chart colors for visualizations
export const CHART_COLORS = {
  primary: "#10B981",
  accent: "#3B82F6",
  yellow: "#F59E0B",
  orange: "#F97316",
  red: "#EF4444",
  cyan: "#06B6D4",
  emerald: "#10B981",
  background: { light: "#F8FAFC", dark: "#0F172A" },
  text: { light: "#1E293B", dark: "#F1F5F9" },
} as const;

// Outcome colors
export const OUTCOME_COLORS = {
  home: {
    bg: "bg-primary-100 dark:bg-primary-500/20",
    text: "text-primary-700 dark:text-primary-300",
    bar: "bg-primary-500",
  },
  draw: {
    bg: "bg-yellow-100 dark:bg-yellow-500/20",
    text: "text-yellow-700 dark:text-yellow-300",
    bar: "bg-yellow-500",
  },
  away: {
    bg: "bg-blue-100 dark:bg-blue-500/20",
    text: "text-blue-700 dark:text-blue-300",
    bar: "bg-blue-500",
  },
} as const;

// Helper functions
export function getConfidenceTier(confidence: number) {
  if (confidence >= CONFIDENCE_THRESHOLDS.VERY_HIGH) return CONFIDENCE_TIERS.veryHigh;
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return CONFIDENCE_TIERS.high;
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return CONFIDENCE_TIERS.medium;
  return CONFIDENCE_TIERS.low;
}

export function getValueTier(valueScore: number) {
  if (valueScore >= VALUE_THRESHOLDS.EXCELLENT) return VALUE_TIERS.excellent;
  if (valueScore >= VALUE_THRESHOLDS.GOOD) return VALUE_TIERS.good;
  if (valueScore >= VALUE_THRESHOLDS.ACCEPTABLE) return VALUE_TIERS.acceptable;
  return VALUE_TIERS.weak;
}

export function isValueBet(valueScore: number): boolean {
  return valueScore >= VALUE_BET_THRESHOLD;
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function formatValue(valueScore: number): string {
  return `+${Math.round(valueScore * 100)}%`;
}
