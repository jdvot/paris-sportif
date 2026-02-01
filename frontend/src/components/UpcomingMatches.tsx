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
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8">
        <div className="flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-dark-800/50 border border-red-500/30 rounded-xl p-8 text-center">
        <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-dark-400">Impossible de charger les matchs</p>
      </div>
    );
  }

  if (!matches || matches.length === 0) {
    return (
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8 text-center">
        <p className="text-dark-400">Aucun match a venir</p>
      </div>
    );
  }

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
      <div className="divide-y divide-dark-700">
        {matches.slice(0, 5).map((match) => (
          <MatchRow key={match.id} match={match} />
        ))}
      </div>

      <Link
        href="/matches"
        className="flex items-center justify-center gap-2 py-4 text-primary-400 hover:text-primary-300 transition-colors border-t border-dark-700"
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
      className="flex items-center justify-between px-6 py-4 hover:bg-dark-700/50 transition-colors"
    >
      <div className="flex items-center gap-4">
        <div
          className={`w-2 h-8 rounded-full ${
            competitionColors[match.competitionCode] || "bg-dark-500"
          }`}
        />
        <div>
          <h4 className="font-medium text-white">
            {homeTeam} vs {awayTeam}
          </h4>
          <p className="text-sm text-dark-400">{match.competition}</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm text-white">
            {format(matchDate, "EEEE d MMM", { locale: fr })}
          </p>
          <p className="text-sm text-dark-400">
            {format(matchDate, "HH:mm", { locale: fr })}
          </p>
        </div>
        <ChevronRight className="w-5 h-5 text-dark-500" />
      </div>
    </Link>
  );
}
