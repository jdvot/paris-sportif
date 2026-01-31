"use client";

import { useQuery } from "@tanstack/react-query";
import { TrendingUp, AlertTriangle, CheckCircle } from "lucide-react";
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

export function DailyPicks() {
  // In production, this would fetch from the API
  const { data: picks = mockPicks, isLoading } = useQuery({
    queryKey: ["dailyPicks"],
    queryFn: () => fetchDailyPicks(),
    // Use mock data in development
    enabled: false,
    initialData: mockPicks,
  });

  if (isLoading) {
    return (
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
    );
  }

  return (
    <div className="grid gap-4">
      {picks.map((pick) => (
        <PickCard key={pick.rank} pick={pick} />
      ))}
    </div>
  );
}

function PickCard({ pick }: { pick: DailyPick }) {
  const { match, prediction, keyFactors, explanation } = pick;

  const betLabel = {
    home: `Victoire ${match.homeTeam}`,
    draw: "Match nul",
    away: `Victoire ${match.awayTeam}`,
  }[prediction.recommendedBet];

  const confidenceColor =
    prediction.confidence >= 0.7
      ? "text-primary-400"
      : prediction.confidence >= 0.6
      ? "text-yellow-400"
      : "text-orange-400";

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden hover:border-dark-600 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700">
        <div className="flex items-center gap-4">
          <span className="flex items-center justify-center w-8 h-8 bg-primary-500 rounded-full text-white font-bold">
            {pick.rank}
          </span>
          <div>
            <h3 className="font-semibold text-white">
              {match.homeTeam} vs {match.awayTeam}
            </h3>
            <p className="text-sm text-dark-400">{match.competition}</p>
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
            prob={prediction.homeProb}
            isRecommended={prediction.recommendedBet === "home"}
          />
          <ProbBar
            label="Nul"
            prob={prediction.drawProb}
            isRecommended={prediction.recommendedBet === "draw"}
          />
          <ProbBar
            label={match.awayTeam}
            prob={prediction.awayProb}
            isRecommended={prediction.recommendedBet === "away"}
          />
        </div>

        {/* Recommendation */}
        <div className="flex items-center gap-2 mb-4 p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg">
          <CheckCircle className="w-5 h-5 text-primary-400" />
          <span className="font-medium text-primary-400">{betLabel}</span>
        </div>

        {/* Explanation */}
        <p className="text-dark-300 text-sm mb-4">{explanation}</p>

        {/* Key Factors */}
        <div className="flex flex-wrap gap-2">
          {keyFactors.map((factor, i) => (
            <span
              key={i}
              className="px-2 py-1 bg-dark-700 rounded text-xs text-dark-300"
            >
              {factor}
            </span>
          ))}
        </div>
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
