"use client";

import { useMemo } from "react";
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
import { Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useGetPredictionStats } from "@/lib/api/endpoints/predictions/predictions";
import { cn } from "@/lib/utils";
import { ROUNDED_TOP } from "@/lib/recharts-types";

const COMPETITION_NAMES: Record<string, string> = {
  PL: "Premier League",
  PD: "La Liga",
  BL1: "Bundesliga",
  SA: "Serie A",
  FL1: "Ligue 1",
};

interface HistoryDataPoint {
  date: string;
  accuracy: number;
  predictions: number;
  cumulative: number;
}

interface CompetitionChartData {
  name: string;
  predictions: number;
  correct: number;
  accuracy: number;
}

export function PerformanceHistory() {
  const t = useTranslations("stats");
  // locale is available via useLocale() if needed for date formatting
  const { data: response, isLoading, error } = useGetPredictionStats(
    { days: 30 },
    { query: { staleTime: 5 * 60 * 1000 } } // 5 minutes
  );

  // Extract stats from Orval response (status 200 returns data)
  const stats = response?.status === 200 ? response.data : null;

  // NOTE: Historical daily data requires backend API endpoint to track predictions per day
  // Removed simulated data - see PAR-172 for implementation with real daily stats
  const historyData = useMemo((): HistoryDataPoint[] => {
    // Return empty array until backend provides real daily breakdown
    return [];
  }, []);

  // Memoize competition chart data with proper types
  const competitionData = useMemo((): CompetitionChartData[] => {
    if (!stats) return [];
    return Object.entries(stats.by_competition || {})
      .map(([code, data]: [string, Record<string, unknown>]) => ({
        name: COMPETITION_NAMES[code] || code,
        predictions: (data.total as number) || (data.predictions as number) || 0,
        correct: (data.correct as number) || 0,
        accuracy: (data.accuracy as number) || 0,
      }))
      .filter((comp) => comp.predictions > 0)
      .sort((a, b) => b.predictions - a.predictions);
  }, [stats]);

  // Memoize ROI calculation
  const roiAmount = useMemo(() => {
    if (!stats) return 0;
    return stats.roi_simulated ? stats.roi_simulated * stats.total_predictions * 10 : 0;
  }, [stats]);

  // Memoize stat cards data
  const statCards = useMemo(() => {
    if (!stats) return [];
    return [
      {
        label: t("totalPredictions"),
        value: stats.total_predictions.toString(),
        subtext: `${stats.correct_predictions} ${t("correct")}`,
        color: "from-primary-500/20 to-primary-600/20",
        borderColor: "border-primary-500/30",
      },
      {
        label: t("successRate"),
        value: `${(stats.accuracy || 0).toFixed(1)}%`,
        subtext: `+${((stats.accuracy || 0) - 50).toFixed(1)}% ${t("vsBaseline")}`,
        color: "from-accent-500/20 to-accent-600/20",
        borderColor: "border-accent-500/30",
      },
      {
        label: t("roiSimulated"),
        value: `${((stats.roi_simulated || 0) * 100).toFixed(1)}%`,
        subtext: `+${Math.round(roiAmount)}€ ${t("profit")}`,
        color: "from-green-500/20 to-green-600/20",
        borderColor: "border-green-500/30",
      },
    ];
  }, [t, stats, roiAmount]);

  const COLORS = useMemo(() => ["#4ade80", "#60a5fa", "#fbbf24", "#f87171", "#a78bfa"], []);

  // Conditional returns AFTER all hooks are called
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
        <p className="text-dark-400">{t("loadErrorHistory")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 px-4 sm:px-0">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        {statCards.map((card, idx) => (
          <div
            key={idx}
            className={cn(
              "bg-gradient-to-br p-4 sm:p-6 rounded-xl border",
              card.color,
              card.borderColor
            )}
          >
            <p className="text-dark-400 text-xs sm:text-sm mb-2">{card.label}</p>
            <p className="text-2xl sm:text-3xl font-bold text-white mb-1">{card.value}</p>
            <p className="text-xs sm:text-sm text-dark-300">{card.subtext}</p>
          </div>
        ))}
      </div>

      {/* Accuracy Over Time Chart - Requires real daily data from backend */}
      {historyData.length > 0 ? (
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-4">
            {t("accuracyOverTime")}
          </h3>
          <div className="w-full h-64 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="date"
                  stroke="#94a3b8"
                  style={{ fontSize: "0.75rem" }}
                  tick={{ fill: "#94a3b8" }}
                />
                <YAxis
                  stroke="#94a3b8"
                  style={{ fontSize: "0.75rem" }}
                  tick={{ fill: "#94a3b8" }}
                  label={{ value: `${t("precision")} (%)`, angle: -90, position: "insideLeft" }}
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                  formatter={(value: number) => {
                    return `${value.toFixed(1)}%`;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#4ade80"
                  strokeWidth={3}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : null}

      {/* Predictions per Competition Chart */}
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-semibold text-white mb-4">
          {t("predictionsByCompetition")}
        </h3>
        <div className="w-full h-64 sm:h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={competitionData} margin={{ top: 5, right: 10, left: -20, bottom: 40 }}>
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
                formatter={(value: number, name: string) => {
                  if (name === "accuracy") return `${value.toFixed(1)}%`;
                  return value;
                }}
              />
              <Legend wrapperStyle={{ paddingTop: "20px" }} />
              <Bar dataKey="predictions" fill="#4ade80" name={t("predictions")} radius={ROUNDED_TOP}>
                {competitionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
              <Bar dataKey="correct" fill="#60a5fa" name={t("correctLabel")} radius={ROUNDED_TOP} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          {competitionData.slice(0, 3).map((comp) => (
            <div key={comp.name} className="bg-dark-700/50 p-3 rounded-lg">
              <p className="text-dark-400 text-xs mb-1">{comp.name}</p>
              <p className="text-white font-semibold">{comp.accuracy.toFixed(1)}%</p>
              <p className="text-xs text-dark-300">{comp.correct}/{comp.predictions}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
