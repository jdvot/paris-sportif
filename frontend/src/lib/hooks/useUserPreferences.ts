"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { customInstance } from "@/lib/api/custom-instance";

// Types
export interface FavoriteTeamInfo {
  id: number;
  name: string;
  short_name: string;
  logo_url: string | null;
  country: string | null;
}

export interface UserPreferences {
  language: string;
  timezone: string;
  odds_format: string;
  dark_mode: boolean;
  email_daily_picks: boolean;
  email_match_results: boolean;
  push_daily_picks: boolean;
  push_match_start: boolean;
  push_bet_results: boolean;
  default_stake: number;
  risk_level: string;
  favorite_competitions: string[];
  favorite_team_id: number | null;
  favorite_team: FavoriteTeamInfo | null;
}

export interface UserPreferencesUpdate {
  language?: string;
  timezone?: string;
  odds_format?: string;
  dark_mode?: boolean;
  email_daily_picks?: boolean;
  email_match_results?: boolean;
  push_daily_picks?: boolean;
  push_match_start?: boolean;
  push_bet_results?: boolean;
  default_stake?: number;
  risk_level?: string;
  favorite_competitions?: string[];
  favorite_team_id?: number | null;
}

export interface TeamSearchResult {
  id: number;
  name: string;
  short_name: string | null;
  logo_url: string | null;
  country: string | null;
}

export interface TeamSearchResponse {
  teams: TeamSearchResult[];
  total: number;
}

// API Functions
async function getPreferences(): Promise<UserPreferences> {
  const response = await customInstance<{ data: UserPreferences; status: number }>(
    "/api/v1/users/me/preferences",
    { method: "GET" }
  );
  if (response.status !== 200) {
    throw new Error("Failed to fetch preferences");
  }
  return response.data;
}

async function updatePreferences(data: UserPreferencesUpdate): Promise<UserPreferences> {
  const response = await customInstance<{ data: UserPreferences; status: number }>(
    "/api/v1/users/me/preferences",
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
  if (response.status !== 200) {
    throw new Error("Failed to update preferences");
  }
  return response.data;
}

async function searchTeams(query: string, limit = 10): Promise<TeamSearchResponse> {
  const response = await customInstance<{ data: TeamSearchResponse; status: number }>(
    `/api/v1/users/teams/search?q=${encodeURIComponent(query)}&limit=${limit}`,
    { method: "GET" }
  );
  if (response.status !== 200) {
    throw new Error("Failed to search teams");
  }
  return response.data;
}

// Hooks
export function useUserPreferences(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["user-preferences"],
    queryFn: getPreferences,
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updatePreferences,
    onSuccess: (data) => {
      queryClient.setQueryData(["user-preferences"], data);
    },
  });
}

export function useTeamSearch(query: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["team-search", query],
    queryFn: () => searchTeams(query),
    enabled: query.length >= 2 && (options?.enabled !== false),
    staleTime: 30 * 1000, // 30 seconds
  });
}
