/**
 * Types for prediction statistics API responses
 */

export interface CompetitionStats {
  total?: number;
  correct: number;
  accuracy: number;
  predictions?: number; // Alias for total
}

export interface BetTypeStats {
  total?: number;
  correct: number;
  accuracy: number;
  predictions?: number; // Alias for total
  avgValue?: number;
}

export interface PredictionStatsResponse {
  totalPredictions: number;
  correctPredictions: number;
  accuracy: number;
  roiSimulated: number;
  byCompetition: Record<string, CompetitionStats>;
  byBetType: Record<string, BetTypeStats>;
}

export interface CompetitionChartData {
  name: string;
  code: string;
  predictions: number;
  correct: number;
  accuracy: number;
  trend?: "up" | "down" | "neutral";
}

export interface HistoryDataPoint {
  date: string;
  accuracy: number;
  predictions: number;
  cumulative: number;
}

export interface ConfidenceData {
  range: string;
  count: number;
  accuracy: number;
  color: string;
}

export interface BetTypeData {
  name: string;
  correct: number;
  total: number;
  accuracy: number;
  avgValue?: number;
}
