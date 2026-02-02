// Confidence thresholds for prediction tiers
export const CONFIDENCE_THRESHOLDS = {
  VERY_HIGH: 0.75, // Très Haut - primary/green
  HIGH: 0.65, // Haut - blue
  MEDIUM: 0.55, // Moyen - yellow
} as const;

// Chart colors for consistency across the app
export const CHART_COLORS = {
  primary: "rgb(34, 197, 94)", // primary-500 (green)
  accent: "rgb(59, 130, 246)", // accent-500 (blue)
  yellow: "rgb(250, 204, 21)", // yellow-400
  orange: "rgb(251, 146, 60)", // orange-400
  background: "rgb(15, 23, 42)", // dark-900
  text: "rgb(248, 250, 252)", // dark-50
} as const;

// Tailwind color class mappings for confidence levels
export const CONFIDENCE_COLORS = {
  veryHigh: {
    text: "text-primary-600 dark:text-primary-400",
    bg: "bg-primary-100 dark:bg-primary-500/20",
    border: "border-primary-300 dark:border-primary-500/40",
    badge: "bg-primary-200 dark:bg-primary-500/30 text-primary-700 dark:text-primary-300",
  },
  high: {
    text: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-100 dark:bg-blue-500/20",
    border: "border-blue-300 dark:border-blue-500/40",
    badge: "bg-blue-200 dark:bg-blue-500/30 text-blue-700 dark:text-blue-300",
  },
  medium: {
    text: "text-yellow-600 dark:text-yellow-400",
    bg: "bg-yellow-100 dark:bg-yellow-500/20",
    border: "border-yellow-300 dark:border-yellow-500/40",
    badge: "bg-yellow-200 dark:bg-yellow-500/30 text-yellow-700 dark:text-yellow-300",
  },
  low: {
    text: "text-orange-600 dark:text-orange-400",
    bg: "bg-orange-100 dark:bg-orange-500/20",
    border: "border-orange-300 dark:border-orange-500/40",
    badge: "bg-orange-200 dark:bg-orange-500/30 text-orange-700 dark:text-orange-300",
  },
} as const;

// Helper function to get confidence tier
export function getConfidenceTier(confidence: number) {
  if (confidence >= CONFIDENCE_THRESHOLDS.VERY_HIGH) return "veryHigh";
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return "high";
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return "medium";
  return "low";
}

// Helper function to get confidence level label
export function getConfidenceLabel(confidence: number): string {
  if (confidence >= CONFIDENCE_THRESHOLDS.VERY_HIGH) return "Très Haut";
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return "Haut";
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return "Moyen";
  return "Bas";
}
