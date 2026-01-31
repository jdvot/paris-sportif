"use client";

import { useQuery } from "@tanstack/react-query";
import { TrendingUp, TrendingDown, Minus, Loader2 } from "lucide-react";
import { fetchPredictionStats } from "@/lib/api";

const COMPETITION_NAMES: Record<string, string> = {
  PL: "Premier League",
  PD: "La Liga",
  BL1: "Bundesliga",
  SA: "Serie A",
  FL1: "Ligue 1",
};

export function StatsOverview() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ["predictionStats"],
    queryFn: () => fetchPredictionStats(30),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 text-center">
        <p className="text-dark-400">Impossible de charger les statistiques</p>
      </div>
    );
  }

  // Transform byCompetition data
  const competitionStats = Object.entries(stats.byCompetition || {}).map(
    ([code, data]: [string, any]) => ({
      name: COMPETITION_NAMES[code] || code,
      code,
      predictions: data.total || 0,
      correct: data.correct || 0,
      accuracy: (data.accuracy || 0) * 100,
      trend: data.accuracy >= 0.55 ? "up" : data.accuracy < 0.50 ? "down" : "neutral",
    })
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {/* Overall Stats Card */}
      <div className="md:col-span-2 lg:col-span-1 bg-gradient-to-br from-primary-500/20 to-accent-500/20 border border-primary-500/30 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">
          Performance Globale
        </h3>
        <div className="space-y-4">
          <div>
            <p className="text-dark-400 text-sm">Predictions totales</p>
            <p className="text-3xl font-bold text-white">{stats.totalPredictions}</p>
          </div>
          <div>
            <p className="text-dark-400 text-sm">Predictions correctes</p>
            <p className="text-3xl font-bold text-primary-400">{stats.correctPredictions}</p>
          </div>
          <div>
            <p className="text-dark-400 text-sm">Taux de reussite</p>
            <p className="text-3xl font-bold text-white">
              {((stats.accuracy || 0) * 100).toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-dark-400 text-sm">ROI simule</p>
            <p className="text-3xl font-bold text-primary-400">
              +{((stats.roiSimulated || 0) * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      {/* Per Competition Stats */}
      <div className="md:col-span-2 bg-dark-800/50 border border-dark-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">
          Par Competition
        </h3>
        <div className="space-y-3">
          {competitionStats.length > 0 ? (
            competitionStats.map((stat) => (
              <div
                key={stat.code}
                className="flex items-center justify-between p-3 bg-dark-700/50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="w-2 h-8 bg-primary-500 rounded-full" />
                  <div>
                    <p className="font-medium text-white">{stat.name}</p>
                    <p className="text-xs text-dark-400">
                      {stat.correct}/{stat.predictions} predictions
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-lg font-semibold text-white">
                    {stat.accuracy.toFixed(1)}%
                  </span>
                  {stat.trend === "up" && (
                    <TrendingUp className="w-5 h-5 text-primary-400" />
                  )}
                  {stat.trend === "down" && (
                    <TrendingDown className="w-5 h-5 text-red-400" />
                  )}
                  {stat.trend === "neutral" && (
                    <Minus className="w-5 h-5 text-dark-400" />
                  )}
                </div>
              </div>
            ))
          ) : (
            <p className="text-dark-400 text-center py-4">Aucune donnee disponible</p>
          )}
        </div>
      </div>
    </div>
  );
}
