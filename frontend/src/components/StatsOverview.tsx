"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";

const competitionStats = [
  {
    name: "Premier League",
    code: "PL",
    predictions: 45,
    correct: 28,
    accuracy: 62.2,
    trend: "up",
  },
  {
    name: "La Liga",
    code: "PD",
    predictions: 42,
    correct: 27,
    accuracy: 64.3,
    trend: "up",
  },
  {
    name: "Bundesliga",
    code: "BL1",
    predictions: 38,
    correct: 22,
    accuracy: 57.9,
    trend: "down",
  },
  {
    name: "Serie A",
    code: "SA",
    predictions: 40,
    correct: 26,
    accuracy: 65.0,
    trend: "up",
  },
  {
    name: "Ligue 1",
    code: "FL1",
    predictions: 36,
    correct: 21,
    accuracy: 58.3,
    trend: "neutral",
  },
];

export function StatsOverview() {
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
            <p className="text-3xl font-bold text-white">201</p>
          </div>
          <div>
            <p className="text-dark-400 text-sm">Predictions correctes</p>
            <p className="text-3xl font-bold text-primary-400">124</p>
          </div>
          <div>
            <p className="text-dark-400 text-sm">Taux de reussite</p>
            <p className="text-3xl font-bold text-white">61.7%</p>
          </div>
          <div>
            <p className="text-dark-400 text-sm">ROI simule</p>
            <p className="text-3xl font-bold text-primary-400">+8.2%</p>
          </div>
        </div>
      </div>

      {/* Per Competition Stats */}
      <div className="md:col-span-2 bg-dark-800/50 border border-dark-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">
          Par Competition
        </h3>
        <div className="space-y-3">
          {competitionStats.map((stat) => (
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
                  {stat.accuracy}%
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
          ))}
        </div>
      </div>
    </div>
  );
}
