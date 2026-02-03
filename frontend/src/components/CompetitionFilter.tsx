"use client";

import { X, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

interface Competition {
  id: string;
  name: string;
}

interface CompetitionFilterProps {
  competitions: Competition[];
  selected: string[];
  onToggle: (id: string) => void;
  onClear: () => void;
  isOpen: boolean;
  onToggleOpen: () => void;
}

const COMPETITION_COLORS: Record<string, string> = {
  PL: "from-purple-500 to-purple-600",
  PD: "from-orange-500 to-orange-600",
  BL1: "from-red-500 to-red-600",
  SA: "from-blue-500 to-blue-600",
  FL1: "from-green-500 to-green-600",
  CL: "from-indigo-500 to-indigo-600",
  EL: "from-amber-500 to-amber-600",
};

export function CompetitionFilter({
  competitions,
  selected,
  onToggle,
  onClear,
  isOpen,
  onToggleOpen,
}: CompetitionFilterProps) {
  const t = useTranslations("components.competitionFilter");

  return (
    <div className="space-y-3 sm:space-y-4">
      {/* Filter Button */}
      <button
        onClick={onToggleOpen}
        className={cn(
          "w-full sm:w-auto flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium",
          "transition-smooth border",
          isOpen
            ? "bg-primary-500/20 border-primary-500/50 text-primary-600 dark:text-primary-300"
            : "bg-gray-100 dark:bg-dark-800/50 border-gray-200 dark:border-dark-700 hover:border-gray-300 dark:hover:border-dark-600 text-gray-900 dark:text-white"
        )}
      >
        <Filter className="w-4 h-4 flex-shrink-0" />
        <span className="text-sm">{t("title")}</span>
        {selected.length > 0 && (
          <span className="ml-auto sm:ml-2 px-2 py-0.5 text-xs font-bold bg-primary-500/40 rounded-full flex-shrink-0">
            {selected.length}
          </span>
        )}
        <span
          className={cn(
            "ml-auto transition-transform flex-shrink-0",
            isOpen && "rotate-180"
          )}
        >
          ▼
        </span>
      </button>

      {/* Filter Panel */}
      {isOpen && (
        <div className="bg-white dark:bg-dark-800/60 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6 space-y-4 animate-scale-in">
          {/* Filter Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-3">
            {competitions.map((comp) => {
              const isSelected = selected.includes(comp.id);
              const colorGradient = COMPETITION_COLORS[comp.id] || "from-gray-500 to-gray-600 dark:from-dark-600 dark:to-dark-700";

              return (
                <button
                  key={comp.id}
                  onClick={() => onToggle(comp.id)}
                  className={cn(
                    "group relative px-3 sm:px-4 py-2.5 rounded-lg font-medium text-sm transition-smooth",
                    "border overflow-hidden",
                    isSelected
                      ? `bg-gradient-to-br ${colorGradient} border-current text-white shadow-lg`
                      : "bg-gray-100 dark:bg-dark-700/30 border-gray-300 dark:border-dark-600 text-gray-600 dark:text-dark-300 hover:border-gray-400 dark:hover:border-dark-500 hover:text-gray-900 dark:hover:text-white"
                  )}
                >
                  {/* Hover glow effect */}
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-10 bg-white transition-opacity pointer-events-none rounded-lg" />

                  {/* Background animation on select */}
                  {isSelected && (
                    <div className="absolute inset-0 opacity-30 animate-pulse pointer-events-none" />
                  )}

                  {/* Content */}
                  <div className="relative flex items-center justify-between gap-2">
                    <span className="truncate">{comp.name}</span>
                    {isSelected && (
                      <span className="flex-shrink-0 text-xs">✓</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Actions */}
          {selected.length > 0 && (
            <div className="flex items-center justify-between pt-3 border-t border-gray-200 dark:border-dark-600/50">
              <span className="text-xs sm:text-sm text-gray-500 dark:text-dark-400">
                {selected.length > 1
                  ? t("competitionsSelectedPlural", { count: selected.length })
                  : t("competitionsSelected", { count: selected.length })}
              </span>
              <button
                onClick={onClear}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs sm:text-sm text-primary-400 hover:text-primary-300 transition-colors hover:bg-primary-500/10 rounded-lg"
              >
                <X className="w-3.5 h-3.5" />
                <span>{t("reset")}</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
