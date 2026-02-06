import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  RefreshControl,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/api";
import { Card } from "../components/Card";
import { colors, spacing, fontSize } from "../constants/theme";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PredictionStatsResponse {
  total_predictions: number;
  verified_predictions: number;
  correct_predictions: number;
  accuracy: number;
  roi_simulated: number;
  last_updated: string;
}

interface PeriodOption {
  key: number;
  label: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PERIOD_OPTIONS: PeriodOption[] = [
  { key: 7, label: "7d" },
  { key: 30, label: "30d" },
  { key: 90, label: "90d" },
];

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function PeriodChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[styles.chip, active && styles.chipActive]}
      onPress={onPress}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

function StatCard({
  title,
  value,
  valueColor,
}: {
  title: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <Card style={styles.statCard}>
      <Text style={styles.statTitle}>{title}</Text>
      <Text style={[styles.statValue, valueColor ? { color: valueColor } : undefined]}>
        {value}
      </Text>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getWinRateColor(rate: number): string {
  if (rate >= 55) return colors.success;
  if (rate >= 45) return colors.warning;
  return colors.danger;
}

function getRoiColor(roi: number): string {
  if (roi > 0) return colors.success;
  if (roi === 0) return colors.textSecondary;
  return colors.danger;
}

function formatRoi(roi: number): string {
  const sign = roi >= 0 ? "+" : "";
  return `${sign}${roi.toFixed(1)}%`;
}

function formatProfit(roi: number, totalPredictions: number): string {
  // Simulate profit based on 10 EUR flat bets
  const totalStaked = totalPredictions * 10;
  const profit = (roi / 100) * totalStaked;
  const sign = profit >= 0 ? "+" : "";
  return `${sign}${profit.toFixed(0)} EUR`;
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export function DashboardScreen() {
  const [days, setDays] = useState(30);

  const { data, isLoading, error, refetch, isRefetching } =
    useQuery<PredictionStatsResponse>({
      queryKey: ["predictionStats", days],
      queryFn: () =>
        apiClient
          .get("/predictions/stats", { params: { days } })
          .then((r) => r.data),
      staleTime: 5 * 60 * 1000,
    });

  const onRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading stats...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Failed to load stats</Text>
        <Text style={styles.errorDetail}>
          {error instanceof Error ? error.message : "Unknown error"}
        </Text>
        <TouchableOpacity style={styles.retryButton} onPress={() => refetch()}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const totalPredictions = data?.total_predictions ?? 0;
  const accuracy = data?.accuracy ?? 0;
  const winRatePercent = Math.round(accuracy * 100);
  const roi = data?.roi_simulated ?? 0;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={onRefresh}
          tintColor={colors.primary}
          colors={[colors.primary]}
        />
      }
    >
      <View style={styles.periodRow}>
        {PERIOD_OPTIONS.map((opt) => (
          <PeriodChip
            key={opt.key}
            label={opt.label}
            active={days === opt.key}
            onPress={() => setDays(opt.key)}
          />
        ))}
      </View>

      <View style={styles.grid}>
        <StatCard
          title="Total Predictions"
          value={String(totalPredictions)}
        />
        <StatCard
          title="Win Rate"
          value={`${winRatePercent}%`}
          valueColor={getWinRateColor(winRatePercent)}
        />
        <StatCard
          title="ROI"
          value={formatRoi(roi)}
          valueColor={getRoiColor(roi)}
        />
        <StatCard
          title="Est. Profit"
          value={formatProfit(roi, totalPredictions)}
          valueColor={getRoiColor(roi)}
        />
      </View>

      {data?.last_updated && (
        <Text style={styles.updatedText}>
          Last updated:{" "}
          {new Date(data.last_updated).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Text>
      )}
    </ScrollView>
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
  scrollContent: {
    padding: spacing.md,
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
  },
  periodRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 20,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  chipText: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    fontWeight: "500",
  },
  chipTextActive: {
    color: colors.white,
    fontWeight: "600",
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
  },
  statCard: {
    width: "47%",
    flexGrow: 1,
    alignItems: "center",
    paddingVertical: spacing.lg,
  },
  statTitle: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  statValue: {
    fontSize: fontSize.xxl,
    fontWeight: "bold",
    color: colors.text,
  },
  updatedText: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    textAlign: "center",
    marginTop: spacing.lg,
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
});
