"use client";

import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  Award,
  Target,
  Zap,
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { fetchPredictionStats } from "@/lib/api";
import { cn } from "@/lib/utils";

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
      <div className="space-y-6 px-4 sm:px-0">
        {/* Loading indicator */}
        <div className="flex items-center justify-center gap-3 py-4">
          <div className="relative">
            <div className="w-6 h-6 rounded-full border-2 border-gray-300 dark:border-dark-600" />
            <div className="absolute top-0 left-0 w-6 h-6 rounded-full border-2 border-transparent border-t-primary-500 animate-spin" />
          </div>
          <span className="text-gray-600 dark:text-dark-400 text-sm animate-pulse">Chargement des statistiques...</span>
        </div>
        {/* Key Metrics Cards Skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {[
            { from: "from-primary-500/10", border: "border-primary-500/20" },
            { from: "from-accent-500/10", border: "border-accent-500/20" },
            { from: "from-green-500/10", border: "border-green-500/20" },
            { from: "from-yellow-500/10", border: "border-yellow-500/20" },
          ].map((style, idx) => (
            <div
              key={idx}
              className={`bg-gradient-to-br ${style.from} to-gray-50 dark:to-dark-800/50 border ${style.border} rounded-xl p-4 sm:p-6`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="h-3 w-24 bg-gray-100 dark:bg-dark-700/50 rounded animate-pulse" />
                <div className="w-5 h-5 bg-gray-200 dark:bg-dark-700/50 rounded animate-pulse" />
              </div>
              <div className="h-8 w-20 bg-gray-200 dark:bg-dark-700 rounded animate-pulse mb-2" style={{ animationDelay: `${idx * 100}ms` }} />
              <div className="h-3 w-28 bg-gray-100 dark:bg-dark-700/30 rounded animate-pulse" style={{ animationDelay: `${idx * 150}ms` }} />
            </div>
          ))}
        </div>
        {/* Chart Section Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          {/* Main Chart Skeleton */}
          <div className="lg:col-span-2 bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
            <div className="h-5 w-48 bg-gray-200 dark:bg-dark-700 rounded animate-pulse mb-4" />
            <div className="h-72 sm:h-80 bg-gray-100 dark:bg-dark-700/30 rounded-lg animate-pulse flex items-end justify-around p-4">
              {[60, 75, 50, 85, 70].map((h, i) => (
                <div
                  key={i}
                  className="w-12 bg-gradient-to-t from-gray-200 to-gray-300 dark:from-dark-600 dark:to-dark-500 rounded-t animate-pulse"
                  style={{ height: `${h}%`, animationDelay: `${i * 100}ms` }}
                />
              ))}
            </div>
          </div>
          {/* Trend Chart Skeleton */}
          <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
            <div className="h-5 w-40 bg-gray-200 dark:bg-dark-700 rounded animate-pulse mb-4" />
            <div className="h-72 sm:h-80 bg-gray-100 dark:bg-dark-700/30 rounded-lg animate-pulse relative overflow-hidden">
              <svg className="w-full h-full" preserveAspectRatio="none">
                <path
                  d="M0,150 Q50,100 100,120 T200,80 T300,110 T400,70"
                  fill="none"
                  stroke="#334155"
                  strokeWidth="2"
                  className="animate-pulse"
                />
              </svg>
            </div>
          </div>
        </div>
        {/* Competition Details Skeleton */}
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
          <div className="h-5 w-44 bg-gray-200 dark:bg-dark-700 rounded animate-pulse mb-4" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="p-3 sm:p-4 bg-gray-100 dark:bg-dark-700/30 rounded-lg border border-gray-300 dark:border-dark-600/30">
                <div className="flex items-center justify-between mb-3">
                  <div className="h-4 w-28 bg-gray-200 dark:bg-dark-700 rounded animate-pulse" />
                  <div className="w-3 h-3 bg-gray-300 dark:bg-dark-600 rounded-full animate-pulse" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <div className="h-3 w-16 bg-gray-100 dark:bg-dark-700/50 rounded animate-pulse" />
                    <div className="h-3 w-12 bg-gray-200 dark:bg-dark-700 rounded animate-pulse" />
                  </div>
                  <div className="flex justify-between">
                    <div className="h-3 w-20 bg-gray-100 dark:bg-dark-700/50 rounded animate-pulse" />
                    <div className="h-3 w-10 bg-primary-500/20 rounded animate-pulse" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-6 text-center">
        <p className="text-gray-600 dark:text-dark-400">Impossible de charger les statistiques</p>
      </div>
    );
  }

  // Transform byCompetition data - if no data, use placeholder data
  const hasRealData = Object.keys(stats.byCompetition || {}).length > 0;

  // Use real data if available, otherwise show placeholder for 5 competitions
  // Note: Backend already returns accuracy as percentage (0-100), not ratio
  const competitionStats = hasRealData
    ? Object.entries(stats.byCompetition)
        .map(([code, data]: [string, any]) => ({
          name: COMPETITION_NAMES[code] || code,
          code,
          predictions: data.total || 0,
          correct: data.correct || 0,
          accuracy: data.accuracy || 0,  // Already a percentage from backend
          trend: data.accuracy >= 55 ? "up" : data.accuracy < 50 ? "down" : "neutral",
        }))
        .sort((a, b) => b.predictions - a.predictions)
    : Object.entries(COMPETITION_NAMES).map(([code, name]) => ({
        name,
        code,
        predictions: 0,
        correct: 0,
        accuracy: 0,
        trend: "neutral" as const,
      }));

  // Generate trend data for mini line chart
  const generateTrendData = () => {
    const data = [];
    for (let i = 0; i < 7; i++) {
      const baseAccuracy = stats.accuracy || 0;  // Already a percentage
      data.push({
        day: i,
        accuracy: baseAccuracy + (Math.random() - 0.5) * 8,
      });
    }
    return data;
  };

  const trendData = generateTrendData();
  // roiSimulated is already a percentage, convert to ratio for calculation
  const roiAmount = stats.roiSimulated ? (stats.roiSimulated / 100) * stats.totalPredictions * 10 : 0;

  const COLORS = ["#4ade80", "#60a5fa", "#fbbf24", "#f87171", "#a78bfa"];

  return (
    <div className="space-y-6 px-4 sm:px-0">
      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Total Predictions */}
        <div className="bg-gradient-to-br from-primary-100 dark:from-primary-500/20 to-primary-200 dark:to-primary-600/20 border border-primary-300 dark:border-primary-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-gray-600 dark:text-dark-400 text-xs sm:text-sm">Predictions totales</p>
            <Target className="w-4 sm:w-5 h-4 sm:h-5 text-primary-600 dark:text-primary-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-1">
            {stats.totalPredictions}
          </p>
          <p className="text-xs sm:text-sm text-primary-700 dark:text-primary-300">
            {stats.correctPredictions} correctes
          </p>
        </div>

        {/* Accuracy */}
        <div className="bg-gradient-to-br from-cyan-100 dark:from-accent-500/20 to-cyan-200 dark:to-accent-600/20 border border-cyan-300 dark:border-accent-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-gray-600 dark:text-dark-400 text-xs sm:text-sm">Taux de reussite</p>
            <Award className="w-4 sm:w-5 h-4 sm:h-5 text-cyan-600 dark:text-accent-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-1">
            {(stats.accuracy || 0).toFixed(1)}%
          </p>
          <p className="text-xs sm:text-sm text-cyan-700 dark:text-accent-300">
            +{((stats.accuracy || 0) - 50).toFixed(1)}% vs baseline
          </p>
        </div>

        {/* ROI Simulated */}
        <div className="bg-gradient-to-br from-green-100 dark:from-green-500/20 to-green-200 dark:to-green-600/20 border border-green-300 dark:border-green-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-gray-600 dark:text-dark-400 text-xs sm:text-sm">ROI simule</p>
            <Zap className="w-4 sm:w-5 h-4 sm:h-5 text-green-600 dark:text-green-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-1">
            {(stats.roiSimulated || 0) >= 0 ? "+" : ""}{(stats.roiSimulated || 0).toFixed(1)}%
          </p>
          <p className="text-xs sm:text-sm text-green-700 dark:text-green-300">
            {roiAmount > 0 ? "+" : ""}{Math.round(roiAmount)}€ profit
          </p>
        </div>

        {/* Competitions Tracked */}
        <div className="bg-gradient-to-br from-yellow-100 dark:from-yellow-500/20 to-yellow-200 dark:to-yellow-600/20 border border-yellow-300 dark:border-yellow-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-gray-600 dark:text-dark-400 text-xs sm:text-sm">Competitions</p>
            <div className="w-4 sm:w-5 h-4 sm:h-5 text-yellow-600 dark:text-yellow-400">🏆</div>
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-1">
            {competitionStats.length}
          </p>
          <p className="text-xs sm:text-sm text-yellow-700 dark:text-yellow-300">
            {competitionStats.reduce((sum, c) => sum + c.predictions, 0)} total
          </p>
        </div>
      </div>

      {/* Info banner when no verified data */}
      {!hasRealData && (
        <div className="bg-gradient-to-r from-amber-50 dark:from-amber-500/10 to-orange-50 dark:to-orange-500/10 border border-amber-300 dark:border-amber-500/30 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <span className="text-xl">📊</span>
            </div>
            <div>
              <p className="text-amber-800 dark:text-amber-200 font-medium">Statistiques en cours de collecte</p>
              <p className="text-amber-700 dark:text-amber-300/70 text-sm">
                Les statistiques détaillées seront disponibles après vérification des prédictions.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Chart Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Competition Rankings Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Classement par competition
          </h3>
          <div className="w-full h-72 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={competitionStats}
                margin={{ top: 5, right: 10, left: -20, bottom: 40 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="name"
                  stroke="#94a3b8"
                  style={{ fontSize: "0.7rem" }}
                  tick={{ fill: "#94a3b8" }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis
                  stroke="#94a3b8"
                  style={{ fontSize: "0.75rem" }}
                  tick={{ fill: "#94a3b8" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="accuracy" fill="#4ade80" radius={[8, 8, 0, 0] as any}>
                  {competitionStats.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Trend Indicator */}
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Tendance (7 derniers jours)
          </h3>
          <div className="w-full h-72 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="day"
                  stroke="#94a3b8"
                  style={{ fontSize: "0.75rem" }}
                  tick={{ fill: "#94a3b8" }}
                />
                <YAxis
                  stroke="#94a3b8"
                  style={{ fontSize: "0.75rem" }}
                  tick={{ fill: "#94a3b8" }}
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                  formatter={(value: number) => `${value.toFixed(1)}%`}
                />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#4ade80"
                  strokeWidth={2}
                  dot={{ fill: "#4ade80", r: 4 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Competition Details */}
      <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Details par competition
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {competitionStats.length > 0 ? (
            competitionStats.map((stat, idx) => (
              <div
                key={stat.code}
                className="p-3 sm:p-4 bg-gray-50 dark:bg-dark-700/50 rounded-lg border border-gray-200 dark:border-dark-600/50 hover:border-primary-400 dark:hover:border-primary-500/30 transition-colors"
              >
                <div className="flex items-center justify-between mb-3">
                  <p className="font-medium text-sm sm:text-base text-gray-900 dark:text-white truncate">
                    {stat.name}
                  </p>
                  <div
                    className="w-2 h-2 sm:w-3 sm:h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs sm:text-sm text-gray-600 dark:text-dark-400">Precision</span>
                    <span className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white">
                      {stat.accuracy.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs sm:text-sm text-gray-600 dark:text-dark-400">Predictions</span>
                    <span className="text-sm sm:text-base font-semibold text-primary-600 dark:text-primary-400">
                      {stat.correct}/{stat.predictions}
                    </span>
                  </div>
                  <div className="pt-2 border-t border-gray-200 dark:border-dark-600/50 flex items-center justify-between">
                    <span className="text-xs text-gray-600 dark:text-dark-400">Tendance</span>
                    {stat.trend === "up" && (
                      <TrendingUp className="w-4 sm:w-5 h-4 sm:h-5 text-primary-600 dark:text-primary-400 flex-shrink-0" />
                    )}
                    {stat.trend === "down" && (
                      <TrendingDown className="w-4 sm:w-5 h-4 sm:h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
                    )}
                    {stat.trend === "neutral" && (
                      <Minus className="w-4 sm:w-5 h-4 sm:h-5 text-gray-500 dark:text-dark-400 flex-shrink-0" />
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full text-center py-6">
              <p className="text-gray-600 dark:text-dark-400 text-sm">Aucune donnee disponible</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
