/**
 * API client for the Paris Sportif backend
 */

import type {
  DailyPick,
  DailyPicksResponse,
  Match,
  DetailedPrediction,
  PredictionStats,
  TeamForm,
} from "./types";
import {
  mockMatch,
  mockPrediction,
  mockHomeTeamForm,
  mockAwayTeamForm,
  mockHeadToHead,
  mockUpcomingMatches,
  getMockMatchById,
} from "./mockData";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true";

// Debug log for API configuration (will be removed in production later)
if (typeof window !== "undefined") {
  console.log("[API Config] URL:", API_BASE_URL, "| Mock mode:", USE_MOCK_DATA);
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch daily picks
 */
export async function fetchDailyPicks(date?: string): Promise<DailyPick[]> {
  const params = date ? `?date=${date}` : "";
  const response = await fetchApi<DailyPicksResponse>(
    `/api/v1/predictions/daily${params}`
  );
  return response.picks;
}

/**
 * Fetch upcoming matches
 */
export async function fetchUpcomingMatches(
  days: number = 2,
  competition?: string
): Promise<Match[]> {
  if (USE_MOCK_DATA) {
    return new Promise((resolve) =>
      setTimeout(() => resolve(mockUpcomingMatches), 300)
    );
  }
  const params = new URLSearchParams({ days: days.toString() });
  if (competition) params.append("competition", competition);

  const response = await fetchApi<{ matches: Match[] }>(
    `/api/v1/matches/upcoming?${params}`
  );
  return response.matches;
}

/**
 * Fetch matches with filters
 */
export async function fetchMatches(options?: {
  competition?: string;
  dateFrom?: string;
  dateTo?: string;
  status?: "scheduled" | "live" | "finished";
  page?: number;
  perPage?: number;
}): Promise<{ matches: Match[]; total: number }> {
  const params = new URLSearchParams();
  if (options?.competition) params.append("competition", options.competition);
  if (options?.dateFrom) params.append("date_from", options.dateFrom);
  if (options?.dateTo) params.append("date_to", options.dateTo);
  if (options?.status) params.append("status", options.status);
  if (options?.page) params.append("page", options.page.toString());
  if (options?.perPage) params.append("per_page", options.perPage.toString());

  return fetchApi(`/api/v1/matches?${params}`);
}

/**
 * Fetch single match details
 */
export async function fetchMatch(matchId: number): Promise<Match> {
  if (USE_MOCK_DATA) {
    return new Promise((resolve) =>
      setTimeout(() => resolve(getMockMatchById(matchId)), 300)
    );
  }
  return fetchApi(`/api/v1/matches/${matchId}`);
}

/**
 * Fetch detailed prediction for a match
 */
export async function fetchPrediction(
  matchId: number,
  includeModelDetails: boolean = false
): Promise<DetailedPrediction> {
  if (USE_MOCK_DATA) {
    return new Promise((resolve) =>
      setTimeout(() => resolve(mockPrediction), 300)
    );
  }
  const params = includeModelDetails ? "?include_model_details=true" : "";
  return fetchApi(`/api/v1/predictions/${matchId}${params}`);
}

/**
 * Fetch team form
 */
export async function fetchTeamForm(
  teamId: number,
  matchesCount: number = 5
): Promise<TeamForm> {
  if (USE_MOCK_DATA) {
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockData = teamId % 2 === 0 ? mockAwayTeamForm : mockHomeTeamForm;
        resolve(mockData);
      }, 300);
    });
  }
  return fetchApi(`/api/v1/matches/teams/${teamId}/form?matches_count=${matchesCount}`);
}

/**
 * Fetch head-to-head history
 */
export async function fetchHeadToHead(
  matchId: number,
  limit: number = 10
): Promise<{ matches: Match[]; homeWins: number; draws: number; awayWins: number }> {
  if (USE_MOCK_DATA) {
    return new Promise((resolve) =>
      setTimeout(() => resolve(mockHeadToHead), 300)
    );
  }
  return fetchApi(`/api/v1/matches/${matchId}/head-to-head?limit=${limit}`);
}

/**
 * Fetch prediction statistics
 */
export async function fetchPredictionStats(days: number = 30): Promise<PredictionStats> {
  return fetchApi(`/api/v1/predictions/stats?days=${days}`);
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; version: string }> {
  return fetchApi("/health");
}
