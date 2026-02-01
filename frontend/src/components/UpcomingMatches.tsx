"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Loader2, AlertCircle } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { fetchUpcomingMatches } from "@/lib/api";
import type { Match } from "@/lib/types";

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
  const { data: matches, isLoading, error } = useQuery({
    queryKey: ["upcomingMatches"],
    queryFn: () => fetchUpcomingMatches(3),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 sm:p-8">
        <div className="flex items-center justify-center">
          <Loader2 className="w-7 sm:w-8 h-7 sm:h-8 text-primary-400 animate-spin" />
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
  const matchDate = new Date(match.matchDate);
  const homeTeam = match.homeTeam;
  const awayTeam = match.awayTeam;

  return (
    <Link
      href={`/match/${match.id}`}
      className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 sm:px-6 py-3 sm:py-4 hover:bg-dark-700/50 transition-colors gap-2 sm:gap-4"
    >
      <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0 w-full sm:w-auto">
        <div
          className={`w-2 h-7 sm:h-8 rounded-full flex-shrink-0 ${
            competitionColors[match.competitionCode] || "bg-dark-500"
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
