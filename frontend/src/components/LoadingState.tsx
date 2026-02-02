"use client";

import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  variant?: "picks" | "matches" | "stats" | "minimal";
  count?: number;
  message?: string;
}

export function LoadingState({
  variant = "picks",
  count = 5,
  message = "Chargement...",
}: LoadingStateProps) {
  if (variant === "minimal") {
    return (
      <div className="flex items-center justify-center gap-3 py-4">
        <div className="relative">
          <div className="w-6 h-6 rounded-full border-2 border-gray-300 dark:border-slate-600" />
          <div className="absolute top-0 left-0 w-6 h-6 rounded-full border-2 border-transparent border-t-primary-500 animate-spin" />
        </div>
        <span className="text-gray-600 dark:text-slate-400 text-sm animate-pulse">{message}</span>
      </div>
    );
  }

  if (variant === "stats") {
    return (
      <div className="space-y-6 px-4 sm:px-0">
        {/* Header */}
        <div className="flex items-center justify-center gap-3 py-4">
          <div className="relative">
            <div className="w-6 h-6 rounded-full border-2 border-gray-300 dark:border-slate-600" />
            <div className="absolute top-0 left-0 w-6 h-6 rounded-full border-2 border-transparent border-t-primary-500 animate-spin" />
          </div>
          <span className="text-gray-600 dark:text-slate-400 text-sm animate-pulse">{message}</span>
        </div>

        {/* Cards Skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {[1, 2, 3, 4].map((idx) => (
            <div
              key={idx}
              className="bg-gradient-to-br from-primary-500/10 to-gray-50 dark:to-slate-800/50 border border-primary-500/20 rounded-xl p-4 sm:p-6 animate-pulse"
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="h-3 w-24 bg-gray-100 dark:bg-slate-700/50 rounded" />
                <div className="w-5 h-5 bg-gray-100 dark:bg-slate-700/50 rounded" />
              </div>
              <div className="h-8 w-20 bg-gray-200 dark:bg-slate-700 rounded mb-2" />
              <div className="h-3 w-28 bg-gray-100 dark:bg-slate-700/30 rounded" />
            </div>
          ))}
        </div>

        {/* Chart Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          <div className="lg:col-span-2 bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6">
            <div className="h-5 w-48 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mb-4" />
            <div className="h-72 sm:h-80 bg-gray-100 dark:bg-slate-700/30 rounded-lg animate-pulse" />
          </div>
          <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6">
            <div className="h-5 w-40 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mb-4" />
            <div className="h-72 sm:h-80 bg-gray-100 dark:bg-slate-700/30 rounded-lg animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (variant === "matches") {
    return (
      <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden mx-4 sm:mx-0">
        {/* Loading header */}
        <div className="flex items-center justify-center gap-3 py-3 border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/30">
          <div className="relative">
            <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-slate-600" />
            <div className="absolute top-0 left-0 w-5 h-5 rounded-full border-2 border-transparent border-t-primary-500 animate-spin" />
          </div>
          <span className="text-gray-600 dark:text-slate-400 text-xs animate-pulse">{message}</span>
        </div>

        {/* Skeleton rows */}
        <div className="divide-y divide-gray-200 dark:divide-slate-700">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 sm:px-6 py-3 sm:py-4 gap-2 sm:gap-4"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0 w-full sm:w-auto">
                <div className="w-2 h-7 sm:h-8 rounded-full bg-gradient-to-b from-gray-200 to-gray-300 dark:from-slate-600 dark:to-slate-700 animate-pulse flex-shrink-0" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 w-48 sm:w-64 bg-gradient-to-r from-gray-200 to-gray-300 dark:from-slate-700 dark:to-slate-600 rounded animate-pulse" />
                  <div className="h-3 w-24 bg-gray-100 dark:bg-slate-700/50 rounded animate-pulse" />
                </div>
              </div>
              <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-end">
                <div className="space-y-1 text-right">
                  <div className="h-3 w-24 bg-gray-200 dark:bg-slate-700 rounded animate-pulse ml-auto" />
                  <div className="h-3 w-12 bg-gray-100 dark:bg-slate-700/50 rounded animate-pulse ml-auto" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Default: picks variant
  return (
    <div className="grid gap-3 sm:gap-4 px-4 sm:px-0">
      {/* Loading header */}
      <div className="flex items-center justify-center gap-3 py-4">
        <div className="relative">
          <div className="w-8 h-8 rounded-full border-2 border-gray-200 dark:border-slate-700" />
          <div className="absolute top-0 left-0 w-8 h-8 rounded-full border-2 border-transparent border-t-primary-500 animate-spin" />
        </div>
        <span className="text-gray-600 dark:text-slate-400 text-sm animate-pulse">{message}</span>
      </div>

      {/* Skeleton cards */}
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden animate-stagger-in"
          style={{ animationDelay: `${i * 50}ms` } as React.CSSProperties}
        >
          {/* Header skeleton */}
          <div className="px-4 sm:px-6 py-4 border-b border-gray-200 dark:border-slate-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-r from-gray-200 to-gray-300 dark:from-slate-700 dark:to-slate-600 animate-pulse" />
                <div className="space-y-2">
                  <div className="h-4 w-40 sm:w-56 bg-gradient-to-r from-gray-200 to-gray-300 dark:from-slate-700 dark:to-slate-600 rounded animate-pulse" />
                  <div className="h-3 w-24 bg-gray-100 dark:bg-slate-700/50 rounded animate-pulse" />
                </div>
              </div>
              <div className="hidden sm:block space-y-2 text-right">
                <div className="h-4 w-28 bg-gradient-to-r from-primary-200 dark:from-primary-500/20 to-gray-300 dark:to-slate-700 rounded animate-pulse ml-auto" />
                <div className="h-3 w-20 bg-gray-100 dark:bg-slate-700/50 rounded animate-pulse ml-auto" />
              </div>
            </div>
          </div>

          {/* Body skeleton */}
          <div className="px-4 sm:px-6 py-4 space-y-4">
            {/* Probability bars */}
            <div className="flex flex-col sm:flex-row gap-2">
              {[1, 2, 3].map((j) => (
                <div key={j} className="flex-1 space-y-1">
                  <div className="flex justify-between">
                    <div className="h-3 w-16 bg-gray-100 dark:bg-slate-700/50 rounded animate-pulse" />
                    <div className="h-3 w-10 bg-gray-100 dark:bg-slate-700/50 rounded animate-pulse" />
                  </div>
                  <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-gray-300 to-gray-400 dark:from-slate-600 dark:to-slate-500 rounded-full animate-pulse"
                      style={{ width: `${25 + j * 20}%`, animationDelay: `${(i * 3 + j) * 100}ms` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Recommendation skeleton */}
            <div className="h-12 bg-primary-50 dark:bg-primary-500/5 border border-primary-200 dark:border-primary-500/10 rounded-lg animate-pulse" />

            {/* Value score skeleton */}
            <div className="h-10 bg-gray-50 dark:bg-slate-700/30 border border-gray-200 dark:border-slate-600/50 rounded-lg animate-pulse" />

            {/* Description skeleton */}
            <div className="space-y-2">
              <div className="h-3 w-full bg-gray-100 dark:bg-slate-700/50 rounded animate-pulse" />
              <div className="h-3 w-4/5 bg-gray-100 dark:bg-slate-700/30 rounded animate-pulse" />
            </div>

            {/* Tags skeleton */}
            <div className="flex gap-2">
              {[1, 2, 3].map((j) => (
                <div key={j} className="h-6 w-24 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
