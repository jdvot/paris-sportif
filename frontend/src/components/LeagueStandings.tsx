"use client";

import { useTranslations } from "next-intl";
import type { StandingsResponse } from "@/lib/api/models";

interface LeagueStandingsProps {
  standings: StandingsResponse;
  isLoading?: boolean;
}

export function LeagueStandings({ standings, isLoading = false }: LeagueStandingsProps) {
  const t = useTranslations("standings");
  const tCommon = useTranslations("common");
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden">
        {/* Loading header */}
        <div className="flex items-center justify-center gap-3 py-4 border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/30">
          <div className="relative">
            <div className="w-6 h-6 rounded-full border-2 border-gray-300 dark:border-slate-600" />
            <div className="absolute top-0 left-0 w-6 h-6 rounded-full border-2 border-transparent border-t-primary-500 animate-spin" />
          </div>
          <span className="text-gray-600 dark:text-slate-400 text-sm animate-pulse">{tCommon("loadingStandings")}</span>
        </div>
        {/* Table Header Skeleton */}
        <div className="hidden md:grid grid-cols-12 gap-4 bg-gray-100 dark:bg-slate-900/50 border-b border-gray-200 dark:border-slate-700 px-4 sm:px-6 py-3 sm:py-4">
          <div className="col-span-1 h-4 w-6 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
          <div className="col-span-4 h-4 w-20 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
          <div className="col-span-1 h-4 w-6 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-6 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-6 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-6 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-8 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-8 bg-gray-200 dark:bg-slate-700 rounded animate-pulse ml-auto" />
        </div>
        {/* Skeleton Rows */}
        <div className="divide-y divide-gray-200 dark:divide-slate-700">
          {Array.from({ length: 10 }).map((_, idx) => (
            <div key={idx}>
              {/* Desktop Skeleton */}
              <div className="hidden md:grid grid-cols-12 gap-4 px-4 sm:px-6 py-3 sm:py-4 items-center">
                <div className="col-span-1">
                  <div className="h-5 w-6 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" style={{ animationDelay: `${idx * 50}ms` }} />
                </div>
                <div className="col-span-4 flex items-center gap-3">
                  <div className="w-8 h-8 bg-gradient-to-r from-gray-200 to-gray-300 dark:from-slate-700 dark:to-slate-600 rounded animate-pulse" style={{ animationDelay: `${idx * 50}ms` }} />
                  <div className="h-4 w-32 bg-gradient-to-r from-gray-200 to-gray-300 dark:from-slate-700 dark:to-slate-600 rounded animate-pulse" style={{ animationDelay: `${idx * 75}ms` }} />
                </div>
                {[1, 2, 3, 4, 5].map((col) => (
                  <div key={col} className="col-span-1 flex justify-center">
                    <div className="h-4 w-6 bg-gray-200 dark:bg-slate-700/50 rounded animate-pulse" style={{ animationDelay: `${(idx * 5 + col) * 30}ms` }} />
                  </div>
                ))}
                <div className="col-span-1 flex justify-end">
                  <div className="h-5 w-8 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" style={{ animationDelay: `${idx * 50}ms` }} />
                </div>
              </div>
              {/* Mobile Skeleton */}
              <div className="md:hidden px-4 py-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-6 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
                    <div className="w-6 h-6 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
                    <div className="h-4 w-28 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
                  </div>
                  <div className="h-4 w-8 bg-primary-500/20 rounded animate-pulse" />
                </div>
                <div className="flex gap-4 pl-8">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-3 w-8 bg-gray-200 dark:bg-slate-700/50 rounded animate-pulse" />
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
        {/* Legend Skeleton */}
        <div className="border-t border-gray-200 dark:border-slate-700 px-4 sm:px-6 py-3 sm:py-4 bg-gray-100 dark:bg-slate-900/30">
          <div className="flex gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-3 h-3 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
                <div className="h-3 w-24 bg-gray-200 dark:bg-slate-700/50 rounded animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!standings.standings || standings.standings.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-6 sm:p-8 text-center">
        <p className="text-gray-600 dark:text-slate-400">{t("noStandings")}</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden">
      {/* Table Header */}
      <div className="hidden md:grid grid-cols-12 gap-4 bg-gray-100 dark:bg-slate-900/50 border-b border-gray-200 dark:border-slate-700 px-4 sm:px-6 py-3 sm:py-4 text-xs sm:text-sm font-semibold text-gray-700 dark:text-slate-300 sticky top-0">
        <div className="col-span-1">#</div>
        <div className="col-span-4">{t("team")}</div>
        <div className="col-span-1 text-center">{t("played")}</div>
        <div className="col-span-1 text-center">{t("won")}</div>
        <div className="col-span-1 text-center">{t("drawn")}</div>
        <div className="col-span-1 text-center">{t("lost")}</div>
        <div className="col-span-1 text-center">{t("goalDiff")}</div>
        <div className="col-span-1 text-right">{t("points")}</div>
      </div>

      {/* Table Body */}
      <div className="divide-y divide-gray-200 dark:divide-slate-700">
        {standings.standings.map((team, idx) => {
          // Determine row background color based on position
          const getRowClass = () => {
            if (team.position <= 4) {
              // Top 4 - Champions League (light blue)
              return "bg-blue-50 dark:bg-blue-900/10 hover:bg-blue-100 dark:hover:bg-blue-900/20";
            } else if (team.position <= 6) {
              // 5-6 - Europa League (light purple)
              return "bg-purple-50 dark:bg-purple-900/10 hover:bg-purple-100 dark:hover:bg-purple-900/20";
            } else if (team.position > standings.standings.length - 3) {
              // Bottom 3 - Relegation (light red)
              return "bg-red-50 dark:bg-red-900/10 hover:bg-red-100 dark:hover:bg-red-900/20";
            }
            return "hover:bg-gray-50 dark:hover:bg-slate-700/30";
          };

          return (
            <div key={`${team.team_id}-${team.position}`} className={`${getRowClass()} transition-colors`}>
              {/* Desktop View */}
              <div className="hidden md:grid grid-cols-12 gap-4 px-4 sm:px-6 py-3 sm:py-4 items-center">
                {/* Position */}
                <div className="col-span-1">
                  <span className="text-sm sm:text-base font-bold text-gray-900 dark:text-white">
                    {team.position}
                  </span>
                </div>

                {/* Team Name and Logo */}
                <div className="col-span-4 flex items-center gap-2 sm:gap-3 min-w-0">
                  {team.team_logo_url ? (
                    <img
                      src={team.team_logo_url}
                      alt={team.team_name}
                      className="w-6 h-6 sm:w-8 sm:h-8 rounded flex-shrink-0 object-contain"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="w-6 h-6 sm:w-8 sm:h-8 bg-gray-200 dark:bg-slate-700 rounded flex-shrink-0" />
                  )}
                  <span className="text-sm sm:text-base font-medium text-gray-900 dark:text-white truncate">
                    {team.team_name}
                  </span>
                </div>

                {/* Played */}
                <div className="col-span-1 text-center">
                  <span className="text-sm text-gray-700 dark:text-slate-300">{team.played}</span>
                </div>

                {/* Won */}
                <div className="col-span-1 text-center">
                  <span className="text-sm text-green-600 dark:text-green-400 font-medium">{team.won}</span>
                </div>

                {/* Drawn */}
                <div className="col-span-1 text-center">
                  <span className="text-sm text-yellow-600 dark:text-yellow-400 font-medium">{team.drawn}</span>
                </div>

                {/* Lost */}
                <div className="col-span-1 text-center">
                  <span className="text-sm text-red-600 dark:text-red-400 font-medium">{team.lost}</span>
                </div>

                {/* Goal Difference */}
                <div className="col-span-1 text-center">
                  <span className={`text-sm font-medium ${
                    team.goal_difference > 0 ? "text-green-600 dark:text-green-400" :
                    team.goal_difference < 0 ? "text-red-600 dark:text-red-400" :
                    "text-gray-700 dark:text-slate-300"
                  }`}>
                    {team.goal_difference > 0 ? "+" : ""}{team.goal_difference}
                  </span>
                </div>

                {/* Points */}
                <div className="col-span-1 text-right">
                  <span className="text-sm sm:text-base font-bold text-gray-900 dark:text-white">{team.points}</span>
                </div>
              </div>

              {/* Mobile View */}
              <div className="md:hidden px-4 py-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  {/* Position and Team */}
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-sm font-bold text-gray-900 dark:text-white flex-shrink-0 w-6">{team.position}</span>
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      {team.team_logo_url ? (
                        <img
                          src={team.team_logo_url}
                          alt={team.team_name}
                          className="w-6 h-6 rounded flex-shrink-0 object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="w-6 h-6 bg-gray-200 dark:bg-slate-700 rounded flex-shrink-0" />
                      )}
                      <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {team.team_name}
                      </span>
                    </div>
                  </div>

                  {/* Points */}
                  <span className="text-sm font-bold text-primary-600 dark:text-primary-400 flex-shrink-0">
                    {team.points}
                  </span>
                </div>

                {/* Stats Row */}
                <div className="flex items-center justify-between text-xs text-gray-600 dark:text-slate-400 pl-8 gap-2">
                  <span>{team.played}J</span>
                  <span className="text-green-600 dark:text-green-400">{team.won}V</span>
                  <span className="text-yellow-600 dark:text-yellow-400">{team.drawn}N</span>
                  <span className="text-red-600 dark:text-red-400">{team.lost}D</span>
                  <span className={team.goal_difference > 0 ? "text-green-600 dark:text-green-400" : team.goal_difference < 0 ? "text-red-600 dark:text-red-400" : ""}>
                    {team.goal_difference > 0 ? "+" : ""}{team.goal_difference}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="border-t border-gray-200 dark:border-slate-700 px-4 sm:px-6 py-3 sm:py-4 bg-gray-50 dark:bg-slate-900/30">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 text-xs text-gray-600 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-blue-200 dark:bg-blue-900/50" />
            <span>{t("championsLeague")}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-purple-200 dark:bg-purple-900/50" />
            <span>{t("europaLeague")}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-red-200 dark:bg-red-900/50" />
            <span>{t("relegation")}</span>
          </div>
          <div className="text-xs text-gray-500 dark:text-slate-500 col-span-2 sm:col-span-1 lg:col-span-1">
            {t("legend")}
          </div>
        </div>
      </div>
    </div>
  );
}
