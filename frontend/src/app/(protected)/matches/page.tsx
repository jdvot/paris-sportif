"use client";

import { useState, useMemo } from "react";
import {
  Calendar,
  ChevronRight,
  Filter,
  X,
  ChevronDown,
  CheckCircle2,
} from "lucide-react";
import Link from "next/link";
import { format, startOfDay, addDays, isSameDay, startOfWeek, endOfWeek } from "date-fns";
import { fr, enUS, type Locale } from "date-fns/locale";
import { useTranslations, useLocale } from "next-intl";
import { useGetMatches } from "@/lib/api/endpoints/matches/matches";
import type { MatchResponse, MatchListResponse } from "@/lib/api/models";
import { LoadingState } from "@/components/LoadingState";
import { isAuthError } from "@/lib/utils";

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
const getTeamName = (team: MatchResponse["home_team"]): string => {
  if (typeof team === "string") return team;
  return team.name || "Unknown";
};

export default function MatchesPage() {
  const t = useTranslations("matches");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const dateLocale = locale === "fr" ? fr : enUS;
  const [dateRange, setDateRange] = useState<DateRange>("week");
  const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>([]);
  const [showFinished, setShowFinished] = useState<boolean>(true);
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
        // Cette Semaine = lundi → dimanche de la semaine actuelle
        dateFrom = startOfWeek(today, { weekStartsOn: 1 }); // Lundi
        dateTo = endOfWeek(today, { weekStartsOn: 1 }); // Dimanche
        break;
      case "next7days":
        dateTo = addDays(today, 7);
        break;
    }

    return {
      date_from: format(dateFrom, "yyyy-MM-dd"),
      date_to: format(dateTo, "yyyy-MM-dd"),
      per_page: 100, // Fetch more matches to avoid pagination issues
      // Competition filtering is done client-side to support multi-select
    };
  }, [dateRange, today]);

  // Fetch matches using Orval hook
  const { data: response, isLoading, error } = useGetMatches(
    dateParams,
    { query: { staleTime: 0, retry: 2 } }
  );

  // Extract matches from response - API returns { data: { matches: [...] }, status: number }
  const matches = (response?.data as MatchListResponse | undefined)?.matches || [];

  // Filter matches by selected competitions and status
  const filteredMatches = useMemo(() => {
    let result = matches;

    // Filter by status (finished or not)
    if (!showFinished) {
      result = result.filter((match) => match.status !== "finished");
    }

    // Filter by competition
    if (selectedCompetitions.length > 0) {
      result = result.filter((match) =>
        selectedCompetitions.includes(match.competition_code)
      );
    }

    return result;
  }, [matches, selectedCompetitions, showFinished]);

  // Get unique competitions from matches
  const availableCompetitions = useMemo(() => {
    const codes = new Set(matches.map((m) => m.competition_code));
    return Array.from(codes).sort();
  }, [matches]);

  // Group matches by date
  const groupedMatches = useMemo(() => {
    const grouped: Record<string, MatchResponse[]> = {};

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
      }, {} as Record<string, MatchResponse[]>);
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
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 dark:text-white mb-2 sm:mb-3">{t("title")}</h1>
        <p className="text-gray-600 dark:text-slate-300 text-sm sm:text-base">
          {t("subtitle")}
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
                  : "bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700"
              }`}
            >
              {range === "today" && t("filters.today")}
              {range === "tomorrow" && t("filters.tomorrow")}
              {range === "week" && t("filters.thisWeek")}
              {range === "next7days" && t("filters.next7Days")}
            </button>
          ))}
        </div>

        {/* Competition Filters */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-gray-600 dark:text-slate-300">
            <Filter className="w-4 h-4" />
            <span className="text-xs sm:text-sm font-medium">{t("filters.competition")}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {availableCompetitions.map((code) => (
              <button
                key={code}
                onClick={() => toggleCompetition(code)}
                className={`px-3 sm:px-4 py-1 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  selectedCompetitions.includes(code)
                    ? "bg-primary-500/20 text-primary-600 dark:text-primary-300 border border-primary-500"
                    : "bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-700 hover:bg-gray-200 dark:hover:bg-slate-700"
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
              {t("filters.clearFilters")}
            </button>
          )}
        </div>

        {/* Show Finished Matches Toggle */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer group">
            <div className="relative">
              <input
                type="checkbox"
                checked={showFinished}
                onChange={(e) => setShowFinished(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-5 h-5 border-2 border-gray-400 dark:border-slate-500 rounded bg-gray-100 dark:bg-slate-800 peer-checked:bg-primary-500 peer-checked:border-primary-500 transition-all">
                {showFinished && (
                  <CheckCircle2 className="w-4 h-4 text-white absolute top-0.5 left-0.5" />
                )}
              </div>
            </div>
            <span className="text-xs sm:text-sm text-gray-600 dark:text-slate-300 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
              {t("filters.includeFinished")}
            </span>
          </label>
        </div>
      </section>

      {/* Matches Summary */}
      <section className="flex flex-col sm:flex-row items-start sm:items-center justify-between py-3 sm:py-4 border-b border-gray-200 dark:border-slate-700 gap-2 px-4 sm:px-0">
        <div>
          <h2 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
            {filteredMatches.length} {t("matchCount", { count: filteredMatches.length })}
          </h2>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-slate-400">
            {datesToDisplay.length} {t("dayCount", { count: datesToDisplay.length })}
          </p>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
            <span className="text-xs sm:text-sm text-gray-500 dark:text-slate-400">{tCommon("loading")}</span>
          </div>
        )}
      </section>

      {/* Error State - Skip for auth errors (global handler will redirect) */}
      {error && !isAuthError(error) ? (
        <section className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 sm:p-8 lg:p-12 text-center mx-4 sm:mx-0">
          <Calendar className="w-10 sm:w-12 h-10 sm:h-12 text-red-400 mx-auto mb-3 sm:mb-4" />
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {tCommon("errorLoading")}
          </h3>
          <p className="text-gray-500 dark:text-slate-400 mb-3 sm:mb-4 text-sm sm:text-base">
            {error instanceof Error ? error.message : t("loadError")}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors text-sm"
          >
            {tCommon("retry")}
          </button>
        </section>
      ) : null}

      {/* Matches List Grouped by Date */}
      {!error || isAuthError(error) ? (
      <section className="space-y-4 sm:space-y-6 px-4 sm:px-0">
        {datesToDisplay.length === 0 ? (
          <div className="text-center py-8 sm:py-12">
            <Calendar className="w-10 sm:w-12 h-10 sm:h-12 text-gray-400 dark:text-slate-500 mx-auto mb-3 sm:mb-4" />
            <h3 className="text-base sm:text-lg font-medium text-gray-600 dark:text-slate-300 mb-1">
              {t("empty")}
            </h3>
            <p className="text-gray-500 dark:text-slate-400 text-sm">
              {t("emptyHint")}
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
                className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden"
              >
                {/* Date Header */}
                <button
                  onClick={() => toggleDate(dateKey)}
                  className="w-full flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
                >
                  <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                    <Calendar className="w-4 sm:w-5 h-4 sm:h-5 text-primary-400 flex-shrink-0" />
                    <div className="text-left min-w-0">
                      <h3 className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base truncate">
                        {format(date, "EEEE d MMMM yyyy", { locale: dateLocale })}
                      </h3>
                      <p className="text-xs sm:text-sm text-gray-500 dark:text-slate-400">
                        {isToday && t("filters.today")}
                        {isTomorrow && t("filters.tomorrow")}
                        {!isToday && !isTomorrow && format(date, "EEEE", { locale: dateLocale })}
                        {" • "}
                        {groupedMatches[dateKey].length} {t("matchCount", { count: groupedMatches[dateKey].length })}
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
                  <div className="divide-y divide-gray-200 dark:divide-slate-700">
                    {groupedMatches[dateKey].map((match) => (
                      <MatchCard key={match.id} match={match} dateLocale={dateLocale} />
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
          <p className="text-gray-500 dark:text-slate-400 text-xs sm:text-sm">
            {t("loadedInfo", { count: filteredMatches.length })}
          </p>
        </section>
      ) : null}
    </div>
  );
}

function MatchCard({ match, dateLocale }: { match: MatchResponse; dateLocale: Locale }) {
  const t = useTranslations("matches");
  const matchDate = new Date(match.match_date);
  const homeTeamName = getTeamName(match.home_team);
  const awayTeamName = getTeamName(match.away_team);
  const isFinished = match.status === "finished";

  return (
    <Link
      href={`/match/${match.id}`}
      className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 sm:px-6 py-3 sm:py-4 hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors group gap-2 sm:gap-4"
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
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-semibold text-sm sm:text-base text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-300 transition-colors">
              {homeTeamName}
            </h4>
            {isFinished && match.home_score !== null && match.away_score !== null ? (
              <span className="text-sm sm:text-base font-bold text-primary-400">
                {match.home_score} - {match.away_score}
              </span>
            ) : (
              <span className="text-gray-500 dark:text-slate-400 text-sm">vs</span>
            )}
            <h4 className="font-semibold text-sm sm:text-base text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-300 transition-colors">
              {awayTeamName}
            </h4>
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-xs font-medium text-gray-600 dark:text-slate-400 bg-gray-100 dark:bg-slate-700/50 px-2 py-1 rounded">
              {match.competition}
            </span>
            {match.matchday && (
              <span className="text-xs text-gray-500 dark:text-slate-500">
                {t("matchday", { day: match.matchday })}
              </span>
            )}
            {isFinished && (
              <span className="text-xs font-medium text-emerald-400 bg-emerald-500/20 px-2 py-1 rounded">
                {t("finished")}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Time and navigation */}
      <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-end">
        <div className="text-right">
          <p className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white">
            {format(matchDate, "HH:mm")}
          </p>
          <p className="text-xs text-gray-500 dark:text-slate-400">
            {format(matchDate, "EEEE", { locale: dateLocale })}
          </p>
        </div>
        <ChevronRight className="w-4 sm:w-5 h-4 sm:h-5 text-gray-400 dark:text-slate-500 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors flex-shrink-0" />
      </div>
    </Link>
  );
}
