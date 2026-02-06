/**
 * Skeleton loader components for Paris Sportif.
 *
 * Each skeleton mirrors the layout of the real component it replaces,
 * using Tailwind `animate-pulse` with `bg-slate-200 dark:bg-slate-700 rounded`
 * for placeholder blocks.
 */

// ---------------------------------------------------------------------------
// MatchCardSkeleton
// Mirrors the MatchCard in /app/(protected)/matches/page.tsx:
//   competition indicator | team names + score area | time + chevron
// ---------------------------------------------------------------------------
export function MatchCardSkeleton() {
  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 sm:px-6 py-3 sm:py-4 gap-2 sm:gap-4">
      {/* Left: competition bar + team names */}
      <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0 w-full sm:w-auto">
        {/* Competition color indicator */}
        <div className="w-2 sm:w-3 h-8 sm:h-10 rounded-full bg-slate-200 dark:bg-slate-700 animate-pulse flex-shrink-0" />

        {/* Match info */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Team names row */}
          <div className="flex items-center gap-2">
            <div className="h-4 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            <div className="h-4 w-6 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            <div className="h-4 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
          </div>
          {/* Competition badge + matchday */}
          <div className="flex items-center gap-2">
            <div className="h-5 w-20 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            <div className="h-3 w-14 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
          </div>
        </div>
      </div>

      {/* Right: time + chevron */}
      <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-end">
        <div className="space-y-1 text-right">
          <div className="h-4 w-12 bg-slate-200 dark:bg-slate-700 rounded animate-pulse ml-auto" />
          <div className="h-3 w-16 bg-slate-200 dark:bg-slate-700 rounded animate-pulse ml-auto" />
        </div>
        <div className="w-5 h-5 bg-slate-200 dark:bg-slate-700 rounded animate-pulse flex-shrink-0" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PredictionCardSkeleton
// Mirrors PredictionCardPremium:
//   header (rank badge, teams, confidence) |
//   body (prob bars, recommendation, explanation, value/score, factors)
//   footer (confidence tier)
// ---------------------------------------------------------------------------
export function PredictionCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800">
      {/* Header */}
      <div className="px-3 sm:px-6 py-3 sm:py-4 border-b border-gray-200 dark:border-slate-700/50">
        <div className="flex items-start justify-between gap-3">
          {/* Left: rank + teams */}
          <div className="flex items-start gap-2 sm:gap-4 flex-1 min-w-0">
            {/* Rank circle */}
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-slate-200 dark:bg-slate-700 animate-pulse flex-shrink-0" />
            <div className="min-w-0 flex-1 space-y-2">
              <div className="h-4 w-48 sm:w-64 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
              <div className="h-3 w-28 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            </div>
          </div>
          {/* Right: confidence badge */}
          <div className="w-14 h-12 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse flex-shrink-0" />
        </div>
      </div>

      {/* Body */}
      <div className="px-3 sm:px-6 py-3 sm:py-4 space-y-3 sm:space-y-4">
        {/* Probability bars */}
        <div className="flex gap-1.5 sm:gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex-1 min-w-0 space-y-1">
              <div className="flex justify-between">
                <div className="h-3 w-12 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                <div className="h-3 w-8 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
              </div>
              <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full animate-pulse" />
            </div>
          ))}
        </div>

        {/* Recommended bet */}
        <div className="h-10 sm:h-12 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />

        {/* Explanation lines */}
        <div className="space-y-2">
          <div className="h-3 w-full bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
          <div className="h-3 w-4/5 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
        </div>

        {/* Value + Pick score row */}
        <div className="grid grid-cols-2 gap-2">
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
        </div>

        {/* Key factors */}
        <div className="flex flex-wrap gap-1.5 sm:gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-6 w-20 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="px-3 sm:px-6 py-2 sm:py-3 border-t border-gray-200 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-800/50 flex items-center justify-between">
        <div className="h-3 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
        <div className="h-3 w-14 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StatCardSkeleton
// Mirrors the stat cards in /app/(protected)/dashboard/page.tsx:
//   CardHeader (title + icon) | CardContent (large value + description)
// ---------------------------------------------------------------------------
export function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
      {/* Header row: label + icon */}
      <div className="flex items-center justify-between mb-3">
        <div className="h-3 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
        <div className="w-4 h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
      </div>
      {/* Large value */}
      <div className="h-8 w-20 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-2" />
      {/* Description */}
      <div className="h-3 w-28 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// TableRowSkeleton
// Generic table row skeleton with configurable column count.
// ---------------------------------------------------------------------------
export function TableRowSkeleton({ columns = 4 }: { columns?: number }) {
  return (
    <tr className="border-b border-gray-200 dark:border-slate-700">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div
            className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse"
            style={{ width: i === 0 ? "60%" : "40%" }}
          />
        </td>
      ))}
    </tr>
  );
}
