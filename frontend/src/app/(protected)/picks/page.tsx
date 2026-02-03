"use client";

import { useState, useCallback } from "react";
import { format, subDays, addDays, parseISO } from "date-fns";
import { fr } from "date-fns/locale";
import { AlertTriangle, Calendar } from "lucide-react";
import { cn, isAuthError } from "@/lib/utils";
import { useGetDailyPicks } from "@/lib/api/endpoints/predictions/predictions";
import { PredictionCardPremium } from "@/components/PredictionCardPremium";
import { LoadingState } from "@/components/LoadingState";
import { CompetitionFilter } from "@/components/CompetitionFilter";
import { ExportCSV } from "@/components/ExportCSV";
import { getErrorMessage } from "@/lib/errors";
import type { DailyPick } from "@/lib/api/models";

const COMPETITIONS = [
  { id: "PL", name: "Premier League" },
  { id: "PD", name: "La Liga" },
  { id: "BL1", name: "Bundesliga" },
  { id: "SA", name: "Serie A" },
  { id: "FL1", name: "Ligue 1" },
  { id: "CL", name: "Champions League" },
  { id: "EL", name: "Europa League" },
];

export default function PicksPage() {
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
  const picks = (response?.data as { picks?: DailyPick[] } | undefined)?.picks || [];

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
          Tous les Picks
        </h1>
        <p className="text-gray-600 dark:text-dark-300 text-sm sm:text-base lg:text-lg max-w-2xl mx-auto">
          Consultez l'historique complet de nos predictions avec filtres par
          date et competition. Analysez nos picks en details et suivez leur
          performance.
        </p>
      </section>

      {/* Date Navigation */}
      <section className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6">
          <button
            onClick={handlePreviousDay}
            className="px-3 sm:px-4 py-2 text-gray-600 dark:text-dark-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-700/50 rounded-lg transition-colors text-sm sm:text-base"
          >
            ← Jour precedent
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
              ({format(parseISO(selectedDate), "EEEE", { locale: fr })})
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
            Jour suivant →
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
            Mis a jour: {format(parseISO(selectedDate), "d MMMM yyyy", { locale: fr })}
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
          message="Analyse des matchs en cours..."
        />
      ) : null}

      {/* Error State - Skip for auth errors (global handler will redirect) */}
      {!isLoading && error && !isAuthError(error) ? (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 sm:p-8 lg:p-12 text-center mx-4 sm:mx-0">
          <AlertTriangle className="w-10 sm:w-12 h-10 sm:h-12 text-red-400 mx-auto mb-3 sm:mb-4" />
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Erreur de chargement
          </h3>
          <p className="text-gray-500 dark:text-dark-400 mb-3 sm:mb-4 text-sm sm:text-base">
            {getErrorMessage(error, "Impossible de charger les picks.")}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors text-sm"
          >
            Réessayer
          </button>
        </div>
      ) : null}

      {/* No Results */}
      {!isLoading && !error && filteredPicks.length === 0 ? (
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-8 sm:p-12 text-center mx-4 sm:mx-0">
          <AlertTriangle className="w-10 sm:w-12 h-10 sm:h-12 text-yellow-400 mx-auto mb-3 sm:mb-4" />
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Aucun pick disponible
          </h3>
          <p className="text-gray-500 dark:text-dark-400 text-sm sm:text-base">
            {selectedCompetitions.length > 0
              ? "Aucun pick ne correspond aux competitions selectionnees."
              : "Aucun pick disponible pour cette date."}
          </p>
        </div>
      ) : null}

      {/* Picks Grid */}
      {!isLoading && filteredPicks.length > 0 ? (
        <div className="grid gap-3 sm:gap-4 px-4 sm:px-0">
          {filteredPicks.map((pick, index) => (
            <PredictionCardPremium
              key={pick.rank}
              pick={pick}
              index={index}
              isTopPick={index === 0}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
