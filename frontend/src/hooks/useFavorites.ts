"use client";

import { useState, useEffect, useCallback } from "react";

export interface FavoriteMatch {
  matchId: number;
  homeTeam: string;
  awayTeam: string;
  matchDate: string;
  competition?: string;
  addedAt: string;
}

const FAVORITES_KEY = "paris-sportif-favorites";

export function useFavorites() {
  const [favorites, setFavorites] = useState<FavoriteMatch[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load favorites from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(FAVORITES_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Filter out expired favorites (matches older than 7 days)
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        const valid = parsed.filter(
          (f: FavoriteMatch) => new Date(f.matchDate) >= sevenDaysAgo
        );
        setFavorites(valid);
        // Update storage if we removed any
        if (valid.length !== parsed.length) {
          localStorage.setItem(FAVORITES_KEY, JSON.stringify(valid));
        }
      }
    } catch (error) {
      console.error("Failed to load favorites:", error);
    }
    setIsLoaded(true);
  }, []);

  // Save favorites to localStorage whenever they change
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
      } catch (error) {
        console.error("Failed to save favorites:", error);
      }
    }
  }, [favorites, isLoaded]);

  const addFavorite = useCallback((match: Omit<FavoriteMatch, "addedAt">) => {
    setFavorites((prev) => {
      // Check if already exists
      if (prev.some((f) => f.matchId === match.matchId)) {
        return prev;
      }
      return [
        ...prev,
        {
          ...match,
          addedAt: new Date().toISOString(),
        },
      ];
    });
  }, []);

  const removeFavorite = useCallback((matchId: number) => {
    setFavorites((prev) => prev.filter((f) => f.matchId !== matchId));
  }, []);

  const toggleFavorite = useCallback(
    (match: Omit<FavoriteMatch, "addedAt">) => {
      if (favorites.some((f) => f.matchId === match.matchId)) {
        removeFavorite(match.matchId);
      } else {
        addFavorite(match);
      }
    },
    [favorites, addFavorite, removeFavorite]
  );

  const isFavorite = useCallback(
    (matchId: number) => {
      return favorites.some((f) => f.matchId === matchId);
    },
    [favorites]
  );

  const clearFavorites = useCallback(() => {
    setFavorites([]);
  }, []);

  return {
    favorites,
    isLoaded,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    isFavorite,
    clearFavorites,
    count: favorites.length,
  };
}
