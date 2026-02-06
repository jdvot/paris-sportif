import React, { useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  TouchableOpacity,
  RefreshControl,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/api";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { colors, spacing, fontSize } from "../constants/theme";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PredictionProbabilities {
  home_win: number;
  draw: number;
  away_win: number;
}

interface PredictionResponse {
  match_id: number;
  home_team: string;
  away_team: string;
  competition: string;
  match_date: string;
  probabilities: PredictionProbabilities;
  recommended_bet: "home_win" | "draw" | "away_win";
  confidence: number;
  value_score: number;
  explanation: string;
}

interface DailyPickResponse {
  rank: number;
  prediction: PredictionResponse;
  pick_score: number;
}

interface DailyPicksResponse {
  date: string;
  picks: DailyPickResponse[];
  total_matches_analyzed: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBetLabel(bet: string): string {
  switch (bet) {
    case "home_win":
      return "Home Win";
    case "draw":
      return "Draw";
    case "away_win":
      return "Away Win";
    default:
      return bet;
  }
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.6) return colors.success;
  if (confidence >= 0.5) return colors.warning;
  return colors.danger;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function ConfidenceBar({ confidence }: { confidence: number }) {
  const barColor = getConfidenceColor(confidence);
  const percentage = Math.round(confidence * 100);

  return (
    <View style={barStyles.container}>
      <View style={barStyles.labelRow}>
        <Text style={barStyles.label}>Confidence</Text>
        <Text style={[barStyles.percentage, { color: barColor }]}>
          {percentage}%
        </Text>
      </View>
      <View style={barStyles.track}>
        <View
          style={[
            barStyles.fill,
            { width: `${percentage}%`, backgroundColor: barColor },
          ]}
        />
      </View>
    </View>
  );
}

const barStyles = StyleSheet.create({
  container: {
    marginTop: spacing.sm,
  },
  labelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing.xs,
  },
  label: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
  },
  percentage: {
    fontSize: fontSize.xs,
    fontWeight: "700",
  },
  track: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.surfaceLight,
    overflow: "hidden",
  },
  fill: {
    height: 6,
    borderRadius: 3,
  },
});

function PickCard({ item }: { item: DailyPickResponse }) {
  const { prediction, rank } = item;
  const probability =
    prediction.probabilities[prediction.recommended_bet] ?? 0;

  return (
    <Card style={styles.pickCard}>
      <View style={styles.cardHeader}>
        <Badge label={`#${rank}`} color={colors.primary} textColor={colors.white} />
        <Badge label={prediction.competition} />
      </View>

      <Text style={styles.teams}>
        {prediction.home_team} vs {prediction.away_team}
      </Text>

      <View style={styles.betRow}>
        <Badge
          label={formatBetLabel(prediction.recommended_bet)}
          color={getConfidenceColor(probability)}
          textColor={colors.white}
        />
        <Text style={styles.probability}>
          {Math.round(probability * 100)}% prob.
        </Text>
      </View>

      <ConfidenceBar confidence={prediction.confidence} />

      <Text style={styles.dateText}>{formatDate(prediction.match_date)}</Text>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export function PicksScreen() {
  const { data, isLoading, error, refetch, isRefetching } = useQuery<DailyPicksResponse>({
    queryKey: ["dailyPicks"],
    queryFn: () => apiClient.get("/predictions/daily").then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const onRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading daily picks...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Failed to load picks</Text>
        <Text style={styles.errorDetail}>
          {error instanceof Error ? error.message : "Unknown error"}
        </Text>
        <TouchableOpacity style={styles.retryButton} onPress={() => refetch()}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const picks = data?.picks ?? [];

  if (picks.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyTitle}>No picks today</Text>
        <Text style={styles.emptySubtitle}>
          Check back later for today's top predictions
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={picks}
        keyExtractor={(item) => String(item.prediction.match_id)}
        renderItem={({ item }) => <PickCard item={item} />}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={onRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
        ListHeaderComponent={
          <Text style={styles.headerInfo}>
            {data?.total_matches_analyzed ?? 0} matches analyzed for{" "}
            {data?.date ?? "today"}
          </Text>
        }
      />
    </View>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
  },
  listContent: {
    padding: spacing.md,
    gap: spacing.md,
  },
  headerInfo: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  pickCard: {
    marginBottom: spacing.xs,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  teams: {
    fontSize: fontSize.lg,
    fontWeight: "bold",
    color: colors.text,
    marginBottom: spacing.sm,
  },
  betRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  probability: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
  },
  dateText: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  loadingText: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: spacing.md,
  },
  errorText: {
    fontSize: fontSize.lg,
    fontWeight: "bold",
    color: colors.danger,
    marginBottom: spacing.sm,
  },
  errorDetail: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginBottom: spacing.lg,
    textAlign: "center",
  },
  retryButton: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: spacing.sm + 2,
    paddingHorizontal: spacing.xl,
  },
  retryText: {
    color: colors.white,
    fontSize: fontSize.md,
    fontWeight: "600",
  },
  emptyTitle: {
    fontSize: fontSize.xl,
    fontWeight: "bold",
    color: colors.text,
    marginBottom: spacing.sm,
  },
  emptySubtitle: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    textAlign: "center",
  },
});
