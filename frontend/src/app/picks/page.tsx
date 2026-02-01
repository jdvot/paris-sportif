"use client";

import { useQuery } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { format, subDays, addDays, parseISO } from "date-fns";
import { fr } from "date-fns/locale";
import { TrendingUp, AlertTriangle, CheckCircle, Calendar, Filter, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchDailyPicks } from "@/lib/api";
import type { DailyPick } from "@/lib/types";

const COMPETITIONS = [
  { id: "PL", name: "Premier League" },
  { id: "PD", name: "La Liga" },
  { id: "BL1", name: "Bundesliga" },
  { id: "SA", name: "Serie A" },
  { id: "FL1", name: "Ligue 1" },
  { id: "CL", name: "Champions League" },
  { id: "EL", name: "Europa League" },
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

export default function PicksPage() {
  const [selectedDate, setSelectedDate] = useState<string>(
    format(new Date(), "yyyy-MM-dd")
  );
  const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  const { data: picks = [], isLoading, error } = useQuery({
    queryKey: ["dailyPicks", selectedDate],
    queryFn: () => fetchDailyPicks(selectedDate),
    enabled: true,
    staleTime: 0, // Always fetch fresh data from API
    retry: 2,
  });

  const filteredPicks = picks.filter((pick) => {
    if (selectedCompetitions.length === 0) return true;
    return selectedCompetitions.some(
      (comp) =>
        pick.match.competition
          .toLowerCase()
          .includes(comp.toLowerCase()) ||
        COMPETITIONS.find(
          (c) => c.id === comp && c.name === pick.match.competition
        )
    );
  });

  const toggleCompetition = useCallback((competitionId: string) => {
    setSelectedCompetitions((prev) =>
      prev.includes(competitionId)
        ? prev.filter((c) => c !== competitionId)
        : [...prev, competitionId]
    );
  }, []);

  const handlePreviousDay = () => {
    setSelectedDate(format(subDays(parseISO(selectedDate), 1), "yyyy-MM-dd"));
  };

  const handleNextDay = () => {
    const nextDay = format(addDays(parseISO(selectedDate), 1), "yyyy-MM-dd");
    if (nextDay <= format(new Date(), "yyyy-MM-dd")) {
      setSelectedDate(nextDay);
    }
  };

  const canGoNext = selectedDate < format(new Date(), "yyyy-MM-dd");

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header Section */}
      <section className="text-center py-6 sm:py-8 px-4">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-3 sm:mb-4">
          Tous les Picks
        </h1>
        <p className="text-dark-300 text-sm sm:text-base lg:text-lg max-w-2xl mx-auto">
          Consultez l'historique complet de nos predictions avec filtres par
          date et competition. Analysez nos picks en details et suivez leur
          performance.
        </p>
      </section>

      {/* Date Navigation */}
      <section className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6">
          <button
            onClick={handlePreviousDay}
            className="px-3 sm:px-4 py-2 text-dark-300 hover:text-white hover:bg-dark-700/50 rounded-lg transition-colors text-sm sm:text-base"
          >
            ← Jour precedent
          </button>

          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-3 w-full sm:w-auto">
            <Calendar className="w-5 h-5 text-primary-400 flex-shrink-0" />
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="bg-dark-700 border border-dark-600 text-white px-3 sm:px-4 py-2 rounded-lg focus:outline-none focus:border-primary-500 text-sm flex-1 sm:flex-none"
            />
            <span className="text-dark-400 text-xs sm:text-sm">
              ({format(parseISO(selectedDate), "EEEE", { locale: fr })})
            </span>
          </div>

          <button
            onClick={handleNextDay}
            disabled={!canGoNext}
            className={cn(
              "px-3 sm:px-4 py-2 rounded-lg transition-colors text-sm sm:text-base",
              canGoNext
                ? "text-dark-300 hover:text-white hover:bg-dark-700/50"
                : "text-dark-600 cursor-not-allowed"
            )}
          >
            Jour suivant →
          </button>
        </div>
      </section>

      {/* Filter Section */}
      <section className="px-4 sm:px-0">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 px-4 py-2 mb-4 bg-dark-800/50 border border-dark-700 hover:border-dark-600 text-white rounded-lg transition-colors w-full sm:w-auto text-sm sm:text-base"
        >
          <Filter className="w-4 h-4 flex-shrink-0" />
          <span>Filtres par competition</span>
          <span className={cn(
            "ml-auto transition-transform flex-shrink-0",
            showFilters && "rotate-180"
          )}>
            ▼
          </span>
        </button>

        {showFilters && (
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 mb-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-3">
              {COMPETITIONS.map((comp) => (
                <button
                  key={comp.id}
                  onClick={() => toggleCompetition(comp.id)}
                  className={cn(
                    "px-3 sm:px-4 py-2 rounded-lg font-medium transition-all duration-200 text-sm",
                    selectedCompetitions.includes(comp.id)
                      ? "bg-primary-500 text-white border border-primary-400"
                      : "bg-dark-700 text-dark-300 border border-dark-600 hover:border-dark-500"
                  )}
                >
                  {comp.name}
                </button>
              ))}
            </div>

            {selectedCompetitions.length > 0 && (
              <button
                onClick={() => setSelectedCompetitions([])}
                className="mt-4 text-xs sm:text-sm text-primary-400 hover:text-primary-300 transition-colors"
              >
                Reinitialiser les filtres
              </button>
            )}
          </div>
        )}
      </section>

      {/* Results Info */}
      <section className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-4 sm:px-0">
        <h2 className="text-lg sm:text-2xl font-bold text-white">
          {filteredPicks.length} Pick{filteredPicks.length !== 1 ? "s" : ""}
          {selectedCompetitions.length > 0 && (
            <span className="text-xs sm:text-sm text-dark-400 ml-2 block sm:inline">
              ({selectedCompetitions.join(", ")})
            </span>
          )}
        </h2>
        <span className="text-dark-400 text-xs sm:text-sm">
          Mis a jour: {format(parseISO(selectedDate), "d MMMM yyyy", { locale: fr })}
        </span>
      </section>

      {/* Loading State */}
      {isLoading && (
        <div className="grid gap-3 sm:gap-4 px-4 sm:px-0">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 animate-pulse"
            >
              <div className="h-5 sm:h-6 bg-dark-700 rounded w-1/3 mb-3 sm:mb-4" />
              <div className="h-4 bg-dark-700 rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {!isLoading && error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 sm:p-8 lg:p-12 text-center mx-4 sm:mx-0">
          <AlertTriangle className="w-10 sm:w-12 h-10 sm:h-12 text-red-400 mx-auto mb-3 sm:mb-4" />
          <h3 className="text-base sm:text-lg font-semibold text-white mb-2">
            Erreur de chargement
          </h3>
          <p className="text-dark-400 mb-3 sm:mb-4 text-sm sm:text-base">
            {error instanceof Error ? error.message : "Impossible de charger les picks."}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors text-sm"
          >
            Réessayer
          </button>
        </div>
      )}

      {/* No Results */}
      {!isLoading && !error && filteredPicks.length === 0 && (
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8 sm:p-12 text-center mx-4 sm:mx-0">
          <AlertTriangle className="w-10 sm:w-12 h-10 sm:h-12 text-yellow-400 mx-auto mb-3 sm:mb-4" />
          <h3 className="text-base sm:text-lg font-semibold text-white mb-2">
            Aucun pick disponible
          </h3>
          <p className="text-dark-400 text-sm sm:text-base">
            {selectedCompetitions.length > 0
              ? "Aucun pick ne correspond aux competitions selectionnees."
              : "Aucun pick disponible pour cette date."}
          </p>
        </div>
      )}

      {/* Picks Grid */}
      {!isLoading && filteredPicks.length > 0 && (
        <div className="grid gap-3 sm:gap-4 px-4 sm:px-0">
          {filteredPicks.map((pick) => (
            <PickCard key={pick.rank} pick={pick} />
          ))}
        </div>
      )}
    </div>
  );
}

function PickCard({ pick }: { pick: DailyPick }) {
  const { match, prediction, keyFactors, explanation, riskFactors } = pick;

  const betLabels: Record<string, string> = {
    home: `Victoire ${match.homeTeam}`,
    home_win: `Victoire ${match.homeTeam}`,
    draw: "Match nul",
    away: `Victoire ${match.awayTeam}`,
    away_win: `Victoire ${match.awayTeam}`,
  };
  const betLabel = betLabels[prediction.recommendedBet] || prediction.recommendedBet;

  // Shorter labels for mobile
  const shortBetLabels: Record<string, string> = {
    home: match.homeTeam.split(' ')[0],
    home_win: match.homeTeam.split(' ')[0],
    draw: "Nul",
    away: match.awayTeam.split(' ')[0],
    away_win: match.awayTeam.split(' ')[0],
  };
  const shortBetLabel = shortBetLabels[prediction.recommendedBet] || prediction.recommendedBet;

  const confidenceColor =
    prediction.confidence >= 0.7
      ? "text-primary-400"
      : prediction.confidence >= 0.6
      ? "text-yellow-400"
      : "text-orange-400";

  const confidenceBgColor =
    prediction.confidence >= 0.7
      ? "bg-primary-500/10 border-primary-500/30"
      : prediction.confidence >= 0.6
      ? "bg-yellow-500/10 border-yellow-500/30"
      : "bg-orange-500/10 border-orange-500/30";

  const matchDate = new Date(match.matchDate);

  // Truncate team name for mobile
  const truncateTeam = (name: string, maxLen: number = 10) => {
    if (name.length <= maxLen) return name;
    return name.slice(0, maxLen) + "…";
  };

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden hover:border-dark-600 transition-colors">
      {/* Header - Mobile optimized */}
      <div className="px-3 sm:px-6 py-3 sm:py-4 border-b border-dark-700">
        {/* Mobile: Stacked layout */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2 sm:gap-4 min-w-0 flex-1">
            <span className="flex items-center justify-center w-6 sm:w-8 h-6 sm:h-8 bg-primary-500 rounded-full text-white font-bold text-[10px] sm:text-sm flex-shrink-0 mt-0.5">
              {pick.rank}
            </span>
            <div className="min-w-0 flex-1">
              {/* Mobile: Show abbreviated team names */}
              <h3 className="font-semibold text-white leading-tight">
                <span className="hidden sm:inline text-base">{match.homeTeam} vs {match.awayTeam}</span>
                <span className="sm:hidden text-sm">{truncateTeam(match.homeTeam)} vs {truncateTeam(match.awayTeam)}</span>
              </h3>
              <div className="flex items-center gap-1.5 sm:gap-2 mt-1 flex-wrap text-[10px] sm:text-sm">
                <span className="text-dark-400">{match.competition}</span>
                <span className="text-dark-500">•</span>
                <span className="text-dark-400">
                  {format(matchDate, "d MMM, HH:mm", { locale: fr })}
                </span>
              </div>
            </div>
          </div>
          {/* Confidence badge - compact on mobile */}
          <div className="text-right flex-shrink-0">
            <p className={cn("font-bold text-sm sm:text-base", confidenceColor)}>
              {Math.round(prediction.confidence * 100)}%
            </p>
            <p className="text-[10px] sm:text-xs text-dark-400">
              +{Math.round(prediction.valueScore * 100)}% value
            </p>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="px-3 sm:px-6 py-3 sm:py-4 space-y-2.5 sm:space-y-4">
        {/* Probabilities - optimized gap for mobile */}
        <div className="flex gap-1.5 sm:gap-2">
          <ProbBar
            label={match.homeTeam}
            prob={prediction.homeProb ?? prediction.probabilities?.homeWin ?? 0}
            isRecommended={prediction.recommendedBet === "home" || prediction.recommendedBet === "home_win"}
          />
          <ProbBar
            label="Nul"
            prob={prediction.drawProb ?? prediction.probabilities?.draw ?? 0}
            isRecommended={prediction.recommendedBet === "draw"}
          />
          <ProbBar
            label={match.awayTeam}
            prob={prediction.awayProb ?? prediction.probabilities?.awayWin ?? 0}
            isRecommended={prediction.recommendedBet === "away" || prediction.recommendedBet === "away_win"}
          />
        </div>

        {/* Recommendation - compact on mobile */}
        <div className={cn(
          "flex items-center gap-2 p-2 sm:p-3 border rounded-lg",
          confidenceBgColor
        )}>
          <CheckCircle className={cn("w-4 sm:w-5 h-4 sm:h-5 flex-shrink-0", confidenceColor)} />
          <span className={cn("font-medium text-xs sm:text-sm", confidenceColor)}>
            <span className="hidden sm:inline">{betLabel}</span>
            <span className="sm:hidden">{shortBetLabel}</span>
          </span>
        </div>

        {/* Explanation - slightly smaller on mobile */}
        <p className="text-dark-300 text-[11px] sm:text-sm leading-relaxed">{explanation}</p>

        {/* Key Factors - compact tags on mobile */}
        {keyFactors.length > 0 && (
          <div>
            <p className="text-[10px] sm:text-xs font-semibold text-dark-300 mb-1.5 sm:mb-2">
              Points positifs:
            </p>
            <div className="flex flex-wrap gap-1 sm:gap-2">
              {keyFactors.map((factor, i) => (
                <span
                  key={i}
                  className="px-1.5 sm:px-2 py-0.5 sm:py-1 bg-primary-500/20 border border-primary-500/30 rounded text-[10px] sm:text-xs text-primary-300"
                >
                  +{factor}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Risk Factors - compact tags on mobile */}
        {riskFactors && riskFactors.length > 0 && (
          <div>
            <p className="text-[10px] sm:text-xs font-semibold text-dark-300 mb-1.5 sm:mb-2">
              Risques:
            </p>
            <div className="flex flex-wrap gap-1 sm:gap-2">
              {riskFactors.map((factor, i) => (
                <span
                  key={i}
                  className="px-1.5 sm:px-2 py-0.5 sm:py-1 bg-orange-500/20 border border-orange-500/30 rounded text-[10px] sm:text-xs text-orange-300"
                >
                  -{factor}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ProbBar({
  label,
  prob,
  isRecommended,
}: {
  label: string;
  prob: number;
  isRecommended: boolean;
}) {
  // Smart truncation - show first word or abbreviate
  const getShortLabel = (name: string) => {
    if (name === "Nul") return name;
    if (name.length <= 8) return name;
    // Try to get meaningful abbreviation
    const firstWord = name.split(' ')[0];
    if (firstWord.length <= 8) return firstWord;
    return name.slice(0, 7) + "…";
  };

  return (
    <div className="flex-1 min-w-0">
      <div className="flex justify-between text-[10px] sm:text-xs mb-1 gap-1">
        <span className={cn(
          "truncate",
          isRecommended ? "text-primary-400 font-medium" : "text-dark-400"
        )}>
          <span className="hidden sm:inline">{label.length > 12 ? label.slice(0, 12) + "…" : label}</span>
          <span className="sm:hidden">{getShortLabel(label)}</span>
        </span>
        <span className={cn(
          "flex-shrink-0 font-medium",
          isRecommended ? "text-primary-400" : "text-dark-400"
        )}>
          {Math.round(prob * 100)}%
        </span>
      </div>
      <div className="h-1.5 sm:h-2 bg-dark-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            isRecommended ? "bg-primary-500" : "bg-dark-500"
          )}
          style={{ width: `${prob * 100}%` }}
        />
      </div>
    </div>
  );
}
