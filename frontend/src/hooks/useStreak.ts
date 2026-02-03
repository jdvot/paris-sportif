"use client";

import { useState, useEffect, useCallback } from "react";

export interface StreakData {
  currentStreak: number;
  bestStreak: number;
  totalWins: number;
  totalLosses: number;
  history: Array<{
    matchId: number;
    homeTeam: string;
    awayTeam: string;
    bet: string;
    won: boolean;
    date: string;
  }>;
  lastUpdated: string;
}

const STREAK_KEY = "paris-sportif-streak";

const DEFAULT_STREAK: StreakData = {
  currentStreak: 0,
  bestStreak: 0,
  totalWins: 0,
  totalLosses: 0,
  history: [],
  lastUpdated: new Date().toISOString(),
};

export function useStreak() {
  const [streak, setStreak] = useState<StreakData>(DEFAULT_STREAK);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load streak from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STREAK_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setStreak(parsed);
      }
    } catch (error) {
      console.error("Failed to load streak:", error);
    }
    setIsLoaded(true);
  }, []);

  // Save streak to localStorage whenever it changes
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(STREAK_KEY, JSON.stringify(streak));
      } catch (error) {
        console.error("Failed to save streak:", error);
      }
    }
  }, [streak, isLoaded]);

  const recordResult = useCallback(
    (result: {
      matchId: number;
      homeTeam: string;
      awayTeam: string;
      bet: string;
      won: boolean;
    }) => {
      setStreak((prev) => {
        // Check if already recorded
        if (prev.history.some((h) => h.matchId === result.matchId)) {
          return prev;
        }

        const newHistory = [
          { ...result, date: new Date().toISOString() },
          ...prev.history.slice(0, 49), // Keep last 50 results
        ];

        const newCurrentStreak = result.won ? prev.currentStreak + 1 : 0;
        const newBestStreak = Math.max(prev.bestStreak, newCurrentStreak);

        return {
          currentStreak: newCurrentStreak,
          bestStreak: newBestStreak,
          totalWins: prev.totalWins + (result.won ? 1 : 0),
          totalLosses: prev.totalLosses + (result.won ? 0 : 1),
          history: newHistory,
          lastUpdated: new Date().toISOString(),
        };
      });
    },
    []
  );

  const resetStreak = useCallback(() => {
    setStreak(DEFAULT_STREAK);
  }, []);

  const winRate = streak.totalWins + streak.totalLosses > 0
    ? (streak.totalWins / (streak.totalWins + streak.totalLosses)) * 100
    : 0;

  return {
    ...streak,
    winRate,
    isLoaded,
    recordResult,
    resetStreak,
  };
}
