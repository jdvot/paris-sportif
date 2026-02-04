"use client";

import { useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useListFavoritesApiV1UserFavoritesGet,
  useAddFavoriteApiV1UserFavoritesPost,
  useRemoveFavoriteApiV1UserFavoritesMatchIdDelete,
  getListFavoritesApiV1UserFavoritesGetQueryKey,
} from "@/lib/api/endpoints/user-data/user-data";

export interface FavoriteMatch {
  matchId: number;
  homeTeam: string;
  awayTeam: string;
  matchDate: string;
  competition?: string;
  addedAt: string;
}

export function useFavorites() {
  const queryClient = useQueryClient();
  const queryKey = getListFavoritesApiV1UserFavoritesGetQueryKey();

  // Fetch favorites from API
  const {
    data: response,
    isLoading,
    error,
  } = useListFavoritesApiV1UserFavoritesGet();

  // Add favorite mutation
  const addMutation = useAddFavoriteApiV1UserFavoritesPost({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey });
      },
    },
  });

  // Remove favorite mutation
  const removeMutation = useRemoveFavoriteApiV1UserFavoritesMatchIdDelete({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey });
      },
    },
  });

  // Extract favorites from response
  const favorites = useMemo<FavoriteMatch[]>(() => {
    if (response?.status !== 200) return [];
    const data = response.data;
    return (data.favorites || []).map((f) => ({
      matchId: f.match_id,
      homeTeam: f.home_team || "",
      awayTeam: f.away_team || "",
      matchDate: f.match_date || "",
      competition: f.competition || undefined,
      addedAt: f.added_at || new Date().toISOString(),
    }));
  }, [response]);

  const addFavorite = useCallback(
    (match: Omit<FavoriteMatch, "addedAt">) => {
      addMutation.mutate({
        data: {
          match_id: match.matchId,
          home_team: match.homeTeam,
          away_team: match.awayTeam,
          match_date: match.matchDate,
          competition: match.competition,
        },
      });
    },
    [addMutation]
  );

  const removeFavorite = useCallback(
    (matchId: number) => {
      removeMutation.mutate({ matchId });
    },
    [removeMutation]
  );

  const toggleFavorite = useCallback(
    (match: Omit<FavoriteMatch, "addedAt">) => {
      const exists = favorites.some((f) => f.matchId === match.matchId);
      if (exists) {
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
    // Clear all favorites by removing each one
    favorites.forEach((f) => {
      removeMutation.mutate({ matchId: f.matchId });
    });
  }, [favorites, removeMutation]);

  return {
    favorites,
    isLoaded: !isLoading,
    isLoading,
    error,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    isFavorite,
    clearFavorites,
    count: favorites.length,
    isPending: addMutation.isPending || removeMutation.isPending,
  };
}
