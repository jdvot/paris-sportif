import { MatchCardSkeleton } from "@/components/skeletons";

export default function MatchesLoading() {
  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header placeholder */}
      <section className="text-center py-6 sm:py-8 px-4">
        <div className="h-8 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mx-auto mb-3" />
        <div className="h-4 w-64 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mx-auto" />
      </section>

      {/* Date range filter placeholder */}
      <section className="flex flex-wrap gap-2 sm:gap-3 px-4 sm:px-0">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 w-28 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
        ))}
      </section>

      {/* Match groups */}
      {Array.from({ length: 2 }).map((_, groupIdx) => (
        <section
          key={groupIdx}
          className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden mx-4 sm:mx-0"
        >
          {/* Date header */}
          <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 dark:border-slate-700">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-5 h-5 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
              <div className="space-y-1">
                <div className="h-4 w-44 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                <div className="h-3 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
              </div>
            </div>
            <div className="w-5 h-5 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
          </div>

          {/* Match rows */}
          <div className="divide-y divide-gray-200 dark:divide-slate-700">
            {Array.from({ length: 3 }).map((_, i) => (
              <MatchCardSkeleton key={i} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
