"use client";

import { useQuery } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { format, subDays, addDays, parseISO } from "date-fns";
import { fr } from "date-fns/locale";
import { TrendingUp, AlertTriangle, CheckCircle, Calendar, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchDailyPicks } from "@/lib/api";
import type { DailyPick } from "@/lib/types";

// Mock data for development
const mockPicks: DailyPick[] = [
  {
    rank: 1,
    match: {
      id: 1,
      homeTeam: "Manchester City",
      awayTeam: "Arsenal",
      competition: "Premier League",
      matchDate: new Date().toISOString(),
    },
    prediction: {
      homeProb: 0.52,
      drawProb: 0.26,
      awayProb: 0.22,
      recommendedBet: "home",
      confidence: 0.72,
      valueScore: 0.08,
    },
    explanation:
      "City en excellente forme a domicile avec 8 victoires consecutives. Arsenal fatigue apres le match de Ligue des Champions.",
    keyFactors: [
      "8 victoires consecutives a domicile",
      "Arsenal en deplacement difficile",
      "Avantage xG significatif",
    ],
  },
  {
    rank: 2,
    match: {
      id: 2,
      homeTeam: "Real Madrid",
      awayTeam: "Barcelona",
      competition: "La Liga",
      matchDate: new Date().toISOString(),
    },
    prediction: {
      homeProb: 0.41,
      drawProb: 0.29,
      awayProb: 0.30,
      recommendedBet: "home",
      confidence: 0.65,
      valueScore: 0.12,
    },
    explanation:
      "El Clasico au Bernabeu. Real favori leger avec l'avantage du terrain.",
    keyFactors: [
      "Bernabeu en feu",
      "Vinicius Jr en forme",
      "Barcelona sans Pedri",
    ],
  },
  {
    rank: 3,
    match: {
      id: 3,
      homeTeam: "Bayern Munich",
      awayTeam: "Dortmund",
      competition: "Bundesliga",
      matchDate: new Date().toISOString(),
    },
    prediction: {
      homeProb: 0.58,
      drawProb: 0.24,
      awayProb: 0.18,
      recommendedBet: "home",
      confidence: 0.78,
      valueScore: 0.06,
    },
    explanation: "Der Klassiker avec Bayern dominant a domicile cette saison.",
    keyFactors: [
      "Bayern invaincu a domicile",
      "Dortmund instable",
      "Historique favorable",
    ],
  },
  {
    rank: 4,
    match: {
      id: 4,
      homeTeam: "PSG",
      awayTeam: "Marseille",
      competition: "Ligue 1",
      matchDate: new Date().toISOString(),
    },
    prediction: {
      homeProb: 0.62,
      drawProb: 0.22,
      awayProb: 0.16,
      recommendedBet: "home",
      confidence: 0.75,
      valueScore: 0.09,
    },
    explanation:
      "Le Classique au Parc des Princes. PSG ultra-favori malgre absence de Mbappe.",
    keyFactors: ["Parc des Princes", "Domination historique", "OM en crise"],
  },
  {
    rank: 5,
    match: {
      id: 5,
      homeTeam: "Inter Milan",
      awayTeam: "Juventus",
      competition: "Serie A",
      matchDate: new Date().toISOString(),
    },
    prediction: {
      homeProb: 0.45,
      drawProb: 0.30,
      awayProb: 0.25,
      recommendedBet: "home",
      confidence: 0.62,
      valueScore: 0.07,
    },
    explanation: "Derby d'Italie. Match serre attendu avec leger avantage Inter.",
    keyFactors: [
      "San Siro plein",
      "Inter en tete",
      "Juventus defensive solide",
    ],
  },
];

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

  const { data: picks = mockPicks, isLoading } = useQuery({
    queryKey: ["dailyPicks", selectedDate],
    queryFn: () => fetchDailyPicks(selectedDate),
    enabled: true,
    initialData: mockPicks,
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
    <div className="space-y-6">
      {/* Header Section */}
      <section className="text-center py-8">
        <h1 className="text-4xl font-bold text-white mb-4">
          Tous les Picks
        </h1>
        <p className="text-dark-300 text-lg max-w-2xl mx-auto">
          Consultez l'historique complet de nos predictions avec filtres par
          date et competition. Analysez nos picks en details et suivez leur
          performance.
        </p>
      </section>

      {/* Date Navigation */}
      <section className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
        <div className="flex items-center justify-center gap-6">
          <button
            onClick={handlePreviousDay}
            className="px-4 py-2 text-dark-300 hover:text-white hover:bg-dark-700/50 rounded-lg transition-colors"
          >
            ← Jour precedent
          </button>

          <div className="flex items-center gap-3">
            <Calendar className="w-5 h-5 text-primary-400" />
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="bg-dark-700 border border-dark-600 text-white px-4 py-2 rounded-lg focus:outline-none focus:border-primary-500"
            />
            <span className="text-dark-400 text-sm">
              ({format(parseISO(selectedDate), "EEEE", { locale: fr })})
            </span>
          </div>

          <button
            onClick={handleNextDay}
            disabled={!canGoNext}
            className={cn(
              "px-4 py-2 rounded-lg transition-colors",
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
      <section>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 px-4 py-2 mb-4 bg-dark-800/50 border border-dark-700 hover:border-dark-600 text-white rounded-lg transition-colors"
        >
          <Filter className="w-4 h-4" />
          <span>Filtres par competition</span>
          <span className={cn(
            "ml-auto transition-transform",
            showFilters && "rotate-180"
          )}>
            ▼
          </span>
        </button>

        {showFilters && (
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 mb-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {COMPETITIONS.map((comp) => (
                <button
                  key={comp.id}
                  onClick={() => toggleCompetition(comp.id)}
                  className={cn(
                    "px-4 py-2 rounded-lg font-medium transition-all duration-200",
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
                className="mt-4 text-sm text-primary-400 hover:text-primary-300 transition-colors"
              >
                Reinitialiser les filtres
              </button>
            )}
          </div>
        )}
      </section>

      {/* Results Info */}
      <section className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">
          {filteredPicks.length} Pick{filteredPicks.length !== 1 ? "s" : ""}
          {selectedCompetitions.length > 0 && (
            <span className="text-sm text-dark-400 ml-2">
              ({selectedCompetitions.join(", ")})
            </span>
          )}
        </h2>
        <span className="text-dark-400 text-sm">
          Mis a jour: {format(parseISO(selectedDate), "d MMMM yyyy", { locale: fr })}
        </span>
      </section>

      {/* Loading State */}
      {isLoading && (
        <div className="grid gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 animate-pulse"
            >
              <div className="h-6 bg-dark-700 rounded w-1/3 mb-4" />
              <div className="h-4 bg-dark-700 rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* No Results */}
      {!isLoading && filteredPicks.length === 0 && (
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-12 text-center">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">
            Aucun pick disponible
          </h3>
          <p className="text-dark-400">
            {selectedCompetitions.length > 0
              ? "Aucun pick ne correspond aux competitions selectionnees."
              : "Aucun pick disponible pour cette date."}
          </p>
        </div>
      )}

      {/* Picks Grid */}
      {!isLoading && filteredPicks.length > 0 && (
        <div className="grid gap-4">
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

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden hover:border-dark-600 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700">
        <div className="flex items-center gap-4">
          <span className="flex items-center justify-center w-8 h-8 bg-primary-500 rounded-full text-white font-bold text-sm">
            {pick.rank}
          </span>
          <div>
            <h3 className="font-semibold text-white">
              {match.homeTeam} vs {match.awayTeam}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm text-dark-400">{match.competition}</span>
              <span className="text-xs text-dark-500">•</span>
              <span className="text-xs text-dark-400">
                {format(matchDate, "d MMM, HH:mm", { locale: fr })}
              </span>
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className={cn("font-semibold", confidenceColor)}>
            {Math.round(prediction.confidence * 100)}% confiance
          </p>
          <p className="text-sm text-dark-400">
            Value: +{Math.round(prediction.valueScore * 100)}%
          </p>
        </div>
      </div>

      {/* Body */}
      <div className="px-6 py-4">
        {/* Probabilities */}
        <div className="flex gap-2 mb-4">
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

        {/* Recommendation */}
        <div className={cn(
          "flex items-center gap-2 mb-4 p-3 border rounded-lg",
          confidenceBgColor
        )}>
          <CheckCircle className={cn("w-5 h-5", confidenceColor)} />
          <span className={cn("font-medium", confidenceColor)}>{betLabel}</span>
        </div>

        {/* Explanation */}
        <p className="text-dark-300 text-sm mb-4">{explanation}</p>

        {/* Key Factors */}
        {keyFactors.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-semibold text-dark-300 mb-2">
              Points positifs:
            </p>
            <div className="flex flex-wrap gap-2">
              {keyFactors.map((factor, i) => (
                <span
                  key={i}
                  className="px-2 py-1 bg-primary-500/20 border border-primary-500/30 rounded text-xs text-primary-300"
                >
                  +{factor}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Risk Factors */}
        {riskFactors && riskFactors.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-dark-300 mb-2">
              Risques:
            </p>
            <div className="flex flex-wrap gap-2">
              {riskFactors.map((factor, i) => (
                <span
                  key={i}
                  className="px-2 py-1 bg-orange-500/20 border border-orange-500/30 rounded text-xs text-orange-300"
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
  return (
    <div className="flex-1">
      <div className="flex justify-between text-xs mb-1">
        <span className={isRecommended ? "text-primary-400" : "text-dark-400"}>
          {label.length > 12 ? label.slice(0, 12) + "..." : label}
        </span>
        <span className={isRecommended ? "text-primary-400" : "text-dark-400"}>
          {Math.round(prob * 100)}%
        </span>
      </div>
      <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
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
