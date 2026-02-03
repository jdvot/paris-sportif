"use client";

import { useEffect } from "react";
import { Flame, Trophy, Target, TrendingUp, Zap, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { useStreak } from "@/hooks/useStreak";
import { useAchievements } from "@/hooks/useAchievements";
import { Achievements } from "@/components/Achievements";

interface StreakTrackerProps {
  variant?: "compact" | "full";
  className?: string;
}

export function StreakTracker({ variant = "compact", className }: StreakTrackerProps) {
  const { currentStreak, bestStreak, totalWins, totalLosses, winRate, history, isLoaded } = useStreak();
  const { checkStreakAchievements, isLoaded: achievementsLoaded } = useAchievements();

  // Check achievements when streak data changes
  useEffect(() => {
    if (isLoaded && achievementsLoaded && history.length > 0) {
      checkStreakAchievements({
        currentStreak,
        bestStreak,
        totalWins,
        totalLosses,
        history: history.map((h) => ({ won: h.won, date: h.date })),
      });
    }
  }, [isLoaded, achievementsLoaded, currentStreak, bestStreak, totalWins, totalLosses, history, checkStreakAchievements]);

  if (!isLoaded) {
    return (
      <div className={cn("animate-pulse bg-gray-200 dark:bg-dark-700 rounded-lg h-20", className)} />
    );
  }

  // Milestone badges
  const getMilestoneBadge = (streak: number) => {
    if (streak >= 10) return { label: "Legendaire", color: "text-yellow-400", bg: "bg-yellow-500/20" };
    if (streak >= 7) return { label: "Expert", color: "text-purple-400", bg: "bg-purple-500/20" };
    if (streak >= 5) return { label: "Pro", color: "text-blue-400", bg: "bg-blue-500/20" };
    if (streak >= 3) return { label: "En Feu", color: "text-orange-400", bg: "bg-orange-500/20" };
    return null;
  };

  const milestone = getMilestoneBadge(currentStreak);

  if (variant === "compact") {
    return (
      <div
        className={cn(
          "flex items-center gap-3 p-3 rounded-lg",
          "bg-gradient-to-r from-orange-100 dark:from-orange-500/10 to-yellow-100 dark:to-yellow-500/10",
          "border border-orange-200 dark:border-orange-500/30",
          className
        )}
      >
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-full bg-orange-500/20">
            <Flame className="w-5 h-5 text-orange-500" />
          </div>
          <div>
            <p className="text-xs text-gray-600 dark:text-dark-400">Serie</p>
            <p className="text-lg font-bold text-orange-600 dark:text-orange-400">
              {currentStreak}
            </p>
          </div>
        </div>
        {milestone && (
          <span
            className={cn(
              "px-2 py-1 rounded-full text-xs font-bold",
              milestone.bg,
              milestone.color
            )}
          >
            {milestone.label}
          </span>
        )}
        <div className="ml-auto text-right">
          <p className="text-xs text-gray-500 dark:text-dark-400">Meilleure</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-white">{bestStreak}</p>
        </div>
      </div>
    );
  }

  // Full variant
  return (
    <div
      className={cn(
        "bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-500" />
          Hit & Win
        </h3>
        {milestone && (
          <span
            className={cn(
              "px-3 py-1 rounded-full text-sm font-bold flex items-center gap-1",
              milestone.bg,
              milestone.color
            )}
          >
            <Star className="w-4 h-4" />
            {milestone.label}
          </span>
        )}
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {/* Current Streak */}
        <div className="text-center p-3 bg-gradient-to-br from-orange-100 dark:from-orange-500/10 to-yellow-100 dark:to-yellow-500/10 rounded-lg">
          <Flame className="w-6 h-6 text-orange-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {currentStreak}
          </p>
          <p className="text-xs text-gray-600 dark:text-dark-400">Serie Actuelle</p>
        </div>

        {/* Best Streak */}
        <div className="text-center p-3 bg-gradient-to-br from-purple-100 dark:from-purple-500/10 to-pink-100 dark:to-pink-500/10 rounded-lg">
          <Trophy className="w-6 h-6 text-purple-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {bestStreak}
          </p>
          <p className="text-xs text-gray-600 dark:text-dark-400">Meilleure Serie</p>
        </div>

        {/* Win Rate */}
        <div className="text-center p-3 bg-gradient-to-br from-green-100 dark:from-green-500/10 to-emerald-100 dark:to-emerald-500/10 rounded-lg">
          <Target className="w-6 h-6 text-green-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">
            {winRate.toFixed(0)}%
          </p>
          <p className="text-xs text-gray-600 dark:text-dark-400">Taux Reussite</p>
        </div>

        {/* Total Wins */}
        <div className="text-center p-3 bg-gradient-to-br from-blue-100 dark:from-blue-500/10 to-cyan-100 dark:to-cyan-500/10 rounded-lg">
          <TrendingUp className="w-6 h-6 text-blue-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {totalWins}/{totalWins + totalLosses}
          </p>
          <p className="text-xs text-gray-600 dark:text-dark-400">Victoires</p>
        </div>
      </div>

      {/* Recent History */}
      {history.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-dark-400 mb-2">
            Derniers Resultats
          </p>
          <div className="flex gap-1 flex-wrap">
            {history.slice(0, 10).map((result, i) => (
              <div
                key={result.matchId}
                title={`${result.homeTeam} vs ${result.awayTeam} - ${result.bet}`}
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold",
                  result.won
                    ? "bg-green-100 dark:bg-green-500/20 text-green-600 dark:text-green-400"
                    : "bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400"
                )}
              >
                {result.won ? "W" : "L"}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {history.length === 0 && (
        <div className="text-center py-4">
          <p className="text-gray-500 dark:text-dark-400 text-sm">
            Aucun resultat enregistre. Commencez a suivre vos paris!
          </p>
        </div>
      )}

      {/* Streak Milestones */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-dark-700">
        <p className="text-xs text-gray-500 dark:text-dark-400 mb-2">Objectifs</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {[
            { target: 3, label: "En Feu", icon: "🔥" },
            { target: 5, label: "Pro", icon: "⚡" },
            { target: 7, label: "Expert", icon: "🎯" },
            { target: 10, label: "Legende", icon: "👑" },
          ].map((goal) => (
            <div
              key={goal.target}
              className={cn(
                "flex items-center gap-1 px-2 py-1 rounded-full text-xs whitespace-nowrap",
                currentStreak >= goal.target
                  ? "bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300"
                  : "bg-gray-100 dark:bg-dark-700 text-gray-500 dark:text-dark-400"
              )}
            >
              <span>{goal.icon}</span>
              <span>{goal.target}x</span>
            </div>
          ))}
        </div>
      </div>

      {/* Achievements Section */}
      <Achievements variant="compact" className="mt-4" />
    </div>
  );
}
