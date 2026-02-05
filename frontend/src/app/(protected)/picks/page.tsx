"use client";

import { useState, useCallback } from "react";
import { format, subDays, addDays, parseISO } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { AlertTriangle, Calendar } from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { cn, isAuthError } from "@/lib/utils";
import { useGetDailyPicks } from "@/lib/api/endpoints/predictions/predictions";
import { PredictionCardPremium } from "@/components/PredictionCardPremium";
import { LoadingState } from "@/components/LoadingState";
import { CompetitionFilter } from "@/components/CompetitionFilter";
import { ExportCSV } from "@/components/ExportCSV";
import { NewsFeed } from "@/components/NewsFeed";
import { getErrorMessage } from "@/lib/errors";
import type { DailyPickResponse } from "@/lib/api/models";
import { COMPETITIONS as COMPETITIONS_DATA } from "@/lib/constants";

// Map centralized competitions to the format used by CompetitionFilter
const COMPETITIONS = COMPETITIONS_DATA.map(c => ({ id: c.code, name: c.name }));

export default function PicksPage() {
  const t = useTranslations("picks");
  const tCommon = useTranslations("common");
  const tDailyPicks = useTranslations("dailyPicks");
  const locale = useLocale();
  const dateLocale = locale === "fr" ? fr : enUS;
  const [selectedDate, setSelectedDate] = useState<string>(
    format(new Date(), "yyyy-MM-dd")
  );
  const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  const { data: response, isLoading, error } = useGetDailyPicks(
    { date: selectedDate },
    { query: { staleTime: 0, retry: 2 } }
  );

  // Extract picks from response - API returns { data: { picks: [...] }, status: number }
  const picks = (response?.data as { picks?: DailyPickResponse[] } | undefined)?.picks || [];

  const filteredPicks = picks.filter((pick) => {
    if (selectedCompetitions.length === 0) return true;
    // Get competition from prediction (snake_case from API)
    const pred = pick.prediction as unknown as { competition?: string };
    const predCompetition = pred?.competition || "";
    return selectedCompetitions.some((compId) => {
      const competition = COMPETITIONS.find((c) => c.id === compId);
      if (!competition) return false;
      return (
        predCompetition === competition.name ||
        predCompetition.toLowerCase().includes(competition.name.toLowerCase()) ||
        predCompetition.includes(compId)
      );
    });
  });

  const toggleCompetition = useCallback((competitionId: string) => {
    setSelectedCompetitions((prev) =>
      prev.includes(competitionId)
        ? prev.filter((c) => c !== competitionId)
        : [...prev, competitionId]
    );
  }, []);

  // Allow navigation up to 7 days in the future
  const MAX_FUTURE_DAYS = 7;

  const handlePreviousDay = () => {
    setSelectedDate(format(subDays(parseISO(selectedDate), 1), "yyyy-MM-dd"));
  };

  const handleNextDay = () => {
    const nextDay = format(addDays(parseISO(selectedDate), 1), "yyyy-MM-dd");
    const maxDate = format(addDays(new Date(), MAX_FUTURE_DAYS), "yyyy-MM-dd");
    if (nextDay <= maxDate) {
      setSelectedDate(nextDay);
    }
  };

  const canGoNext = selectedDate < format(addDays(new Date(), MAX_FUTURE_DAYS), "yyyy-MM-dd");

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header Section */}
      <section className="text-center py-6 sm:py-8 px-4">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 dark:text-white mb-3 sm:mb-4">
          {t("allPicks")}
        </h1>
        <p className="text-gray-600 dark:text-dark-300 text-sm sm:text-base lg:text-lg max-w-2xl mx-auto">
          {t("allPicksDescription")}
        </p>
      </section>

      {/* Date Navigation */}
      <section className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6">
          <button
            onClick={handlePreviousDay}
            className="px-3 sm:px-4 py-2 text-gray-600 dark:text-dark-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-700/50 rounded-lg transition-colors text-sm sm:text-base"
          >
            ← {t("navigation.previousDay")}
          </button>

          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-3 w-full sm:w-auto">
            <Calendar className="w-5 h-5 text-primary-400 flex-shrink-0" />
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              max={format(addDays(new Date(), MAX_FUTURE_DAYS), "yyyy-MM-dd")}
              className="bg-gray-100 dark:bg-dark-700 border border-gray-300 dark:border-dark-600 text-gray-900 dark:text-white px-3 sm:px-4 py-2 rounded-lg focus:outline-none focus:border-primary-500 text-sm flex-1 sm:flex-none"
            />
            <span className="text-gray-500 dark:text-dark-400 text-xs sm:text-sm">
              ({format(parseISO(selectedDate), "EEEE", { locale: dateLocale })})
            </span>
          </div>

          <button
            onClick={handleNextDay}
            disabled={!canGoNext}
            className={cn(
              "px-3 sm:px-4 py-2 rounded-lg transition-colors text-sm sm:text-base",
              canGoNext
                ? "text-gray-600 dark:text-dark-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-700/50"
                : "text-gray-400 dark:text-dark-600 cursor-not-allowed"
            )}
          >
            {t("navigation.nextDay")} →
          </button>
        </div>
      </section>

      {/* Filter Section */}
      <section className="px-4 sm:px-0">
        <CompetitionFilter
          competitions={COMPETITIONS}
          selected={selectedCompetitions}
          onToggle={toggleCompetition}
          onClear={() => setSelectedCompetitions([])}
          isOpen={showFilters}
          onToggleOpen={() => setShowFilters(!showFilters)}
        />
      </section>

      {/* Results Info */}
      <section className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-4 sm:px-0">
        <h2 className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white">
          {filteredPicks.length} Pick{filteredPicks.length !== 1 ? "s" : ""}
          {selectedCompetitions.length > 0 && (
            <span className="text-xs sm:text-sm text-gray-500 dark:text-dark-400 ml-2 block sm:inline">
              ({selectedCompetitions.join(", ")})
            </span>
          )}
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-gray-500 dark:text-dark-400 text-xs sm:text-sm">
            {t("updatedOn")}: {format(parseISO(selectedDate), "d MMMM yyyy", { locale: dateLocale })}
          </span>
          <ExportCSV
            picks={filteredPicks}
            filename={`picks-${selectedDate}`}
            variant="icon"
          />
        </div>
      </section>

      {/* Loading State */}
      {isLoading ? (
        <LoadingState
          variant="picks"
          count={5}
          message={tDailyPicks("loading")}
        />
      ) : null}

      {/* Error State - Skip for auth errors (global handler will redirect) */}
      {!isLoading && error && !isAuthError(error) ? (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 sm:p-8 lg:p-12 text-center mx-4 sm:mx-0">
          <AlertTriangle className="w-10 sm:w-12 h-10 sm:h-12 text-red-400 mx-auto mb-3 sm:mb-4" />
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {tCommon("errorLoading")}
          </h3>
          <p className="text-gray-500 dark:text-dark-400 mb-3 sm:mb-4 text-sm sm:text-base">
            {getErrorMessage(error, tDailyPicks("loadError"))}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors text-sm"
          >
            {tCommon("retry")}
          </button>
        </div>
      ) : null}

      {/* No Results */}
      {!isLoading && !error && filteredPicks.length === 0 ? (
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-8 sm:p-12 text-center mx-4 sm:mx-0">
          <AlertTriangle className="w-10 sm:w-12 h-10 sm:h-12 text-yellow-400 mx-auto mb-3 sm:mb-4" />
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {t("empty")}
          </h3>
          <p className="text-gray-500 dark:text-dark-400 text-sm sm:text-base">
            {selectedCompetitions.length > 0
              ? t("emptyFiltered")
              : t("emptyDate")}
          </p>
        </div>
      ) : null}

      {/* Picks Grid + News Feed */}
      {!isLoading && filteredPicks.length > 0 ? (
        <div className="grid lg:grid-cols-3 gap-4 sm:gap-6 px-4 sm:px-0">
          {/* Main Picks Column */}
          <div className="lg:col-span-2 grid gap-3 sm:gap-4">
            {filteredPicks.map((pick, index) => (
              <PredictionCardPremium
                key={pick.rank}
                pick={pick}
                index={index}
                isTopPick={index === 0}
              />
            ))}
          </div>

          {/* News Sidebar */}
          <div className="lg:col-span-1">
            <div className="sticky top-4">
              <NewsFeed limit={8} />
            </div>
          </div>
        </div>
      ) : null}

      {/* News Feed when no picks */}
      {!isLoading && filteredPicks.length === 0 && !error ? (
        <div className="px-4 sm:px-0">
          <NewsFeed limit={10} />
        </div>
      ) : null}
    </div>
  );
}
