import { useQuery } from "@tanstack/react-query";
import { customInstance } from "@/lib/api/custom-instance";

export interface CalibrationBucket {
  confidence_range: string;
  predicted_confidence: number;
  actual_win_rate: number;
  count: number;
  overconfidence: number;
}

export interface CalibrationByBet {
  bet_type: string;
  total_predictions: number;
  correct: number;
  accuracy: number;
  avg_confidence: number;
  buckets: CalibrationBucket[];
}

export interface CalibrationResponse {
  total_verified: number;
  overall_accuracy: number;
  overall_calibration_error: number;
  by_bet_type: CalibrationByBet[];
  by_confidence: CalibrationBucket[];
  by_competition: Record<string, {
    total: number;
    correct: number;
    accuracy: number;
    avg_confidence: number;
  }>;
  period: string;
  generated_at: string;
}

export interface CalibrationApiResponse {
  data: CalibrationResponse;
  status: number;
}

export async function getCalibration(days = 90): Promise<CalibrationApiResponse> {
  return customInstance<CalibrationApiResponse>(`/api/v1/predictions/calibration?days=${days}`, {
    method: "GET",
  });
}

export function useGetCalibration(days = 90, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["calibration", days],
    queryFn: () => getCalibration(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}
