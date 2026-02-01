"use client";

import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg" | "xl";
  text?: string;
  className?: string;
}

export function LoadingSpinner({ size = "md", text, className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
    xl: "w-16 h-16",
  };

  return (
    <div className={cn("flex flex-col items-center justify-center gap-3", className)}>
      <div className="relative">
        {/* Outer ring */}
        <div
          className={cn(
            "rounded-full border-2 border-dark-700",
            sizeClasses[size]
          )}
        />
        {/* Spinning arc */}
        <div
          className={cn(
            "absolute top-0 left-0 rounded-full border-2 border-transparent border-t-primary-500 animate-spin",
            sizeClasses[size]
          )}
        />
        {/* Inner pulsing dot */}
        <div
          className={cn(
            "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary-500 animate-pulse",
            size === "sm" ? "w-1 h-1" : size === "md" ? "w-2 h-2" : size === "lg" ? "w-3 h-3" : "w-4 h-4"
          )}
        />
      </div>
      {text && (
        <p className="text-dark-400 text-sm animate-pulse">{text}</p>
      )}
    </div>
  );
}

interface SkeletonCardProps {
  className?: string;
  lines?: number;
  showHeader?: boolean;
  showFooter?: boolean;
}

export function SkeletonCard({ className, lines = 2, showHeader = true, showFooter = false }: SkeletonCardProps) {
  return (
    <div
      className={cn(
        "bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden",
        className
      )}
    >
      {showHeader && (
        <div className="px-4 sm:px-6 py-4 border-b border-dark-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-dark-700 animate-pulse" />
              <div className="space-y-2">
                <div className="h-4 w-32 sm:w-48 bg-dark-700 rounded animate-pulse" />
                <div className="h-3 w-20 sm:w-24 bg-dark-700/50 rounded animate-pulse" />
              </div>
            </div>
            <div className="hidden sm:block space-y-2 text-right">
              <div className="h-4 w-24 bg-dark-700 rounded animate-pulse ml-auto" />
              <div className="h-3 w-16 bg-dark-700/50 rounded animate-pulse ml-auto" />
            </div>
          </div>
        </div>
      )}
      <div className="px-4 sm:px-6 py-4 space-y-3">
        {/* Probability bars skeleton */}
        <div className="flex gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex-1 space-y-1">
              <div className="flex justify-between">
                <div className="h-3 w-12 bg-dark-700/50 rounded animate-pulse" />
                <div className="h-3 w-8 bg-dark-700/50 rounded animate-pulse" />
              </div>
              <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-dark-600 rounded-full animate-pulse"
                  style={{ width: `${30 + i * 15}%`, animationDelay: `${i * 100}ms` }}
                />
              </div>
            </div>
          ))}
        </div>
        {/* Content lines */}
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-4 bg-dark-700 rounded animate-pulse",
              i === 0 ? "w-full" : i === 1 ? "w-4/5" : "w-3/5"
            )}
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
      {showFooter && (
        <div className="px-4 sm:px-6 py-3 border-t border-dark-700">
          <div className="flex gap-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-6 w-20 bg-dark-700 rounded animate-pulse"
                style={{ animationDelay: `${i * 100}ms` }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function LoadingOverlay({ text = "Chargement..." }: { text?: string }) {
  return (
    <div className="fixed inset-0 bg-dark-900/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-dark-800 border border-dark-700 rounded-2xl p-8 shadow-2xl">
        <LoadingSpinner size="xl" text={text} />
      </div>
    </div>
  );
}

export function TableSkeleton({ rows = 5, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="grid gap-4 px-4 py-3 border-b border-dark-700 bg-dark-800/50" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {Array.from({ length: columns }).map((_, i) => (
          <div key={i} className="h-4 bg-dark-700 rounded animate-pulse" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="grid gap-4 px-4 py-3 border-b border-dark-700/50 last:border-0"
          style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div
              key={colIndex}
              className={cn(
                "h-4 bg-dark-700 rounded animate-pulse",
                colIndex === 0 ? "w-full" : "w-3/4"
              )}
              style={{ animationDelay: `${(rowIndex * columns + colIndex) * 50}ms` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
