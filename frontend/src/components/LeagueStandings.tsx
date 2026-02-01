"use client";

import { Loader2 } from "lucide-react";
import type { Standings } from "@/lib/types";

interface LeagueStandingsProps {
  standings: Standings;
  isLoading?: boolean;
}

export function LeagueStandings({ standings, isLoading = false }: LeagueStandingsProps) {
  if (isLoading) {
    return (
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
        {/* Loading header */}
        <div className="flex items-center justify-center gap-3 py-4 border-b border-dark-700 bg-dark-800/30">
          <div className="relative">
            <div className="w-6 h-6 rounded-full border-2 border-dark-600" />
            <div className="absolute top-0 left-0 w-6 h-6 rounded-full border-2 border-transparent border-t-primary-500 animate-spin" />
          </div>
          <span className="text-dark-400 text-sm animate-pulse">Chargement du classement...</span>
        </div>
        {/* Table Header Skeleton */}
        <div className="hidden md:grid grid-cols-12 gap-4 bg-dark-900/50 border-b border-dark-700 px-4 sm:px-6 py-3 sm:py-4">
          <div className="col-span-1 h-4 w-6 bg-dark-700 rounded animate-pulse" />
          <div className="col-span-4 h-4 w-20 bg-dark-700 rounded animate-pulse" />
          <div className="col-span-1 h-4 w-6 bg-dark-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-6 bg-dark-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-6 bg-dark-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-6 bg-dark-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-8 bg-dark-700 rounded animate-pulse mx-auto" />
          <div className="col-span-1 h-4 w-8 bg-dark-700 rounded animate-pulse ml-auto" />
        </div>
        {/* Skeleton Rows */}
        <div className="divide-y divide-dark-700">
          {Array.from({ length: 10 }).map((_, idx) => (
            <div key={idx}>
              {/* Desktop Skeleton */}
              <div className="hidden md:grid grid-cols-12 gap-4 px-4 sm:px-6 py-3 sm:py-4 items-center">
                <div className="col-span-1">
                  <div className="h-5 w-6 bg-dark-700 rounded animate-pulse" style={{ animationDelay: `${idx * 50}ms` }} />
                </div>
                <div className="col-span-4 flex items-center gap-3">
                  <div className="w-8 h-8 bg-gradient-to-r from-dark-700 to-dark-600 rounded animate-pulse" style={{ animationDelay: `${idx * 50}ms` }} />
                  <div className="h-4 w-32 bg-gradient-to-r from-dark-700 to-dark-600 rounded animate-pulse" style={{ animationDelay: `${idx * 75}ms` }} />
                </div>
                {[1, 2, 3, 4, 5].map((col) => (
                  <div key={col} className="col-span-1 flex justify-center">
                    <div className="h-4 w-6 bg-dark-700/50 rounded animate-pulse" style={{ animationDelay: `${(idx * 5 + col) * 30}ms` }} />
                  </div>
                ))}
                <div className="col-span-1 flex justify-end">
                  <div className="h-5 w-8 bg-dark-700 rounded animate-pulse" style={{ animationDelay: `${idx * 50}ms` }} />
                </div>
              </div>
              {/* Mobile Skeleton */}
              <div className="md:hidden px-4 py-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-6 bg-dark-700 rounded animate-pulse" />
                    <div className="w-6 h-6 bg-dark-700 rounded animate-pulse" />
                    <div className="h-4 w-28 bg-dark-700 rounded animate-pulse" />
                  </div>
                  <div className="h-4 w-8 bg-primary-500/20 rounded animate-pulse" />
                </div>
                <div className="flex gap-4 pl-8">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-3 w-8 bg-dark-700/50 rounded animate-pulse" />
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
        {/* Legend Skeleton */}
        <div className="border-t border-dark-700 px-4 sm:px-6 py-3 sm:py-4 bg-dark-900/30">
          <div className="flex gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-3 h-3 bg-dark-700 rounded animate-pulse" />
                <div className="h-3 w-24 bg-dark-700/50 rounded animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!standings.standings || standings.standings.length === 0) {
    return (
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 sm:p-8 text-center">
        <p className="text-dark-400">Aucun classement disponible</p>
      </div>
    );
  }

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
      {/* Table Header */}
      <div className="hidden md:grid grid-cols-12 gap-4 bg-dark-900/50 border-b border-dark-700 px-4 sm:px-6 py-3 sm:py-4 text-xs sm:text-sm font-semibold text-dark-300 sticky top-0">
        <div className="col-span-1">#</div>
        <div className="col-span-4">Équipe</div>
        <div className="col-span-1 text-center">J</div>
        <div className="col-span-1 text-center">G</div>
        <div className="col-span-1 text-center">N</div>
        <div className="col-span-1 text-center">P</div>
        <div className="col-span-1 text-center">+/-</div>
        <div className="col-span-1 text-right">PTS</div>
      </div>

      {/* Table Body */}
      <div className="divide-y divide-dark-700">
        {standings.standings.map((team, idx) => {
          // Determine row background color based on position
          const getRowClass = () => {
            if (team.position <= 4) {
              // Top 4 - Champions League (light blue)
              return "bg-blue-900/10 hover:bg-blue-900/20";
            } else if (team.position <= 6) {
              // 5-6 - Europa League (light purple)
              return "bg-purple-900/10 hover:bg-purple-900/20";
            } else if (team.position > standings.standings.length - 3) {
              // Bottom 3 - Relegation (light red)
              return "bg-red-900/10 hover:bg-red-900/20";
            }
            return "hover:bg-dark-700/30";
          };

          return (
            <div key={`${team.team_id}-${team.position}`} className={`${getRowClass()} transition-colors`}>
              {/* Desktop View */}
              <div className="hidden md:grid grid-cols-12 gap-4 px-4 sm:px-6 py-3 sm:py-4 items-center">
                {/* Position */}
                <div className="col-span-1">
                  <span className="text-sm sm:text-base font-bold text-white">
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
                    <div className="w-6 h-6 sm:w-8 sm:h-8 bg-dark-700 rounded flex-shrink-0" />
                  )}
                  <span className="text-sm sm:text-base font-medium text-white truncate">
                    {team.team_name}
                  </span>
                </div>

                {/* Played */}
                <div className="col-span-1 text-center">
                  <span className="text-sm text-dark-300">{team.played}</span>
                </div>

                {/* Won */}
                <div className="col-span-1 text-center">
                  <span className="text-sm text-green-400 font-medium">{team.won}</span>
                </div>

                {/* Drawn */}
                <div className="col-span-1 text-center">
                  <span className="text-sm text-yellow-400 font-medium">{team.drawn}</span>
                </div>

                {/* Lost */}
                <div className="col-span-1 text-center">
                  <span className="text-sm text-red-400 font-medium">{team.lost}</span>
                </div>

                {/* Goal Difference */}
                <div className="col-span-1 text-center">
                  <span className={`text-sm font-medium ${
                    team.goal_difference > 0 ? "text-green-400" :
                    team.goal_difference < 0 ? "text-red-400" :
                    "text-dark-300"
                  }`}>
                    {team.goal_difference > 0 ? "+" : ""}{team.goal_difference}
                  </span>
                </div>

                {/* Points */}
                <div className="col-span-1 text-right">
                  <span className="text-sm sm:text-base font-bold text-white">{team.points}</span>
                </div>
              </div>

              {/* Mobile View */}
              <div className="md:hidden px-4 py-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  {/* Position and Team */}
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-sm font-bold text-white flex-shrink-0 w-6">{team.position}</span>
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
                        <div className="w-6 h-6 bg-dark-700 rounded flex-shrink-0" />
                      )}
                      <span className="text-sm font-medium text-white truncate">
                        {team.team_name}
                      </span>
                    </div>
                  </div>

                  {/* Points */}
                  <span className="text-sm font-bold text-primary-400 flex-shrink-0">
                    {team.points}
                  </span>
                </div>

                {/* Stats Row */}
                <div className="flex items-center justify-between text-xs text-dark-400 pl-8 gap-2">
                  <span>{team.played}J</span>
                  <span className="text-green-400">{team.won}V</span>
                  <span className="text-yellow-400">{team.drawn}N</span>
                  <span className="text-red-400">{team.lost}D</span>
                  <span className={team.goal_difference > 0 ? "text-green-400" : team.goal_difference < 0 ? "text-red-400" : ""}>
                    {team.goal_difference > 0 ? "+" : ""}{team.goal_difference}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="border-t border-dark-700 px-4 sm:px-6 py-3 sm:py-4 bg-dark-900/30">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 text-xs text-dark-400">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-blue-900/50" />
            <span>Ligue des Champions</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-purple-900/50" />
            <span>Ligue Europa</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-red-900/50" />
            <span>Relégation</span>
          </div>
          <div className="text-xs text-dark-500 col-span-2 sm:col-span-1 lg:col-span-1">
            J=Joués, V=Victoires, N=Nuls, D=Défaites
          </div>
        </div>
      </div>
    </div>
  );
}
