import React from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { apiClient } from "../lib/api";
import { colors, spacing, fontSize } from "../constants/theme";
import { RootStackParamList } from "../navigation/RootNavigator";

type Props = NativeStackScreenProps<RootStackParamList, "MatchDetail">;

interface TeamInfo {
  id: number;
  name: string;
  logo?: string;
}

interface Match {
  id: number;
  home_team: string;
  away_team: string;
  home_team_info?: TeamInfo;
  away_team_info?: TeamInfo;
  home_score?: number | null;
  away_score?: number | null;
  status: string;
  competition: string;
  matchday?: number | null;
  date: string;
}

interface Prediction {
  match_id: number;
  predicted_outcome: string;
  home_win_probability: number;
  draw_probability: number;
  away_win_probability: number;
  confidence: number;
  value_score?: number | null;
  key_factors?: string[];
  risk_factors?: string[];
  explanation?: string;
}

function getStatusColor(status: string): string {
  switch (status.toUpperCase()) {
    case "FINISHED":
      return colors.success;
    case "LIVE":
    case "IN_PLAY":
      return colors.danger;
    case "SCHEDULED":
    case "TIMED":
      return colors.primary;
    default:
      return colors.textSecondary;
  }
}

function getStatusLabel(status: string): string {
  switch (status.toUpperCase()) {
    case "FINISHED":
      return "Finished";
    case "LIVE":
    case "IN_PLAY":
      return "Live";
    case "SCHEDULED":
      return "Scheduled";
    case "TIMED":
      return "Timed";
    case "POSTPONED":
      return "Postponed";
    default:
      return status;
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function ProbabilityBar({
  label,
  value,
  isHighest,
}: {
  label: string;
  value: number;
  isHighest: boolean;
}) {
  const percentage = Math.round(value * 100);
  return (
    <View style={probStyles.row}>
      <Text style={probStyles.label}>{label}</Text>
      <View style={probStyles.barBackground}>
        <View
          style={[
            probStyles.barFill,
            {
              width: `${percentage}%`,
              backgroundColor: isHighest ? colors.primary : colors.surfaceLight,
            },
          ]}
        />
      </View>
      <Text
        style={[
          probStyles.percentage,
          isHighest && { color: colors.primary, fontWeight: "700" },
        ]}
      >
        {percentage}%
      </Text>
    </View>
  );
}

const probStyles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  label: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    width: 50,
  },
  barBackground: {
    flex: 1,
    height: 8,
    backgroundColor: colors.surface,
    borderRadius: 4,
    marginHorizontal: spacing.sm,
    overflow: "hidden",
  },
  barFill: {
    height: "100%",
    borderRadius: 4,
  },
  percentage: {
    color: colors.text,
    fontSize: fontSize.sm,
    fontWeight: "600",
    width: 45,
    textAlign: "right",
  },
});

export function MatchDetailScreen({ route }: Props) {
  const { matchId } = route.params;

  const {
    data: match,
    isLoading: matchLoading,
    error: matchError,
  } = useQuery<Match>({
    queryKey: ["match", matchId],
    queryFn: async () => {
      const res = await apiClient.get(`/matches/${matchId}`);
      return res.data;
    },
  });

  const {
    data: prediction,
    isLoading: predictionLoading,
    error: predictionError,
  } = useQuery<Prediction>({
    queryKey: ["prediction", matchId],
    queryFn: async () => {
      const res = await apiClient.get(`/predictions/${matchId}`);
      return res.data;
    },
  });

  const isLoading = matchLoading || predictionLoading;

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading match details...</Text>
      </View>
    );
  }

  if (matchError || !match) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Failed to load match details</Text>
        <Text style={styles.errorSubtext}>
          {matchError instanceof Error ? matchError.message : "Unknown error"}
        </Text>
      </View>
    );
  }

  const highestProb = prediction
    ? Math.max(
        prediction.home_win_probability,
        prediction.draw_probability,
        prediction.away_win_probability
      )
    : 0;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
    >
      {/* Competition & Matchday */}
      <View style={styles.competitionRow}>
        <Text style={styles.competitionText}>{match.competition}</Text>
        {match.matchday != null && (
          <Text style={styles.matchdayText}>Matchday {match.matchday}</Text>
        )}
      </View>

      {/* Status Badge */}
      <View style={styles.statusRow}>
        <View
          style={[
            styles.statusBadge,
            { backgroundColor: getStatusColor(match.status) + "20" },
          ]}
        >
          <View
            style={[
              styles.statusDot,
              { backgroundColor: getStatusColor(match.status) },
            ]}
          />
          <Text
            style={[
              styles.statusText,
              { color: getStatusColor(match.status) },
            ]}
          >
            {getStatusLabel(match.status)}
          </Text>
        </View>
      </View>

      {/* Teams Header */}
      <View style={styles.teamsCard}>
        <View style={styles.teamColumn}>
          <View style={styles.teamLogoPlaceholder}>
            <Text style={styles.teamInitial}>
              {match.home_team.charAt(0)}
            </Text>
          </View>
          <Text style={styles.teamName} numberOfLines={2}>
            {match.home_team}
          </Text>
        </View>

        <View style={styles.scoreColumn}>
          {match.home_score != null && match.away_score != null ? (
            <Text style={styles.scoreText}>
              {match.home_score} - {match.away_score}
            </Text>
          ) : (
            <Text style={styles.vsText}>VS</Text>
          )}
        </View>

        <View style={styles.teamColumn}>
          <View style={styles.teamLogoPlaceholder}>
            <Text style={styles.teamInitial}>
              {match.away_team.charAt(0)}
            </Text>
          </View>
          <Text style={styles.teamName} numberOfLines={2}>
            {match.away_team}
          </Text>
        </View>
      </View>

      {/* Date & Time */}
      <View style={styles.dateTimeRow}>
        <Text style={styles.dateText}>{formatDate(match.date)}</Text>
        <Text style={styles.timeText}>{formatTime(match.date)}</Text>
      </View>

      {/* Prediction Card */}
      {prediction && !predictionError ? (
        <View style={styles.predictionCard}>
          <Text style={styles.sectionTitle}>Prediction</Text>

          {/* Predicted Outcome */}
          <View style={styles.outcomeRow}>
            <Text style={styles.outcomeLabel}>Predicted Outcome</Text>
            <View style={styles.outcomeBadge}>
              <Text style={styles.outcomeValue}>
                {prediction.predicted_outcome}
              </Text>
            </View>
          </View>

          {/* Probability Bars */}
          <View style={styles.probabilitiesSection}>
            <Text style={styles.subsectionTitle}>Probabilities</Text>
            <ProbabilityBar
              label="Home"
              value={prediction.home_win_probability}
              isHighest={prediction.home_win_probability === highestProb}
            />
            <ProbabilityBar
              label="Draw"
              value={prediction.draw_probability}
              isHighest={prediction.draw_probability === highestProb}
            />
            <ProbabilityBar
              label="Away"
              value={prediction.away_win_probability}
              isHighest={prediction.away_win_probability === highestProb}
            />
          </View>

          {/* Confidence & Value */}
          <View style={styles.metricsRow}>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>Confidence</Text>
              <Text style={styles.metricValue}>
                {Math.round(prediction.confidence * 100)}%
              </Text>
            </View>
            {prediction.value_score != null && (
              <View style={styles.metricBox}>
                <Text style={styles.metricLabel}>Value Score</Text>
                <Text
                  style={[
                    styles.metricValue,
                    {
                      color:
                        prediction.value_score > 0
                          ? colors.success
                          : colors.danger,
                    },
                  ]}
                >
                  {prediction.value_score > 0 ? "+" : ""}
                  {prediction.value_score.toFixed(2)}
                </Text>
              </View>
            )}
          </View>

          {/* Key Factors */}
          {prediction.key_factors && prediction.key_factors.length > 0 && (
            <View style={styles.factorsSection}>
              <Text style={styles.subsectionTitle}>Key Factors</Text>
              {prediction.key_factors.map((factor, index) => (
                <View key={index} style={styles.factorRow}>
                  <Text style={styles.bulletSuccess}>+</Text>
                  <Text style={styles.factorText}>{factor}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Risk Factors */}
          {prediction.risk_factors && prediction.risk_factors.length > 0 && (
            <View style={styles.factorsSection}>
              <Text style={styles.subsectionTitle}>Risk Factors</Text>
              {prediction.risk_factors.map((factor, index) => (
                <View key={index} style={styles.factorRow}>
                  <Text style={styles.bulletDanger}>!</Text>
                  <Text style={styles.factorText}>{factor}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Explanation */}
          {prediction.explanation && (
            <View style={styles.explanationSection}>
              <Text style={styles.subsectionTitle}>Analysis</Text>
              <Text style={styles.explanationText}>
                {prediction.explanation}
              </Text>
            </View>
          )}
        </View>
      ) : predictionError ? (
        <View style={styles.noPredictionCard}>
          <Text style={styles.noPredictionText}>
            No prediction available for this match
          </Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  contentContainer: {
    padding: spacing.md,
    paddingBottom: spacing.xl,
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.background,
    padding: spacing.lg,
  },
  loadingText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginTop: spacing.md,
  },
  errorText: {
    color: colors.danger,
    fontSize: fontSize.lg,
    fontWeight: "bold",
    marginBottom: spacing.sm,
  },
  errorSubtext: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    textAlign: "center",
  },
  competitionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  competitionText: {
    color: colors.primary,
    fontSize: fontSize.sm,
    fontWeight: "600",
  },
  matchdayText: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
  },
  statusRow: {
    alignItems: "center",
    marginBottom: spacing.md,
  },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    borderRadius: 20,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: spacing.xs,
  },
  statusText: {
    fontSize: fontSize.xs,
    fontWeight: "600",
  },
  teamsCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
  },
  teamColumn: {
    flex: 1,
    alignItems: "center",
  },
  teamLogoPlaceholder: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  teamInitial: {
    color: colors.text,
    fontSize: fontSize.xl,
    fontWeight: "bold",
  },
  teamName: {
    color: colors.text,
    fontSize: fontSize.sm,
    fontWeight: "600",
    textAlign: "center",
  },
  scoreColumn: {
    paddingHorizontal: spacing.md,
    alignItems: "center",
  },
  scoreText: {
    color: colors.text,
    fontSize: fontSize.xxl,
    fontWeight: "bold",
  },
  vsText: {
    color: colors.textSecondary,
    fontSize: fontSize.lg,
    fontWeight: "600",
  },
  dateTimeRow: {
    alignItems: "center",
    marginBottom: spacing.lg,
  },
  dateText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginBottom: spacing.xs,
  },
  timeText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: "600",
  },
  predictionCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.md,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: "bold",
    marginBottom: spacing.md,
  },
  outcomeRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  outcomeLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
  },
  outcomeBadge: {
    backgroundColor: colors.primary + "20",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 8,
  },
  outcomeValue: {
    color: colors.primary,
    fontSize: fontSize.sm,
    fontWeight: "700",
  },
  probabilitiesSection: {
    marginBottom: spacing.md,
  },
  subsectionTitle: {
    color: colors.text,
    fontSize: fontSize.sm,
    fontWeight: "600",
    marginBottom: spacing.sm,
  },
  metricsRow: {
    flexDirection: "row",
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  metricBox: {
    flex: 1,
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: spacing.md,
    alignItems: "center",
  },
  metricLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
    marginBottom: spacing.xs,
  },
  metricValue: {
    color: colors.text,
    fontSize: fontSize.xl,
    fontWeight: "bold",
  },
  factorsSection: {
    marginBottom: spacing.md,
  },
  factorRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: spacing.xs,
    paddingLeft: spacing.xs,
  },
  bulletSuccess: {
    color: colors.success,
    fontSize: fontSize.md,
    fontWeight: "bold",
    marginRight: spacing.sm,
    width: 16,
  },
  bulletDanger: {
    color: colors.warning,
    fontSize: fontSize.md,
    fontWeight: "bold",
    marginRight: spacing.sm,
    width: 16,
  },
  factorText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    flex: 1,
    lineHeight: 20,
  },
  explanationSection: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.md,
  },
  explanationText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    lineHeight: 22,
  },
  noPredictionCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.lg,
    alignItems: "center",
  },
  noPredictionText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
  },
});
