"use client";

import { ChevronRight, AlertCircle } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { useGetUpcomingMatches } from "@/lib/api/endpoints/matches/matches";
import type { Match } from "@/lib/api/models";

const competitionColors: Record<string, string> = {
  PL: "bg-purple-500",
  PD: "bg-orange-500",
  BL1: "bg-red-500",
  SA: "bg-blue-500",
  FL1: "bg-green-500",
  CL: "bg-indigo-500",
  EL: "bg-amber-500",
};

export function UpcomingMatches() {
  const { data: response, isLoading, error } = useGetUpcomingMatches(
    { days: 3 },
    { query: { staleTime: 5 * 60 * 1000 } }
  );

  // Extract matches from response - API returns { matches: [...] } directly
  const responseData = response as unknown as { matches?: Match[] } | undefined;
  const matches = responseData?.matches || [];

  if (isLoading) {
    return (
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden mx-4 sm:mx-0">
        {/* Loading indicator */}
        <div className="flex items-center justify-center gap-3 py-3 border-b border-dark-700 bg-dark-800/30">
          <div className="relative">
            <div className="w-5 h-5 rounded-full border-2 border-dark-600" />
            <div className="absolute top-0 left-0 w-5 h-5 rounded-full border-2 border-transparent border-t-primary-500 animate-spin" />
          </div>
          <span className="text-dark-400 text-xs animate-pulse">Chargement des matchs...</span>
        </div>
        {/* Skeleton rows */}
        <div className="divide-y divide-dark-700">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 sm:px-6 py-3 sm:py-4 gap-2 sm:gap-4"
            >
              <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0 w-full sm:w-auto">
                <div
                  className="w-2 h-7 sm:h-8 rounded-full bg-gradient-to-b from-dark-600 to-dark-700 animate-pulse flex-shrink-0"
                  style={{ animationDelay: `${i * 100}ms` }}
                />
                <div className="space-y-2 flex-1">
                  <div className="h-4 w-48 sm:w-64 bg-gradient-to-r from-dark-700 to-dark-600 rounded animate-pulse" style={{ animationDelay: `${i * 50}ms` }} />
                  <div className="h-3 w-24 bg-dark-700/50 rounded animate-pulse" style={{ animationDelay: `${i * 75}ms` }} />
                </div>
              </div>
              <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-end">
                <div className="space-y-1 text-right">
                  <div className="h-3 w-24 bg-dark-700 rounded animate-pulse ml-auto" />
                  <div className="h-3 w-12 bg-dark-700/50 rounded animate-pulse ml-auto" />
                </div>
                <div className="w-4 sm:w-5 h-4 sm:h-5 bg-dark-700 rounded animate-pulse" />
              </div>
            </div>
          ))}
        </div>
        {/* Footer skeleton */}
        <div className="flex items-center justify-center py-3 sm:py-4 border-t border-dark-700">
          <div className="h-4 w-32 bg-dark-700 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-dark-800/50 border border-red-500/30 rounded-xl p-6 sm:p-8 text-center mx-4 sm:mx-0">
        <AlertCircle className="w-7 sm:w-8 h-7 sm:h-8 text-red-400 mx-auto mb-2" />
        <p className="text-dark-400 text-sm">Impossible de charger les matchs</p>
      </div>
    );
  }

  if (!matches || matches.length === 0) {
    return (
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 sm:p-8 text-center mx-4 sm:mx-0">
        <p className="text-dark-400 text-sm">Aucun match a venir</p>
      </div>
    );
  }

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden mx-4 sm:mx-0">
      <div className="divide-y divide-dark-700">
        {matches.slice(0, 5).map((match) => (
          <MatchRow key={match.id} match={match} />
        ))}
      </div>

      <Link
        href="/matches"
        className="flex items-center justify-center gap-2 py-3 sm:py-4 text-sm sm:text-base text-primary-400 hover:text-primary-300 transition-colors border-t border-dark-700"
      >
        <span>Voir tous les matchs</span>
        <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

function MatchRow({ match }: { match: Match }) {
  // Use snake_case properties from Orval types
  const matchDate = new Date(match.match_date);
  const homeTeam = typeof match.home_team === 'string' ? match.home_team : match.home_team.name;
  const awayTeam = typeof match.away_team === 'string' ? match.away_team : match.away_team.name;
  const competitionCode = match.competition_code;

  return (
    <Link
      href={`/match/${match.id}`}
      className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 sm:px-6 py-3 sm:py-4 hover:bg-dark-700/50 transition-colors gap-2 sm:gap-4"
    >
      <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0 w-full sm:w-auto">
        <div
          className={`w-2 h-7 sm:h-8 rounded-full flex-shrink-0 ${
            competitionColors[competitionCode] || "bg-dark-500"
          }`}
        />
        <div className="min-w-0">
          <h4 className="font-medium text-sm sm:text-base text-white truncate">
            {homeTeam} vs {awayTeam}
          </h4>
          <p className="text-xs sm:text-sm text-dark-400">{match.competition}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-end">
        <div className="text-right">
          <p className="text-xs sm:text-sm text-white">
            {format(matchDate, "EEEE d MMM", { locale: fr })}
          </p>
          <p className="text-xs sm:text-sm text-dark-400">
            {format(matchDate, "HH:mm", { locale: fr })}
          </p>
        </div>
        <ChevronRight className="w-4 sm:w-5 h-4 sm:h-5 text-dark-500 flex-shrink-0" />
      </div>
    </Link>
  );
}
