import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind CSS classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a probability as percentage
 */
export function formatProbability(prob: number): string {
  return `${Math.round(prob * 100)}%`;
}

/**
 * Format a decimal odds value
 */
export function formatOdds(odds: number): string {
  return odds.toFixed(2);
}

/**
 * Get outcome label in French
 */
export function getOutcomeLabel(
  outcome: "home" | "draw" | "away",
  homeTeam: string,
  awayTeam: string
): string {
  switch (outcome) {
    case "home":
      return `Victoire ${homeTeam}`;
    case "draw":
      return "Match nul";
    case "away":
      return `Victoire ${awayTeam}`;
  }
}

/**
 * Get confidence level color class
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.75) return "text-primary-400";
  if (confidence >= 0.65) return "text-green-400";
  if (confidence >= 0.55) return "text-yellow-400";
  return "text-orange-400";
}

/**
 * Get value score color class
 */
export function getValueColor(value: number): string {
  if (value >= 0.15) return "text-primary-400";
  if (value >= 0.08) return "text-green-400";
  if (value >= 0.05) return "text-yellow-400";
  return "text-dark-400";
}

/**
 * Check if an error is an authentication error (401/403)
 * Used to skip local error UI and let global handler redirect
 */
export function isAuthError(error: unknown): boolean {
  const err = error as { status?: number; name?: string };
  return err?.name === 'ApiError' && [401, 403].includes(err?.status || 0);
}

/**
 * Safely reload the page, handling SSR and potential errors
 * Use this instead of directly calling window.location.reload()
 */
export function safeReload(): void {
  if (typeof window !== "undefined") {
    try {
      window.location.reload();
    } catch {
      // Fallback: navigate to current URL
      window.location.href = window.location.href;
    }
  }
}

/**
 * Safely navigate to a URL, handling SSR
 */
export function safeNavigate(url: string): void {
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
}
