export default function BasketballLoading() {
  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header skeleton */}
      <section className="text-center py-6 sm:py-8 px-4">
        <div className="flex items-center justify-center gap-2 mb-2 sm:mb-3">
          <div className="w-7 h-7 sm:w-8 sm:h-8 bg-gray-200 dark:bg-slate-700 rounded-full animate-pulse" />
          <div className="h-8 sm:h-10 bg-gray-200 dark:bg-slate-700 rounded w-64 animate-pulse" />
        </div>
        <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-52 mx-auto animate-pulse" />
      </section>

      {/* Tabs skeleton */}
      <section className="px-4 sm:px-0">
        <div className="flex gap-1 bg-gray-100 dark:bg-slate-800 rounded-lg p-1 w-fit">
          <div className="h-8 w-14 bg-gray-200 dark:bg-slate-700 rounded-md animate-pulse" />
          <div className="h-8 w-14 bg-gray-200 dark:bg-slate-700 rounded-md animate-pulse" />
          <div className="h-8 w-24 bg-gray-200 dark:bg-slate-700 rounded-md animate-pulse" />
        </div>

        {/* Match cards skeleton */}
        <div className="space-y-4 mt-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-4 sm:p-6"
            >
              <div className="animate-pulse space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-5 w-12 bg-gray-200 dark:bg-slate-700 rounded" />
                    <div className="h-5 w-20 bg-gray-200 dark:bg-slate-700 rounded" />
                  </div>
                  <div className="h-4 w-28 bg-gray-200 dark:bg-slate-700 rounded" />
                </div>
                <div className="flex items-center justify-between py-1">
                  <div className="h-5 w-36 bg-gray-200 dark:bg-slate-700 rounded" />
                  <div className="h-7 w-10 bg-gray-200 dark:bg-slate-700 rounded" />
                </div>
                <div className="flex items-center justify-between py-1">
                  <div className="h-5 w-36 bg-gray-200 dark:bg-slate-700 rounded" />
                  <div className="h-7 w-10 bg-gray-200 dark:bg-slate-700 rounded" />
                </div>
                <div className="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-slate-700/50">
                  <div className="h-8 w-24 bg-gray-200 dark:bg-slate-700 rounded-lg" />
                  <div className="h-8 w-24 bg-gray-200 dark:bg-slate-700 rounded-lg" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
