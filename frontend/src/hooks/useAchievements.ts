"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

export type AchievementId =
  // Streak achievements
  | "first_win"
  | "streak_3"
  | "streak_5"
  | "streak_7"
  | "streak_10"
  | "streak_15"
  // Volume achievements
  | "bets_10"
  | "bets_50"
  | "bets_100"
  | "bets_500"
  // Win rate achievements
  | "winrate_60"
  | "winrate_70"
  | "winrate_80"
  // Special achievements
  | "perfect_week"
  | "comeback_king"
  | "value_hunter"
  | "early_bird"
  | "night_owl"
  | "multi_league";

export interface Achievement {
  id: AchievementId;
  name: string;
  nameEn: string;
  description: string;
  descriptionEn: string;
  icon: string;
  rarity: "common" | "rare" | "epic" | "legendary";
  xp: number;
  unlockedAt?: string;
}

export interface AchievementsData {
  unlocked: Record<AchievementId, string>; // achievement_id -> unlock date
  totalXP: number;
  level: number;
  lastChecked: string;
}

const ACHIEVEMENTS_KEY = "paris-sportif-achievements";

// Achievement definitions
export const ACHIEVEMENTS: Record<AchievementId, Omit<Achievement, "unlockedAt">> = {
  // Streak achievements
  first_win: {
    id: "first_win",
    name: "Premiere Victoire",
    nameEn: "First Victory",
    description: "Gagnez votre premier pari",
    descriptionEn: "Win your first bet",
    icon: "🎉",
    rarity: "common",
    xp: 10,
  },
  streak_3: {
    id: "streak_3",
    name: "En Feu",
    nameEn: "On Fire",
    description: "Atteignez une serie de 3 victoires",
    descriptionEn: "Reach a 3-win streak",
    icon: "🔥",
    rarity: "common",
    xp: 25,
  },
  streak_5: {
    id: "streak_5",
    name: "Pro Gamer",
    nameEn: "Pro Gamer",
    description: "Atteignez une serie de 5 victoires",
    descriptionEn: "Reach a 5-win streak",
    icon: "⚡",
    rarity: "rare",
    xp: 50,
  },
  streak_7: {
    id: "streak_7",
    name: "Expert",
    nameEn: "Expert",
    description: "Atteignez une serie de 7 victoires",
    descriptionEn: "Reach a 7-win streak",
    icon: "🎯",
    rarity: "epic",
    xp: 100,
  },
  streak_10: {
    id: "streak_10",
    name: "Legendaire",
    nameEn: "Legendary",
    description: "Atteignez une serie de 10 victoires",
    descriptionEn: "Reach a 10-win streak",
    icon: "👑",
    rarity: "legendary",
    xp: 250,
  },
  streak_15: {
    id: "streak_15",
    name: "Imbattable",
    nameEn: "Unbeatable",
    description: "Atteignez une serie de 15 victoires",
    descriptionEn: "Reach a 15-win streak",
    icon: "🏆",
    rarity: "legendary",
    xp: 500,
  },
  // Volume achievements
  bets_10: {
    id: "bets_10",
    name: "Debutant",
    nameEn: "Beginner",
    description: "Placez 10 paris",
    descriptionEn: "Place 10 bets",
    icon: "📊",
    rarity: "common",
    xp: 15,
  },
  bets_50: {
    id: "bets_50",
    name: "Habitue",
    nameEn: "Regular",
    description: "Placez 50 paris",
    descriptionEn: "Place 50 bets",
    icon: "📈",
    rarity: "rare",
    xp: 75,
  },
  bets_100: {
    id: "bets_100",
    name: "Veteran",
    nameEn: "Veteran",
    description: "Placez 100 paris",
    descriptionEn: "Place 100 bets",
    icon: "🎖️",
    rarity: "epic",
    xp: 150,
  },
  bets_500: {
    id: "bets_500",
    name: "Maitre Parieur",
    nameEn: "Master Bettor",
    description: "Placez 500 paris",
    descriptionEn: "Place 500 bets",
    icon: "💎",
    rarity: "legendary",
    xp: 400,
  },
  // Win rate achievements (min 20 bets)
  winrate_60: {
    id: "winrate_60",
    name: "Analyste",
    nameEn: "Analyst",
    description: "Maintenez 60% de reussite (min. 20 paris)",
    descriptionEn: "Maintain 60% win rate (min. 20 bets)",
    icon: "📐",
    rarity: "rare",
    xp: 60,
  },
  winrate_70: {
    id: "winrate_70",
    name: "Strategiste",
    nameEn: "Strategist",
    description: "Maintenez 70% de reussite (min. 20 paris)",
    descriptionEn: "Maintain 70% win rate (min. 20 bets)",
    icon: "🧠",
    rarity: "epic",
    xp: 120,
  },
  winrate_80: {
    id: "winrate_80",
    name: "Oracle",
    nameEn: "Oracle",
    description: "Maintenez 80% de reussite (min. 20 paris)",
    descriptionEn: "Maintain 80% win rate (min. 20 bets)",
    icon: "🔮",
    rarity: "legendary",
    xp: 300,
  },
  // Special achievements
  perfect_week: {
    id: "perfect_week",
    name: "Semaine Parfaite",
    nameEn: "Perfect Week",
    description: "Gagnez 7 paris consecutifs en une semaine",
    descriptionEn: "Win 7 consecutive bets in one week",
    icon: "✨",
    rarity: "epic",
    xp: 200,
  },
  comeback_king: {
    id: "comeback_king",
    name: "Roi du Comeback",
    nameEn: "Comeback King",
    description: "Gagnez 3 paris apres une serie de 3 defaites",
    descriptionEn: "Win 3 bets after a 3-loss streak",
    icon: "💪",
    rarity: "rare",
    xp: 80,
  },
  value_hunter: {
    id: "value_hunter",
    name: "Chasseur de Value",
    nameEn: "Value Hunter",
    description: "Gagnez 5 paris sur des cotes > 2.0",
    descriptionEn: "Win 5 bets on odds > 2.0",
    icon: "🎰",
    rarity: "rare",
    xp: 75,
  },
  early_bird: {
    id: "early_bird",
    name: "Leve-Tot",
    nameEn: "Early Bird",
    description: "Placez un pari avant 8h du matin",
    descriptionEn: "Place a bet before 8 AM",
    icon: "🌅",
    rarity: "common",
    xp: 20,
  },
  night_owl: {
    id: "night_owl",
    name: "Oiseau de Nuit",
    nameEn: "Night Owl",
    description: "Placez un pari apres minuit",
    descriptionEn: "Place a bet after midnight",
    icon: "🦉",
    rarity: "common",
    xp: 20,
  },
  multi_league: {
    id: "multi_league",
    name: "Globe-Trotter",
    nameEn: "Globe Trotter",
    description: "Gagnez des paris dans 5 ligues differentes",
    descriptionEn: "Win bets in 5 different leagues",
    icon: "🌍",
    rarity: "rare",
    xp: 100,
  },
};

// XP required for each level
const XP_PER_LEVEL = 100;

const DEFAULT_DATA: AchievementsData = {
  unlocked: {} as Record<AchievementId, string>,
  totalXP: 0,
  level: 1,
  lastChecked: new Date().toISOString(),
};

export function useAchievements() {
  const [data, setData] = useState<AchievementsData>(DEFAULT_DATA);
  const [isLoaded, setIsLoaded] = useState(false);
  const [newUnlock, setNewUnlock] = useState<Achievement | null>(null);

  // Load from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(ACHIEVEMENTS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setData(parsed);
      }
    } catch (error) {
      console.error("Failed to load achievements:", error);
    }
    setIsLoaded(true);
  }, []);

  // Save to localStorage
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(ACHIEVEMENTS_KEY, JSON.stringify(data));
      } catch (error) {
        console.error("Failed to save achievements:", error);
      }
    }
  }, [data, isLoaded]);

  // Check if an achievement is unlocked
  const isUnlocked = useCallback(
    (id: AchievementId): boolean => {
      return id in data.unlocked;
    },
    [data.unlocked]
  );

  // Unlock an achievement
  const unlock = useCallback(
    (id: AchievementId): boolean => {
      if (isUnlocked(id)) return false;

      const achievement = ACHIEVEMENTS[id];
      if (!achievement) return false;

      const now = new Date().toISOString();
      const newXP = data.totalXP + achievement.xp;
      const newLevel = Math.floor(newXP / XP_PER_LEVEL) + 1;

      setData((prev) => ({
        ...prev,
        unlocked: {
          ...prev.unlocked,
          [id]: now,
        },
        totalXP: newXP,
        level: newLevel,
        lastChecked: now,
      }));

      // Trigger notification
      setNewUnlock({ ...achievement, unlockedAt: now });
      setTimeout(() => setNewUnlock(null), 5000);

      return true;
    },
    [data.totalXP, isUnlocked]
  );

  // Check achievements based on streak data
  const checkStreakAchievements = useCallback(
    (streakData: {
      currentStreak: number;
      bestStreak: number;
      totalWins: number;
      totalLosses: number;
      history: Array<{ won: boolean; date: string }>;
    }) => {
      const { bestStreak, totalWins, totalLosses, history } = streakData;
      const totalBets = totalWins + totalLosses;
      const winRate = totalBets > 0 ? (totalWins / totalBets) * 100 : 0;

      // First win
      if (totalWins >= 1) unlock("first_win");

      // Streak achievements (check best streak)
      if (bestStreak >= 3) unlock("streak_3");
      if (bestStreak >= 5) unlock("streak_5");
      if (bestStreak >= 7) unlock("streak_7");
      if (bestStreak >= 10) unlock("streak_10");
      if (bestStreak >= 15) unlock("streak_15");

      // Volume achievements
      if (totalBets >= 10) unlock("bets_10");
      if (totalBets >= 50) unlock("bets_50");
      if (totalBets >= 100) unlock("bets_100");
      if (totalBets >= 500) unlock("bets_500");

      // Win rate achievements (min 20 bets)
      if (totalBets >= 20) {
        if (winRate >= 60) unlock("winrate_60");
        if (winRate >= 70) unlock("winrate_70");
        if (winRate >= 80) unlock("winrate_80");
      }

      // Perfect week check
      if (history.length >= 7) {
        const oneWeekAgo = new Date();
        oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
        const recentHistory = history.filter(
          (h) => new Date(h.date) >= oneWeekAgo
        );
        if (recentHistory.length >= 7 && recentHistory.every((h) => h.won)) {
          unlock("perfect_week");
        }
      }

      // Comeback king check
      if (history.length >= 6) {
        const last6 = history.slice(0, 6);
        // Check pattern: W W W L L L (reversed because history is newest first)
        const reversed = [...last6].reverse();
        if (
          reversed.slice(0, 3).every((h) => !h.won) &&
          reversed.slice(3, 6).every((h) => h.won)
        ) {
          unlock("comeback_king");
        }
      }

      // Time-based achievements
      if (history.length > 0) {
        const lastBetHour = new Date(history[0].date).getHours();
        if (lastBetHour < 8) unlock("early_bird");
        if (lastBetHour >= 0 && lastBetHour < 5) unlock("night_owl");
      }
    },
    [unlock]
  );

  // Get all achievements with unlock status
  const allAchievements = useMemo((): Achievement[] => {
    return Object.values(ACHIEVEMENTS).map((a) => ({
      ...a,
      unlockedAt: data.unlocked[a.id] || undefined,
    }));
  }, [data.unlocked]);

  // Get unlocked achievements
  const unlockedAchievements = useMemo((): Achievement[] => {
    return allAchievements.filter((a) => a.unlockedAt);
  }, [allAchievements]);

  // Get locked achievements
  const lockedAchievements = useMemo((): Achievement[] => {
    return allAchievements.filter((a) => !a.unlockedAt);
  }, [allAchievements]);

  // Progress to next level
  const levelProgress = useMemo(() => {
    const currentLevelXP = (data.level - 1) * XP_PER_LEVEL;
    const xpInCurrentLevel = data.totalXP - currentLevelXP;
    return (xpInCurrentLevel / XP_PER_LEVEL) * 100;
  }, [data.totalXP, data.level]);

  // XP needed for next level
  const xpToNextLevel = useMemo(() => {
    const nextLevelXP = data.level * XP_PER_LEVEL;
    return nextLevelXP - data.totalXP;
  }, [data.totalXP, data.level]);

  // Reset achievements
  const resetAchievements = useCallback(() => {
    setData(DEFAULT_DATA);
  }, []);

  // Dismiss new unlock notification
  const dismissNotification = useCallback(() => {
    setNewUnlock(null);
  }, []);

  return {
    // Data
    unlocked: data.unlocked,
    totalXP: data.totalXP,
    level: data.level,
    levelProgress,
    xpToNextLevel,
    isLoaded,
    // Achievements
    allAchievements,
    unlockedAchievements,
    lockedAchievements,
    unlockedCount: unlockedAchievements.length,
    totalCount: allAchievements.length,
    // Notifications
    newUnlock,
    dismissNotification,
    // Methods
    isUnlocked,
    unlock,
    checkStreakAchievements,
    resetAchievements,
  };
}
