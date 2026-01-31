"use client";

import { useQuery } from "@tanstack/react-query";
import { Calendar, ChevronRight } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { fetchUpcomingMatches } from "@/lib/api";
import type { Match } from "@/lib/types";

// Mock data
const mockMatches: Match[] = [
  {
    id: 1,
    homeTeam: "Liverpool",
    awayTeam: "Chelsea",
    competition: "Premier League",
    competitionCode: "PL",
    matchDate: new Date(Date.now() + 86400000).toISOString(),
    status: "scheduled",
  },
  {
    id: 2,
    homeTeam: "Atletico Madrid",
    awayTeam: "Sevilla",
    competition: "La Liga",
    competitionCode: "PD",
    matchDate: new Date(Date.now() + 86400000 * 1.5).toISOString(),
    status: "scheduled",
  },
  {
    id: 3,
    homeTeam: "Leipzig",
    awayTeam: "Leverkusen",
    competition: "Bundesliga",
    competitionCode: "BL1",
    matchDate: new Date(Date.now() + 86400000 * 2).toISOString(),
    status: "scheduled",
  },
  {
    id: 4,
    homeTeam: "AC Milan",
    awayTeam: "Napoli",
    competition: "Serie A",
    competitionCode: "SA",
    matchDate: new Date(Date.now() + 86400000 * 2.5).toISOString(),
    status: "scheduled",
  },
  {
    id: 5,
    homeTeam: "Lyon",
    awayTeam: "Monaco",
    competition: "Ligue 1",
    competitionCode: "FL1",
    matchDate: new Date(Date.now() + 86400000 * 3).toISOString(),
    status: "scheduled",
  },
];

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
  const { data: matches = mockMatches } = useQuery({
    queryKey: ["upcomingMatches"],
    queryFn: () => fetchUpcomingMatches(),
    enabled: true,
    initialData: mockMatches,
  });

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
      <div className="divide-y divide-dark-700">
        {matches.map((match) => (
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
            {match.homeTeam} vs {match.awayTeam}
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
