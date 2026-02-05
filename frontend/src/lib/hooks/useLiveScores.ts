"use client";

import { useQuery } from "@tanstack/react-query";
import { customInstance } from "@/lib/api/custom-instance";

// Types
export interface TeamInfo {
  id: number;
  name: string;
  short_name: string;
  logo_url: string | null;
  elo_rating?: number | null;
  form?: string | null;
}

export interface LiveMatchEvent {
  type: string; // goal, yellow_card, red_card, substitution
  minute: number;
  team: "home" | "away";
  player: string | null;
}

export interface LiveMatch {
  id: number;
  external_id: string;
  home_team: TeamInfo;
  away_team: TeamInfo;
  home_score: number;
  away_score: number;
  minute: number | null;
  status: string; // 1H, HT, 2H, FT, ET, PEN
  competition: string;
  competition_code: string;
  events: LiveMatchEvent[];
}

export interface LiveScoresResponse {
  matches: LiveMatch[];
  total: number;
  updated_at: string;
  data_source?: {
    source: string;
    is_fallback: boolean;
    warning?: string;
  };
}

// API Function
async function getLiveScores(competition?: string): Promise<LiveScoresResponse> {
  const url = competition
    ? `/api/v1/matches/live?competition=${encodeURIComponent(competition)}`
    : "/api/v1/matches/live";

  const response = await customInstance<{ data: LiveScoresResponse; status: number }>(
    url,
    { method: "GET" }
  );

  if (response.status !== 200) {
    throw new Error("Failed to fetch live scores");
  }

  return response.data;
}

// Hook
export function useLiveScores(
  competition?: string,
  options?: { enabled?: boolean; refetchInterval?: number }
) {
  return useQuery({
    queryKey: ["live-scores", competition],
    queryFn: () => getLiveScores(competition),
    refetchInterval: options?.refetchInterval ?? 30000, // 30 seconds default
    staleTime: 15000, // 15 seconds
    enabled: options?.enabled !== false,
  });
}
