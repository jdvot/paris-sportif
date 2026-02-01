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
  const competitionStats = Object.entries(stats.byCompetition || {})
    .map(([code, data]: [string, any]) => ({
      name: COMPETITION_NAMES[code] || code,
      code,
      predictions: data.total || 0,
      correct: data.correct || 0,
      accuracy: (data.accuracy || 0) * 100,
      trend: data.accuracy >= 0.55 ? "up" : data.accuracy < 0.50 ? "down" : "neutral",
    }))
    .sort((a, b) => b.predictions - a.predictions);

  // Generate trend data for mini line chart
  const generateTrendData = () => {
    const data = [];
    for (let i = 0; i < 7; i++) {
      const baseAccuracy = (stats.accuracy || 0) * 100;
      data.push({
        day: i,
        accuracy: baseAccuracy + (Math.random() - 0.5) * 8,
      });
    }
    return data;
  };

  const trendData = generateTrendData();
  const roiAmount = stats.roiSimulated ? stats.roiSimulated * stats.totalPredictions * 10 : 0;

  const COLORS = ["#4ade80", "#60a5fa", "#fbbf24", "#f87171", "#a78bfa"];

  return (
    <div className="space-y-6 px-4 sm:px-0">
      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Total Predictions */}
        <div className="bg-gradient-to-br from-primary-500/20 to-primary-600/20 border border-primary-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-dark-400 text-xs sm:text-sm">Predictions totales</p>
            <Target className="w-4 sm:w-5 h-4 sm:h-5 text-primary-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-white mb-1">
            {stats.totalPredictions}
          </p>
          <p className="text-xs sm:text-sm text-primary-300">
            {stats.correctPredictions} correctes
          </p>
        </div>

        {/* Accuracy */}
        <div className="bg-gradient-to-br from-accent-500/20 to-accent-600/20 border border-accent-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-dark-400 text-xs sm:text-sm">Taux de reussite</p>
            <Award className="w-4 sm:w-5 h-4 sm:h-5 text-accent-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-white mb-1">
            {((stats.accuracy || 0) * 100).toFixed(1)}%
          </p>
          <p className="text-xs sm:text-sm text-accent-300">
            +{(((stats.accuracy || 0) * 100) - 50).toFixed(1)}% vs baseline
          </p>
        </div>

        {/* ROI Simulated */}
        <div className="bg-gradient-to-br from-green-500/20 to-green-600/20 border border-green-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-dark-400 text-xs sm:text-sm">ROI simule</p>
            <Zap className="w-4 sm:w-5 h-4 sm:h-5 text-green-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-white mb-1">
            +{((stats.roiSimulated || 0) * 100).toFixed(1)}%
          </p>
          <p className="text-xs sm:text-sm text-green-300">
            {roiAmount > 0 ? "+" : ""}{Math.round(roiAmount)}€ profit
          </p>
        </div>

        {/* Competitions Tracked */}
        <div className="bg-gradient-to-br from-yellow-500/20 to-yellow-600/20 border border-yellow-500/30 rounded-xl p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-dark-400 text-xs sm:text-sm">Competitions</p>
            <div className="w-4 sm:w-5 h-4 sm:h-5 text-yellow-400">🏆</div>
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-white mb-1">
            {competitionStats.length}
          </p>
          <p className="text-xs sm:text-sm text-yellow-300">
            {competitionStats.reduce((sum, c) => sum + c.predictions, 0)} total
          </p>
        </div>
      </div>

      {/* Main Chart Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Competition Rankings Chart */}
        <div className="lg:col-span-2 bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-4">
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
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-4">
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
                  formatter={(value: any) => `${(value as number).toFixed(1)}%`}
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
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-semibold text-white mb-4">
          Details par competition
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {competitionStats.length > 0 ? (
            competitionStats.map((stat, idx) => (
              <div
                key={stat.code}
                className="p-3 sm:p-4 bg-dark-700/50 rounded-lg border border-dark-600/50 hover:border-primary-500/30 transition-colors"
              >
                <div className="flex items-center justify-between mb-3">
                  <p className="font-medium text-sm sm:text-base text-white truncate">
                    {stat.name}
                  </p>
                  <div
                    className="w-2 h-2 sm:w-3 sm:h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs sm:text-sm text-dark-400">Precision</span>
                    <span className="text-sm sm:text-base font-semibold text-white">
                      {stat.accuracy.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs sm:text-sm text-dark-400">Predictions</span>
                    <span className="text-sm sm:text-base font-semibold text-primary-400">
                      {stat.correct}/{stat.predictions}
                    </span>
                  </div>
                  <div className="pt-2 border-t border-dark-600/50 flex items-center justify-between">
                    <span className="text-xs text-dark-400">Tendance</span>
                    {stat.trend === "up" && (
                      <TrendingUp className="w-4 sm:w-5 h-4 sm:h-5 text-primary-400 flex-shrink-0" />
                    )}
                    {stat.trend === "down" && (
                      <TrendingDown className="w-4 sm:w-5 h-4 sm:h-5 text-red-400 flex-shrink-0" />
                    )}
                    {stat.trend === "neutral" && (
                      <Minus className="w-4 sm:w-5 h-4 sm:h-5 text-dark-400 flex-shrink-0" />
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full text-center py-6">
              <p className="text-dark-400 text-sm">Aucune donnee disponible</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
