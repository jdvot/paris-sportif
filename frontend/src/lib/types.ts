/**
 * Type definitions for the WinRate AI application
 */

export interface Match {
  id: number;
  homeTeam: string;
  awayTeam: string;
  competition: string;
  competitionCode: string;
  matchDate: string;
  status: "scheduled" | "live" | "finished" | "postponed";
  homeScore?: number;
  awayScore?: number;
  matchday?: number;
}

export interface Probabilities {
  homeWin: number;
  draw: number;
  awayWin: number;
}

export interface Prediction {
  // Legacy format (frontend mock data)
  homeProb?: number;
  drawProb?: number;
  awayProb?: number;
  // New format (backend API)
  probabilities?: Probabilities;
  recommendedBet: "home" | "draw" | "away" | "home_win" | "away_win";
  confidence: number;
  valueScore: number;
}

export interface DailyPick {
  rank: number;
  match: Pick<Match, "id" | "homeTeam" | "awayTeam" | "competition" | "matchDate">;
  prediction: Prediction;
  explanation: string;
  keyFactors: string[];
  riskFactors?: string[];
  pickScore?: number;
}

export interface DailyPicksResponse {
  date: string;
  picks: DailyPick[];
  totalMatchesAnalyzed: number;
}

export interface TeamFormMatch {
  opponent: string;
  result: "W" | "D" | "L";
  score: string;
  homeAway: "H" | "A";
  date: string;
}

export interface TeamForm {
  teamId: number;
  teamName: string;
  lastMatches: TeamFormMatch[];
  formString: string;
  pointsLast5: number;
  goalsScoredAvg: number;
  goalsConcededAvg: number;
  cleanSheets: number;
  xgForAvg?: number;
  xgAgainstAvg?: number;
}

export interface ModelContribution {
  homeProb?: number;
  drawProb?: number;
  awayProb?: number;
  homeWin?: number;
  draw?: number;
  awayWin?: number;
  weight?: number;
}

export interface LLMAdjustments {
  injuryImpactHome: number;
  injuryImpactAway: number;
  sentimentHome: number;
  sentimentAway: number;
  tacticalEdge: number;
  totalAdjustment: number;
  reasoning: string;
}

export interface DetailedPrediction extends Prediction {
  matchId?: number;
  homeTeam?: string;
  awayTeam?: string;
  matchDate?: string;
  explanation: string;
  keyFactors: string[];
  riskFactors: string[];
  modelContributions?: {
    poisson: ModelContribution;
    elo: ModelContribution;
    xgModel?: ModelContribution;
    xgboost?: ModelContribution;
  };
  llmAdjustments?: LLMAdjustments;
  expectedHomeGoals?: number;
  expectedAwayGoals?: number;
  createdAt?: string;
}

export interface PredictionStats {
  totalPredictions: number;
  correctPredictions: number;
  accuracy: number;
  roiSimulated: number;
  byCompetition: Record<string, {
    total?: number;
    predictions?: number;
    correct: number;
    accuracy: number;
  }>;
  byBetType: Record<string, {
    total?: number;
    predictions?: number;
    correct: number;
    accuracy: number;
    avgValue?: number;
  }>;
  lastUpdated?: string;
}

export interface Competition {
  id: number;
  name: string;
  code: string;
  country?: string;
  emblemUrl?: string;
}

export interface StandingTeam {
  position: number;
  team_id: number;
  team_name: string;
  team_logo_url?: string | null;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
}

export interface Standings {
  competition_code: string;
  competition_name: string;
  standings: StandingTeam[];
  last_updated?: string;
}
