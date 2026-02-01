"use client";

import { DailyPicks } from "@/components/DailyPicks";
import { UpcomingMatches } from "@/components/UpcomingMatches";
import { StatsOverview } from "@/components/StatsOverview";
import { TrendingUp, Calendar, Trophy, Loader2 } from "lucide-react";
import { useGetPredictionStats } from "@/lib/api/endpoints/predictions/predictions";

export default function Home() {
  const { data: statsResponse, isLoading: statsLoading } = useGetPredictionStats(
    { days: 30 },
    { query: { staleTime: 5 * 60 * 1000 } }
  );

  // Extract stats data from response - API returns { data: {...}, status: number }
  const stats = statsResponse?.data as { total_predictions?: number; accuracy?: number; by_competition?: Record<string, unknown> } | undefined;

  // Check if stats have actual data (total_predictions > 0 indicates real data)
  const totalPreds = stats?.total_predictions ?? 0;
  const hasData = totalPreds > 0;
  const successRate = hasData ? ((stats?.accuracy || 0) * 100).toFixed(1) : null;
  const totalPredictions = hasData ? totalPreds : null;

  // Count competitions with data
  const competitionsWithData = hasData && stats?.by_competition
    ? Object.keys(stats.by_competition).length
    : null;

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Hero Section */}
      <section className="text-center py-6 sm:py-8">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-3 sm:mb-4">
          Predictions Football IA
        </h1>
        <p className="text-dark-300 text-sm sm:text-base lg:text-lg max-w-2xl mx-auto px-4">
          Analyse statistique avancee combinant modeles Poisson, ELO, xG et
          machine learning pour identifier les meilleures opportunites de paris
          sur le football europeen.
        </p>
      </section>

      {/* Quick Stats - Only show if data is available */}
      {hasData && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 flex flex-col sm:flex-row items-center sm:items-center gap-3 sm:gap-4">
            <div className="p-2 sm:p-3 bg-primary-500/20 rounded-lg flex-shrink-0">
              <TrendingUp className="w-5 sm:w-6 h-5 sm:h-6 text-primary-400" />
            </div>
            <div className="text-center sm:text-left">
              <p className="text-dark-400 text-xs sm:text-sm">Taux de reussite</p>
              {statsLoading ? (
                <Loader2 className="w-5 sm:w-6 h-5 sm:h-6 text-primary-400 animate-spin mt-1 mx-auto sm:mx-0" />
              ) : (
                <p className="text-xl sm:text-2xl font-bold text-white">{successRate}%</p>
              )}
            </div>
          </div>
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 flex flex-col sm:flex-row items-center sm:items-center gap-3 sm:gap-4">
            <div className="p-2 sm:p-3 bg-accent-500/20 rounded-lg flex-shrink-0">
              <Calendar className="w-5 sm:w-6 h-5 sm:h-6 text-accent-400" />
            </div>
            <div className="text-center sm:text-left">
              <p className="text-dark-400 text-xs sm:text-sm">Predictions analysees</p>
              {statsLoading ? (
                <Loader2 className="w-5 sm:w-6 h-5 sm:h-6 text-accent-400 animate-spin mt-1 mx-auto sm:mx-0" />
              ) : (
                <p className="text-xl sm:text-2xl font-bold text-white">{totalPredictions}</p>
              )}
            </div>
          </div>
          <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 flex flex-col sm:flex-row items-center sm:items-center gap-3 sm:gap-4 sm:col-span-2 lg:col-span-1">
            <div className="p-2 sm:p-3 bg-yellow-500/20 rounded-lg flex-shrink-0">
              <Trophy className="w-5 sm:w-6 h-5 sm:h-6 text-yellow-400" />
            </div>
            <div className="text-center sm:text-left">
              <p className="text-dark-400 text-xs sm:text-sm">Championnats couverts</p>
              <p className="text-xl sm:text-2xl font-bold text-white">{competitionsWithData}</p>
            </div>
          </div>
        </section>
      )}

      {/* Daily Picks */}
      <section>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 sm:mb-6 gap-2 sm:gap-0 px-4 sm:px-0">
          <h2 className="text-xl sm:text-2xl font-bold text-white">
            5 Picks du Jour
          </h2>
          <span className="text-dark-400 text-xs sm:text-sm">
            Mis a jour: {new Date().toLocaleDateString("fr-FR")}
          </span>
        </div>
        <DailyPicks />
      </section>

      {/* Upcoming Matches */}
      <section>
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-4 sm:mb-6 px-4 sm:px-0">
          Matchs a Venir
        </h2>
        <UpcomingMatches />
      </section>

      {/* Stats Overview */}
      <section>
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-4 sm:mb-6 px-4 sm:px-0">
          Performance des Predictions
        </h2>
        <StatsOverview />
      </section>
    </div>
  );
}
