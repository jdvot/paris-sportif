"use client";

import { useState, useMemo } from "react";
import {
  Calendar,
  ChevronRight,
  Filter,
  X,
  ChevronDown,
} from "lucide-react";
import Link from "next/link";
import { format, startOfDay, addDays, isSameDay } from "date-fns";
import { fr } from "date-fns/locale";
import { useListMatches } from "@/lib/api/endpoints/matches/matches";
import type { Match, MatchListResponse } from "@/lib/api/models";

const competitionColors: Record<string, string> = {
  PL: "bg-purple-500",
  PD: "bg-orange-500",
  BL1: "bg-red-500",
  SA: "bg-blue-500",
  FL1: "bg-green-500",
  CL: "bg-indigo-500",
  EL: "bg-amber-500",
};

const competitionLabels: Record<string, string> = {
  PL: "Premier League",
  PD: "La Liga",
  BL1: "Bundesliga",
  SA: "Serie A",
  FL1: "Ligue 1",
  CL: "Ligue des Champions",
  EL: "Ligue Europa",
};

type DateRange = "today" | "tomorrow" | "week" | "next7days" | "custom";

// Helper to get team name from Team | string
const getTeamName = (team: Match["home_team"]): string => {
  if (typeof team === "string") return team;
  return team.name || "Unknown";
};

export default function MatchesPage() {
  const [dateRange, setDateRange] = useState<DateRange>("today");
  const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>([]);
  // Auto-expand today's date by default
  const todayKey = format(startOfDay(new Date()), "yyyy-MM-dd");
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set([todayKey]));

  // Calculate dates based on range
  const today = startOfDay(new Date());
  const dateParams = useMemo(() => {
    let dateFrom = today;
    let dateTo = today;

    switch (dateRange) {
      case "today":
        dateTo = addDays(today, 0);
        break;
      case "tomorrow":
        dateFrom = addDays(today, 1);
        dateTo = addDays(today, 1);
        break;
      case "week":
        dateTo = addDays(today, 6);
        break;
      case "next7days":
        dateTo = addDays(today, 7);
        break;
    }

    return {
      date_from: format(dateFrom, "yyyy-MM-dd"),
      date_to: format(dateTo, "yyyy-MM-dd"),
      competition: selectedCompetitions.length > 0 ? selectedCompetitions[0] : undefined,
    };
  }, [dateRange, selectedCompetitions, today]);

  // Fetch matches using Orval hook
  const { data: response, isLoading, error } = useListMatches(
    dateParams,
    { query: { staleTime: 0, retry: 2 } }
  );

  // Extract matches from response
  const responseData = response as unknown as { data?: MatchListResponse } | undefined;
  const matches = responseData?.data?.matches || [];

  // Filter matches by selected competitions
  const filteredMatches = useMemo(() => {
    if (selectedCompetitions.length === 0) return matches;
    return matches.filter((match) =>
      selectedCompetitions.includes(match.competition_code)
    );
  }, [matches, selectedCompetitions]);

  // Get unique competitions from matches
  const availableCompetitions = useMemo(() => {
    const codes = new Set(matches.map((m) => m.competition_code));
    return Array.from(codes).sort();
  }, [matches]);

  // Group matches by date
  const groupedMatches = useMemo(() => {
    const grouped: Record<string, Match[]> = {};

    filteredMatches.forEach((match) => {
      const date = startOfDay(new Date(match.match_date));
      const dateKey = format(date, "yyyy-MM-dd");

      if (!grouped[dateKey]) {
        grouped[dateKey] = [];
      }
      grouped[dateKey].push(match);
    });

    // Sort dates
    return Object.entries(grouped)
      .sort(([dateA], [dateB]) => dateA.localeCompare(dateB))
      .reduce((acc, [key, value]) => {
        acc[key] = value.sort(
          (a, b) =>
            new Date(a.match_date).getTime() - new Date(b.match_date).getTime()
        );
        return acc;
      }, {} as Record<string, Match[]>);
  }, [filteredMatches]);

  // Toggle competition filter
  const toggleCompetition = (code: string) => {
    setSelectedCompetitions((prev) =>
      prev.includes(code)
        ? prev.filter((c) => c !== code)
        : [...prev, code]
    );
  };

  // Toggle date expansion
  const toggleDate = (dateKey: string) => {
    const newExpanded = new Set(expandedDates);
    if (newExpanded.has(dateKey)) {
      newExpanded.delete(dateKey);
    } else {
      newExpanded.add(dateKey);
    }
    setExpandedDates(newExpanded);
  };

  const datesToDisplay = Object.keys(groupedMatches);

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <section className="text-center py-6 sm:py-8 px-4">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-2 sm:mb-3">Tous les Matchs</h1>
        <p className="text-dark-300 text-sm sm:text-base">
          Explorez les matchs a venir et trouvez les meilleures opportunites de
          paris
        </p>
      </section>

      {/* Filters and Controls */}
      <section className="space-y-3 sm:space-y-4 px-4 sm:px-0">
        {/* Date Range Navigation */}
        <div className="flex flex-wrap gap-2 sm:gap-3">
          {(
            ["today", "tomorrow", "week", "next7days"] as const
          ).map((range) => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={`px-3 sm:px-4 py-2 rounded-lg font-medium text-sm sm:text-base transition-all ${
                dateRange === range
                  ? "bg-primary-500 text-white"
                  : "bg-dark-800 text-dark-300 hover:bg-dark-700"
              }`}
            >
              {range === "today" && "Aujourd'hui"}
              {range === "tomorrow" && "Demain"}
              {range === "week" && "Cette Semaine"}
              {range === "next7days" && "7 Prochains Jours"}
            </button>
          ))}
        </div>

        {/* Competition Filters */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-dark-300">
            <Filter className="w-4 h-4" />
            <span className="text-xs sm:text-sm font-medium">Competitions</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {availableCompetitions.map((code) => (
              <button
                key={code}
                onClick={() => toggleCompetition(code)}
                className={`px-3 sm:px-4 py-1 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  selectedCompetitions.includes(code)
                    ? "bg-primary-500/20 text-primary-300 border border-primary-500"
                    : "bg-dark-800 text-dark-300 border border-dark-700 hover:bg-dark-700"
                }`}
              >
                {competitionLabels[code] || code}
              </button>
            ))}
          </div>

          {/* Clear Filters */}
          {selectedCompetitions.length > 0 && (
            <button
              onClick={() => setSelectedCompetitions([])}
              className="flex items-center gap-1 text-xs sm:text-sm text-primary-400 hover:text-primary-300 transition-colors"
            >
              <X className="w-4 h-4" />
              Effacer les filtres
            </button>
          )}
        </div>
      </section>

      {/* Matches Summary */}
      <section className="flex flex-col sm:flex-row items-start sm:items-center justify-between py-3 sm:py-4 border-b border-dark-700 gap-2 px-4 sm:px-0">
        <div>
          <h2 className="text-base sm:text-lg font-semibold text-white">
            {filteredMatches.length} Match{filteredMatches.length > 1 ? "s" : ""}
          </h2>
          <p className="text-xs sm:text-sm text-dark-400">
            {datesToDisplay.length} jour{datesToDisplay.length > 1 ? "s" : ""}
          </p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
            <span className="text-xs sm:text-sm text-dark-400">Chargement...</span>
          </div>
        )}
      </section>

      {/* Error State */}
      {error ? (
        <section className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 sm:p-8 lg:p-12 text-center mx-4 sm:mx-0">
          <Calendar className="w-10 sm:w-12 h-10 sm:h-12 text-red-400 mx-auto mb-3 sm:mb-4" />
          <h3 className="text-base sm:text-lg font-semibold text-white mb-2">
            Erreur de chargement
          </h3>
          <p className="text-dark-400 mb-3 sm:mb-4 text-sm sm:text-base">
            {error instanceof Error ? error.message : "Impossible de charger les matchs."}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors text-sm"
          >
            Réessayer
          </button>
        </section>
      ) : null}

      {/* Matches List Grouped by Date */}
      {!error ? (
      <section className="space-y-4 sm:space-y-6 px-4 sm:px-0">
        {datesToDisplay.length === 0 ? (
          <div className="text-center py-8 sm:py-12">
            <Calendar className="w-10 sm:w-12 h-10 sm:h-12 text-dark-500 mx-auto mb-3 sm:mb-4" />
            <h3 className="text-base sm:text-lg font-medium text-dark-300 mb-1">
              Aucun match disponible
            </h3>
            <p className="text-dark-400 text-sm">
              Essayez de modifier vos filtres ou de selectionner une autre periode
            </p>
          </div>
        ) : (
          datesToDisplay.map((dateKey) => {
            const date = new Date(dateKey);
            const isToday = isSameDay(date, today);
            const isTomorrow = isSameDay(date, addDays(today, 1));
            const isExpanded = expandedDates.has(dateKey);

            return (
              <div
                key={dateKey}
                className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden"
              >
                {/* Date Header */}
                <button
                  onClick={() => toggleDate(dateKey)}
                  className="w-full flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 hover:bg-dark-700/50 transition-colors"
                >
                  <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                    <Calendar className="w-4 sm:w-5 h-4 sm:h-5 text-primary-400 flex-shrink-0" />
                    <div className="text-left min-w-0">
                      <h3 className="font-semibold text-white text-sm sm:text-base truncate">
                        {format(date, "EEEE d MMMM yyyy", { locale: fr })}
                      </h3>
                      <p className="text-xs sm:text-sm text-dark-400">
                        {isToday && "Aujourd'hui"}
                        {isTomorrow && "Demain"}
                        {!isToday && !isTomorrow && format(date, "EEEE", { locale: fr })}
                        {" • "}
                        {groupedMatches[dateKey].length} match
                        {groupedMatches[dateKey].length > 1 ? "s" : ""}
                      </p>
                    </div>
                  </div>
                  <ChevronDown
                    className={`w-5 h-5 text-dark-400 transition-transform flex-shrink-0 ml-2`}
                    style={{
                      transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)'
                    }}
                  />
                </button>

                {/* Matches for this date */}
                {isExpanded && (
                  <div className="divide-y divide-dark-700">
                    {groupedMatches[dateKey].map((match) => (
                      <MatchCard key={match.id} match={match} />
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </section>
      ) : null}

      {/* Load More Info */}
      {filteredMatches.length > 0 ? (
        <section className="text-center py-6 sm:py-8 px-4">
          <p className="text-dark-400 text-xs sm:text-sm">
            {filteredMatches.length} matchs charges. Les donnees sont mises a
            jour en temps reel.
          </p>
        </section>
      ) : null}
    </div>
  );
}

function MatchCard({ match }: { match: Match }) {
  const matchDate = new Date(match.match_date);
  const homeTeamName = getTeamName(match.home_team);
  const awayTeamName = getTeamName(match.away_team);

  return (
    <Link
      href={`/match/${match.id}`}
      className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 sm:px-6 py-3 sm:py-4 hover:bg-dark-700/30 transition-colors group gap-2 sm:gap-4"
    >
      <div className="flex items-center gap-2 sm:gap-4 flex-1 min-w-0 w-full sm:w-auto">
        {/* Competition indicator */}
        <div
          className={`w-2 sm:w-3 h-8 sm:h-10 rounded-full flex-shrink-0 ${
            competitionColors[match.competition_code] || "bg-dark-500"
          }`}
        />

        {/* Match info */}
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-sm sm:text-base text-white group-hover:text-primary-300 transition-colors break-words">
            {homeTeamName}
            <span className="text-dark-400 mx-1 sm:mx-2">vs</span>
            {awayTeamName}
          </h4>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-xs font-medium text-dark-400 bg-dark-700/50 px-2 py-1 rounded">
              {match.competition}
            </span>
            {match.matchday && (
              <span className="text-xs text-dark-500">
                Journee {match.matchday}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Time and navigation */}
      <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-end">
        <div className="text-right">
          <p className="text-xs sm:text-sm font-medium text-white">
            {format(matchDate, "HH:mm")}
          </p>
          <p className="text-xs text-dark-400">
            {format(matchDate, "EEEE", { locale: fr })}
          </p>
        </div>
        <ChevronRight className="w-4 sm:w-5 h-4 sm:h-5 text-dark-500 group-hover:text-primary-400 transition-colors flex-shrink-0" />
      </div>
    </Link>
  );
}
