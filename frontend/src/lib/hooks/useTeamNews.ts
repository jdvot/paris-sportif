"use client";

import { useQuery } from "@tanstack/react-query";
import { customInstance } from "@/lib/api/custom-instance";

// Types
export interface TeamNews {
  id: string;
  title: string;
  content: string;
  source: string;
  published_at: string;
  category: string; // injury, transfer, form, preview
  sentiment?: "positive" | "negative" | "neutral";
}

export interface TeamNewsResponse {
  news: TeamNews[];
  total: number;
}

export interface TeamSummary {
  summary: string;
  form: string; // WWLDW format
  position: number | null;
  competition: string | null;
  points: number | null;
  next_match?: {
    opponent: string;
    date: string;
    is_home: boolean;
  };
  key_insights: string[];
  generated_at: string;
}

// API Functions
async function getTeamNews(teamId: number, limit = 5): Promise<TeamNewsResponse> {
  const response = await customInstance<{ data: TeamNewsResponse; status: number }>(
    `/api/v1/users/teams/${teamId}/news?limit=${limit}`,
    { method: "GET" }
  );
  if (response.status !== 200) {
    throw new Error("Failed to fetch team news");
  }
  return response.data;
}

async function getTeamSummary(teamId: number): Promise<TeamSummary> {
  const response = await customInstance<{ data: TeamSummary; status: number }>(
    `/api/v1/users/teams/${teamId}/summary`,
    { method: "GET" }
  );
  if (response.status !== 200) {
    throw new Error("Failed to fetch team summary");
  }
  return response.data;
}

// Hooks
export function useTeamNews(teamId: number | null, options?: { enabled?: boolean; limit?: number }) {
  return useQuery({
    queryKey: ["team-news", teamId, options?.limit],
    queryFn: () => getTeamNews(teamId!, options?.limit),
    enabled: !!teamId && (options?.enabled !== false),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useTeamSummary(teamId: number | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["team-summary", teamId],
    queryFn: () => getTeamSummary(teamId!),
    enabled: !!teamId && (options?.enabled !== false),
    staleTime: 15 * 60 * 1000, // 15 minutes
  });
}
