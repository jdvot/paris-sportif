/**
 * API client for the WinRate AI backend
 */

import type {
  DailyPick,
  Match,
  DetailedPrediction,
  PredictionStats,
  TeamForm,
  ModelContribution,
  Standings,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// API response types (snake_case from backend)
interface ApiMatch {
  id: number;
  external_id?: string;
  home_team: { id: number; name: string; short_name?: string } | string;
  away_team: { id: number; name: string; short_name?: string } | string;
  competition: string;
  competition_code: string;
  match_date: string;
  status: string;
  home_score?: number | null;
  away_score?: number | null;
  matchday?: number;
}

/**
 * Extended Match type with team IDs for API calls
 */
export interface MatchWithTeamIds extends Match {
  homeTeamId?: number;
  awayTeamId?: number;
}

/**
 * Transform API match response to frontend Match type
 */
function transformMatch(apiMatch: ApiMatch): Match {
  return {
    id: apiMatch.id,
    homeTeam: typeof apiMatch.home_team === 'string'
      ? apiMatch.home_team
      : apiMatch.home_team.name,
    awayTeam: typeof apiMatch.away_team === 'string'
      ? apiMatch.away_team
      : apiMatch.away_team.name,
    competition: apiMatch.competition,
    competitionCode: apiMatch.competition_code,
    matchDate: apiMatch.match_date,
    status: apiMatch.status as Match['status'],
    homeScore: apiMatch.home_score ?? undefined,
    awayScore: apiMatch.away_score ?? undefined,
    matchday: apiMatch.matchday,
  };
}

/**
 * Transform API match response to frontend Match type WITH team IDs
 */
function transformMatchWithIds(apiMatch: ApiMatch): MatchWithTeamIds {
  const base = transformMatch(apiMatch);
  return {
    ...base,
    homeTeamId: typeof apiMatch.home_team === 'object' ? apiMatch.home_team.id : undefined,
    awayTeamId: typeof apiMatch.away_team === 'object' ? apiMatch.away_team.id : undefined,
  };
}

/**
 * Get auth token from the global token store
 * Uses the cached token which is populated by onAuthStateChange in Providers
 */
async function getAuthTokenFromStore(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null; // Server-side, no token
  }

  try {
    // Use the global token store instead of calling getSession()
    // This avoids race conditions during initialization
    const { getAuthToken } = await import("@/lib/auth/token-store");
    return getAuthToken();
  } catch {
    return null;
  }
}

/**
 * Generic fetch wrapper with error handling and authentication
 */
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  // Get auth token from global store
  const token = await getAuthTokenFromStore();

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let error: Record<string, unknown> = {};
    try {
      error = await response.json();
    } catch {
      error = { message: `API error: ${response.status} ${response.statusText}` };
    }

    // Handle auth errors specifically
    if (response.status === 401) {
      throw new Error("Authentification requise. Veuillez vous connecter.");
    }
    if (response.status === 403) {
      throw new Error("Acces refuse. Abonnement premium requis.");
    }

    throw new Error((error.message as string) || (error.detail as string) || `API error: ${response.status}`);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON response from ${endpoint}`);
  }
}

// API response type for daily picks (snake_case from backend)
interface ApiDailyPick {
  rank: number;
  pick_score?: number;
  prediction: Record<string, unknown>;
}

interface ApiDailyPicksResponse {
  date: string;
  picks: ApiDailyPick[];
  total_matches_analyzed?: number;
}

/**
 * Transform API daily pick to frontend format
 */
function transformDailyPick(apiPick: ApiDailyPick): DailyPick {
  const pred = apiPick.prediction;

  // Extract probabilities
  const probs = pred.probabilities as Record<string, number> | undefined;
  const probabilities = probs ? {
    homeWin: probs.home_win ?? probs.homeWin ?? 0,
    draw: probs.draw ?? 0,
    awayWin: probs.away_win ?? probs.awayWin ?? 0,
  } : undefined;

  // Map recommended_bet
  const recBet = (pred.recommended_bet ?? pred.recommendedBet) as string;
  const validBets = ["home_win", "draw", "away_win", "home", "away"] as const;
  const recommendedBet = validBets.includes(recBet as typeof validBets[number])
    ? (recBet as "home_win" | "draw" | "away_win" | "home" | "away")
    : "home";

  // Build match object from prediction fields
  const match = {
    id: (pred.match_id ?? pred.matchId ?? 0) as number,
    homeTeam: (pred.home_team ?? pred.homeTeam ?? "") as string,
    awayTeam: (pred.away_team ?? pred.awayTeam ?? "") as string,
    competition: (pred.competition ?? "") as string,
    matchDate: (pred.match_date ?? pred.matchDate ?? "") as string,
  };

  // Build prediction object
  const prediction = {
    probabilities,
    homeProb: probabilities?.homeWin,
    drawProb: probabilities?.draw,
    awayProb: probabilities?.awayWin,
    recommendedBet,
    confidence: (pred.confidence as number) ?? 0,
    valueScore: (pred.value_score ?? pred.valueScore ?? 0) as number,
  };

  return {
    rank: apiPick.rank || 0,
    match,
    prediction,
    explanation: (pred.explanation as string) ?? "",
    keyFactors: (pred.key_factors ?? pred.keyFactors ?? []) as string[],
    riskFactors: (pred.risk_factors ?? pred.riskFactors) as string[] | undefined,
    pickScore: apiPick.pick_score,
  };
}

/**
 * Fetch daily picks
 */
export async function fetchDailyPicks(date?: string): Promise<DailyPick[]> {
  const params = date ? `?date=${date}` : "";
  const response = await fetchApi<ApiDailyPicksResponse>(
    `/api/v1/predictions/daily${params}`
  );

  // Transform each pick from API format to frontend format
  if (!response.picks || !Array.isArray(response.picks)) {
    return [];
  }

  return response.picks.map(transformDailyPick);
}

/**
 * Fetch upcoming matches
 */
export async function fetchUpcomingMatches(
  days: number = 2,
  competition?: string
): Promise<Match[]> {
  const params = new URLSearchParams({ days: days.toString() });
  if (competition) params.append("competition", competition);

  const response = await fetchApi<{ matches: ApiMatch[] }>(
    `/api/v1/matches/upcoming?${params}`
  );
  return response.matches.map(transformMatch);
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

  const response = await fetchApi<{ matches: ApiMatch[]; total: number }>(`/api/v1/matches?${params}`);
  return {
    matches: response.matches.map(transformMatch),
    total: response.total,
  };
}

/**
 * Fetch single match details (with team IDs for form queries)
 */
export async function fetchMatch(matchId: number): Promise<MatchWithTeamIds> {
  const response = await fetchApi<ApiMatch>(`/api/v1/matches/${matchId}`);
  return transformMatchWithIds(response);
}

/**
 * Transform API prediction response (snake_case) to frontend format (camelCase)
 */
function transformPrediction(apiPrediction: Record<string, unknown>): DetailedPrediction {
  // Handle probabilities - API uses snake_case
  const probs = apiPrediction.probabilities as Record<string, number> | undefined;
  const probabilities = probs ? {
    homeWin: probs.home_win ?? probs.homeWin ?? 0,
    draw: probs.draw ?? 0,
    awayWin: probs.away_win ?? probs.awayWin ?? 0,
  } : undefined;

  // Handle model contributions - API uses snake_case
  const mc = apiPrediction.model_contributions as Record<string, unknown> | undefined;
  const modelContributions = mc ? {
    poisson: transformModelContrib(mc.poisson),
    elo: transformModelContrib(mc.elo),
    xgModel: transformModelContrib(mc.xg_model),
    xgboost: transformModelContrib(mc.xgboost),
  } : undefined;

  // Handle LLM adjustments - API uses snake_case
  const llm = apiPrediction.llm_adjustments as Record<string, unknown> | undefined;
  const llmAdjustments = llm ? {
    injuryImpactHome: (llm.injury_impact_home as number) ?? 0,
    injuryImpactAway: (llm.injury_impact_away as number) ?? 0,
    sentimentHome: (llm.sentiment_home as number) ?? 0,
    sentimentAway: (llm.sentiment_away as number) ?? 0,
    tacticalEdge: (llm.tactical_edge as number) ?? 0,
    totalAdjustment: (llm.total_adjustment as number) ?? 0,
    reasoning: (llm.reasoning as string) ?? "",
  } : undefined;

  // Map recommended_bet to valid type
  const recBet = apiPrediction.recommended_bet as string;
  const validBets = ["home_win", "draw", "away_win", "home", "away"] as const;
  const recommendedBet = validBets.includes(recBet as typeof validBets[number])
    ? (recBet as "home_win" | "draw" | "away_win" | "home" | "away")
    : "home";

  // Build model contributions only if all required properties exist
  const finalModelContributions = modelContributions?.poisson && modelContributions?.elo
    ? {
        poisson: modelContributions.poisson,
        elo: modelContributions.elo,
        xgModel: modelContributions.xgModel,
        xgboost: modelContributions.xgboost,
      }
    : undefined;

  return {
    matchId: apiPrediction.match_id as number,
    homeTeam: apiPrediction.home_team as string,
    awayTeam: apiPrediction.away_team as string,
    matchDate: apiPrediction.match_date as string,
    probabilities,
    homeProb: probabilities?.homeWin,
    drawProb: probabilities?.draw,
    awayProb: probabilities?.awayWin,
    recommendedBet,
    confidence: (apiPrediction.confidence as number) ?? 0,
    valueScore: (apiPrediction.value_score as number) ?? 0,
    explanation: (apiPrediction.explanation as string) ?? "",
    keyFactors: (apiPrediction.key_factors as string[]) ?? [],
    riskFactors: (apiPrediction.risk_factors as string[]) ?? [],
    modelContributions: finalModelContributions,
    llmAdjustments,
    expectedHomeGoals: apiPrediction.expected_home_goals as number | undefined,
    expectedAwayGoals: apiPrediction.expected_away_goals as number | undefined,
    createdAt: apiPrediction.created_at as string,
  };
}

function transformModelContrib(mc: unknown): ModelContribution | undefined {
  if (!mc || typeof mc !== 'object') return undefined;
  const contrib = mc as Record<string, number>;
  return {
    homeProb: contrib.home_win ?? contrib.homeWin,
    drawProb: contrib.draw,
    awayProb: contrib.away_win ?? contrib.awayWin,
  };
}

/**
 * Fetch detailed prediction for a match
 */
export async function fetchPrediction(
  matchId: number,
  includeModelDetails: boolean = false
): Promise<DetailedPrediction> {
  const params = includeModelDetails ? "?include_model_details=true" : "";
  const rawPrediction = await fetchApi<Record<string, unknown>>(`/api/v1/predictions/${matchId}${params}`);
  return transformPrediction(rawPrediction);
}

/**
 * Transform API team form response (snake_case) to frontend format (camelCase)
 */
function transformTeamForm(apiForm: Record<string, unknown>): TeamForm {
  const lastMatches = Array.isArray(apiForm.last_matches)
    ? apiForm.last_matches.map((m: Record<string, unknown>) => ({
        opponent: m.opponent as string,
        result: m.result as "W" | "D" | "L",
        score: m.score as string,
        homeAway: (m.home_away ?? m.homeAway) as "H" | "A",
        date: m.date as string,
      }))
    : [];

  return {
    teamId: (apiForm.team_id ?? apiForm.teamId) as number,
    teamName: (apiForm.team_name ?? apiForm.teamName) as string,
    lastMatches,
    formString: (apiForm.form_string ?? apiForm.formString) as string,
    pointsLast5: (apiForm.points_last_5 ?? apiForm.pointsLast5) as number,
    goalsScoredAvg: (apiForm.goals_scored_avg ?? apiForm.goalsScoredAvg) as number,
    goalsConcededAvg: (apiForm.goals_conceded_avg ?? apiForm.goalsConcededAvg) as number,
    cleanSheets: (apiForm.clean_sheets ?? apiForm.cleanSheets) as number,
    xgForAvg: apiForm.xg_for_avg as number | undefined,
    xgAgainstAvg: apiForm.xg_against_avg as number | undefined,
  };
}

/**
 * Fetch team form
 */
export async function fetchTeamForm(
  teamId: number,
  matchesCount: number = 5
): Promise<TeamForm> {
  const rawForm = await fetchApi<Record<string, unknown>>(`/api/v1/matches/teams/${teamId}/form?matches_count=${matchesCount}`);
  return transformTeamForm(rawForm);
}

/**
 * Transform API head-to-head response (snake_case) to frontend format (camelCase)
 */
function transformHeadToHead(apiH2H: Record<string, unknown>): { matches: Match[]; homeWins: number; draws: number; awayWins: number } {
  const matches = Array.isArray(apiH2H.matches)
    ? apiH2H.matches.map((m: Record<string, unknown>) => ({
        id: (m.id ?? 0) as number,
        homeTeam: (m.home_team ?? m.homeTeam) as string,
        awayTeam: (m.away_team ?? m.awayTeam) as string,
        competition: m.competition as string,
        competitionCode: (m.competition_code ?? "") as string,
        matchDate: (m.date ?? m.matchDate) as string,
        status: "finished" as const,
        homeScore: (m.home_score ?? m.homeScore) as number | undefined,
        awayScore: (m.away_score ?? m.awayScore) as number | undefined,
      }))
    : [];

  return {
    matches,
    homeWins: (apiH2H.home_wins ?? apiH2H.homeWins ?? 0) as number,
    draws: (apiH2H.draws ?? 0) as number,
    awayWins: (apiH2H.away_wins ?? apiH2H.awayWins ?? 0) as number,
  };
}

/**
 * Fetch head-to-head history
 */
export async function fetchHeadToHead(
  matchId: number,
  limit: number = 10
): Promise<{ matches: Match[]; homeWins: number; draws: number; awayWins: number }> {
  const rawH2H = await fetchApi<Record<string, unknown>>(`/api/v1/matches/${matchId}/head-to-head?limit=${limit}`);
  return transformHeadToHead(rawH2H);
}

// API response type for prediction stats (snake_case from backend)
interface ApiPredictionStats {
  total_predictions: number;
  correct_predictions: number;
  accuracy: number;
  roi_simulated: number;
  by_competition: Record<string, {
    total?: number;
    predictions?: number;
    correct: number;
    accuracy: number;
  }>;
  by_bet_type: Record<string, {
    total?: number;
    predictions?: number;
    correct: number;
    accuracy: number;
    avg_value?: number;
  }>;
  last_updated?: string;
}

/**
 * Transform API prediction stats response (snake_case) to frontend format (camelCase)
 */
function transformPredictionStats(apiStats: ApiPredictionStats): PredictionStats {
  // Transform by_competition entries
  const byCompetition: PredictionStats['byCompetition'] = {};
  if (apiStats.by_competition) {
    for (const [code, data] of Object.entries(apiStats.by_competition)) {
      byCompetition[code] = {
        total: data.total,
        predictions: data.predictions,
        correct: data.correct,
        accuracy: data.accuracy,
      };
    }
  }

  // Transform by_bet_type entries
  const byBetType: PredictionStats['byBetType'] = {};
  if (apiStats.by_bet_type) {
    for (const [type, data] of Object.entries(apiStats.by_bet_type)) {
      byBetType[type] = {
        total: data.total,
        predictions: data.predictions,
        correct: data.correct,
        accuracy: data.accuracy,
        avgValue: data.avg_value,
      };
    }
  }

  return {
    totalPredictions: apiStats.total_predictions ?? 0,
    correctPredictions: apiStats.correct_predictions ?? 0,
    accuracy: apiStats.accuracy ?? 0,
    roiSimulated: apiStats.roi_simulated ?? 0,
    byCompetition,
    byBetType,
    lastUpdated: apiStats.last_updated,
  };
}

/**
 * Fetch prediction statistics
 */
export async function fetchPredictionStats(days: number = 30): Promise<PredictionStats> {
  const rawStats = await fetchApi<ApiPredictionStats>(`/api/v1/predictions/stats?days=${days}`);
  return transformPredictionStats(rawStats);
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; version: string }> {
  return fetchApi("/health");
}

/**
 * Transform API standings response (snake_case) to frontend format (camelCase)
 */
function transformStandings(apiStandings: Record<string, unknown>): Standings {
  const standings = Array.isArray(apiStandings.standings)
    ? (apiStandings.standings as Record<string, unknown>[]).map((team) => ({
        position: (team.position as number) ?? 0,
        team_id: (team.team_id ?? team.teamId ?? 0) as number,
        team_name: (team.team_name ?? team.teamName ?? "") as string,
        team_logo_url: (team.team_logo_url ?? team.teamLogoUrl ?? null) as string | null | undefined,
        played: (team.played ?? team.playedGames ?? 0) as number,
        won: (team.won ?? 0) as number,
        drawn: (team.drawn ?? team.draw ?? 0) as number,
        lost: (team.lost ?? 0) as number,
        goals_for: (team.goals_for ?? team.goalsFor ?? 0) as number,
        goals_against: (team.goals_against ?? team.goalsAgainst ?? 0) as number,
        goal_difference: (team.goal_difference ?? team.goalDifference ?? 0) as number,
        points: (team.points ?? 0) as number,
      }))
    : [];

  return {
    competition_code: (apiStandings.competition_code ?? apiStandings.competitionCode ?? "") as string,
    competition_name: (apiStandings.competition_name ?? apiStandings.competitionName ?? "") as string,
    standings,
    last_updated: (apiStandings.last_updated ?? apiStandings.lastUpdated) as string | undefined,
  };
}

/**
 * Fetch league standings
 */
export async function fetchStandings(competitionCode: string): Promise<Standings> {
  const rawStandings = await fetchApi<Record<string, unknown>>(`/api/v1/matches/standings/${competitionCode}`);
  return transformStandings(rawStandings);
}
