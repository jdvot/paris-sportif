"use client";

import { TrendingUp, TrendingDown, Minus, Shield, Swords, Target, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface TeamStats {
  name: string;
  position?: number;
  points?: number;
  form?: string[];
  goalsFor?: number;
  goalsAgainst?: number;
  xgFor?: number;
  xgAgainst?: number;
}

interface TeamStrengthIndexProps {
  homeTeam: TeamStats;
  awayTeam: TeamStats;
  homeElo?: number;
  awayElo?: number;
  className?: string;
}

export function TeamStrengthIndex({
  homeTeam,
  awayTeam,
  homeElo = 1500,
  awayElo = 1500,
  className,
}: TeamStrengthIndexProps) {
  // Calculate strength scores (0-100)
  const calculateStrength = (elo: number) => {
    // ELO typically ranges from 1200-1800 for football
    const minElo = 1200;
    const maxElo = 1900;
    const normalized = ((elo - minElo) / (maxElo - minElo)) * 100;
    return Math.max(0, Math.min(100, normalized));
  };

  const homeStrength = calculateStrength(homeElo);
  const awayStrength = calculateStrength(awayElo);
  const eloDiff = homeElo - awayElo;

  // Form analysis
  const analyzeForm = (form?: string[]) => {
    if (!form || form.length === 0) return { wins: 0, draws: 0, losses: 0, points: 0 };
    const wins = form.filter((r) => r === "W").length;
    const draws = form.filter((r) => r === "D").length;
    const losses = form.filter((r) => r === "L").length;
    return { wins, draws, losses, points: wins * 3 + draws };
  };

  const homeForm = analyzeForm(homeTeam.form);
  const awayForm = analyzeForm(awayTeam.form);

  const getStrengthColor = (strength: number) => {
    if (strength >= 70) return "text-primary-500";
    if (strength >= 50) return "text-blue-500";
    if (strength >= 30) return "text-yellow-500";
    return "text-orange-500";
  };

  const getStrengthLabel = (strength: number) => {
    if (strength >= 80) return "Elite";
    if (strength >= 65) return "Tres Fort";
    if (strength >= 50) return "Fort";
    if (strength >= 35) return "Moyen";
    return "Faible";
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Zap className="w-4 h-4 text-yellow-500" />
          Indice de Force
        </h3>
        <span className="text-xs text-gray-500 dark:text-dark-400">
          Base ELO
        </span>
      </div>

      {/* Strength Comparison */}
      <div className="grid grid-cols-3 gap-4">
        {/* Home Team */}
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-dark-400 mb-1 truncate">
            {homeTeam.name}
          </p>
          <div className="relative w-16 h-16 mx-auto mb-2">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="32"
                cy="32"
                r="28"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                className="text-gray-200 dark:text-dark-700"
              />
              <circle
                cx="32"
                cy="32"
                r="28"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                strokeDasharray={`${(homeStrength / 100) * 176} 176`}
                strokeLinecap="round"
                className={getStrengthColor(homeStrength)}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={cn("text-lg font-bold", getStrengthColor(homeStrength))}>
                {Math.round(homeStrength)}
              </span>
            </div>
          </div>
          <span className={cn("text-xs font-medium", getStrengthColor(homeStrength))}>
            {getStrengthLabel(homeStrength)}
          </span>
        </div>

        {/* VS Comparison */}
        <div className="flex flex-col items-center justify-center">
          <div className="text-xs text-gray-500 dark:text-dark-400 mb-1">Difference</div>
          <div
            className={cn(
              "flex items-center gap-1 text-sm font-bold",
              eloDiff > 50
                ? "text-primary-500"
                : eloDiff < -50
                ? "text-blue-500"
                : "text-gray-500 dark:text-dark-400"
            )}
          >
            {eloDiff > 0 ? (
              <TrendingUp className="w-4 h-4" />
            ) : eloDiff < 0 ? (
              <TrendingDown className="w-4 h-4" />
            ) : (
              <Minus className="w-4 h-4" />
            )}
            <span>{Math.abs(eloDiff)}</span>
          </div>
          <span className="text-[10px] text-gray-400 dark:text-dark-500">ELO pts</span>
        </div>

        {/* Away Team */}
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-dark-400 mb-1 truncate">
            {awayTeam.name}
          </p>
          <div className="relative w-16 h-16 mx-auto mb-2">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="32"
                cy="32"
                r="28"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                className="text-gray-200 dark:text-dark-700"
              />
              <circle
                cx="32"
                cy="32"
                r="28"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                strokeDasharray={`${(awayStrength / 100) * 176} 176`}
                strokeLinecap="round"
                className={getStrengthColor(awayStrength)}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={cn("text-lg font-bold", getStrengthColor(awayStrength))}>
                {Math.round(awayStrength)}
              </span>
            </div>
          </div>
          <span className={cn("text-xs font-medium", getStrengthColor(awayStrength))}>
            {getStrengthLabel(awayStrength)}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-200 dark:border-dark-700">
        {/* Home Stats */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1 text-gray-500 dark:text-dark-400">
              <Shield className="w-3 h-3" />
              Position
            </span>
            <span className="font-medium text-gray-900 dark:text-white">
              {homeTeam.position ? `#${homeTeam.position}` : "-"}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1 text-gray-500 dark:text-dark-400">
              <Swords className="w-3 h-3" />
              Forme
            </span>
            <span className="font-medium text-gray-900 dark:text-white">
              {homeForm.wins}W {homeForm.draws}D {homeForm.losses}L
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1 text-gray-500 dark:text-dark-400">
              <Target className="w-3 h-3" />
              Buts
            </span>
            <span className="font-medium text-gray-900 dark:text-white">
              {homeTeam.goalsFor ?? "-"} / {homeTeam.goalsAgainst ?? "-"}
            </span>
          </div>
        </div>

        {/* Away Stats */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1 text-gray-500 dark:text-dark-400">
              <Shield className="w-3 h-3" />
              Position
            </span>
            <span className="font-medium text-gray-900 dark:text-white">
              {awayTeam.position ? `#${awayTeam.position}` : "-"}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1 text-gray-500 dark:text-dark-400">
              <Swords className="w-3 h-3" />
              Forme
            </span>
            <span className="font-medium text-gray-900 dark:text-white">
              {awayForm.wins}W {awayForm.draws}D {awayForm.losses}L
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1 text-gray-500 dark:text-dark-400">
              <Target className="w-3 h-3" />
              Buts
            </span>
            <span className="font-medium text-gray-900 dark:text-white">
              {awayTeam.goalsFor ?? "-"} / {awayTeam.goalsAgainst ?? "-"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
