import { PredictionCardSkeleton } from "@/components/skeletons";

export default function PicksLoading() {
  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header placeholder */}
      <section className="text-center py-6 sm:py-8 px-4">
        <div className="h-8 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mx-auto mb-3" />
        <div className="h-4 w-72 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mx-auto" />
      </section>

      {/* Date navigation placeholder */}
      <section className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 mx-4 sm:mx-0">
        <div className="flex items-center justify-center gap-6">
          <div className="h-8 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
          <div className="h-8 w-40 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
          <div className="h-8 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
        </div>
      </section>

      {/* Cards grid */}
      <div className="grid lg:grid-cols-3 gap-4 sm:gap-6 px-4 sm:px-0">
        <div className="lg:col-span-2 grid gap-3 sm:gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <PredictionCardSkeleton key={i} />
          ))}
        </div>

        {/* Sidebar placeholder */}
        <div className="lg:col-span-1">
          <div className="h-96 bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl animate-pulse" />
        </div>
      </div>
    </div>
  );
}
