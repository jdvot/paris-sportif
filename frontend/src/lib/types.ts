/**
 * Type definitions for the Paris Sportif application
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

export interface Prediction {
  homeProb: number;
  drawProb: number;
  awayProb: number;
  recommendedBet: "home" | "draw" | "away";
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
}

export interface DailyPicksResponse {
  date: string;
  picks: DailyPick[];
  totalMatchesAnalyzed: number;
}

export interface TeamForm {
  teamId: number;
  teamName: string;
  lastMatches: Match[];
  formString: string;
  pointsLast5: number;
  goalsScoredAvg: number;
  goalsConcededAvg: number;
  cleanSheets: number;
  xgForAvg?: number;
  xgAgainstAvg?: number;
}

export interface ModelContribution {
  homeProb: number;
  drawProb: number;
  awayProb: number;
  weight: number;
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
  explanation: string;
  keyFactors: string[];
  riskFactors: string[];
  modelContributions?: {
    poisson: ModelContribution;
    elo: ModelContribution;
    xg?: ModelContribution;
    xgboost?: ModelContribution;
  };
  llmAdjustments?: LLMAdjustments;
  expectedHomeGoals: number;
  expectedAwayGoals: number;
  createdAt: string;
}

export interface PredictionStats {
  totalPredictions: number;
  correctPredictions: number;
  accuracy: number;
  roiSimulated: number;
  byCompetition: Record<string, {
    predictions: number;
    correct: number;
    accuracy: number;
  }>;
  byBetType: Record<string, {
    predictions: number;
    correct: number;
    accuracy: number;
  }>;
  lastUpdated: string;
}

export interface Competition {
  id: number;
  name: string;
  code: string;
  country?: string;
  emblemUrl?: string;
}
