import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/api";
import { colors, spacing, fontSize } from "../constants/theme";

type Circuit = "ATP" | "WTA";
type Surface = "All" | "Hard" | "Clay" | "Grass" | "Indoor";

interface TennisPrediction {
  player1_win_probability: number;
  player2_win_probability: number;
  predicted_winner: string;
  confidence: number;
}

interface TennisMatch {
  id: number;
  player1: string;
  player2: string;
  tournament: string;
  round: string;
  surface: string;
  circuit: string;
  date: string;
  score?: string | null;
  status: string;
  prediction?: TennisPrediction | null;
}

const CIRCUITS: Circuit[] = ["ATP", "WTA"];
const SURFACES: Surface[] = ["All", "Hard", "Clay", "Grass", "Indoor"];

function getSurfaceColor(surface: string): string {
  switch (surface.toLowerCase()) {
    case "clay":
      return "#e07c4f";
    case "grass":
      return "#22c55e";
    case "hard":
      return "#3b82f6";
    case "indoor":
      return "#a855f7";
    default:
      return colors.textSecondary;
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function TennisMatchCard({ match }: { match: TennisMatch }) {
  const surfaceColor = getSurfaceColor(match.surface);

  return (
    <View style={cardStyles.container}>
      <View style={cardStyles.header}>
        <Text style={cardStyles.tournament}>{match.tournament}</Text>
        <View
          style={[
            cardStyles.surfaceBadge,
            { backgroundColor: surfaceColor + "20" },
          ]}
        >
          <Text style={[cardStyles.surfaceText, { color: surfaceColor }]}>
            {match.surface}
          </Text>
        </View>
      </View>

      <View style={cardStyles.roundRow}>
        <Text style={cardStyles.roundText}>{match.round}</Text>
        <Text style={cardStyles.dateText}>{formatDate(match.date)}</Text>
      </View>

      <View style={cardStyles.playersRow}>
        <View style={cardStyles.playerColumn}>
          <Text style={cardStyles.playerName}>{match.player1}</Text>
        </View>
        <Text style={cardStyles.vsText}>vs</Text>
        <View style={cardStyles.playerColumn}>
          <Text style={[cardStyles.playerName, { textAlign: "right" }]}>
            {match.player2}
          </Text>
        </View>
      </View>

      {match.score && (
        <View style={cardStyles.scoreRow}>
          <Text style={cardStyles.scoreText}>{match.score}</Text>
        </View>
      )}

      {match.prediction && (
        <View style={cardStyles.predictionRow}>
          <View style={cardStyles.predictionLeft}>
            <Text style={cardStyles.predictionLabel}>Prediction:</Text>
            <Text style={cardStyles.predictedWinner}>
              {match.prediction.predicted_winner}
            </Text>
          </View>
          <View style={cardStyles.confidenceBadge}>
            <Text style={cardStyles.confidenceText}>
              {Math.round(match.prediction.confidence * 100)}%
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}

const cardStyles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    marginHorizontal: spacing.md,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.xs,
  },
  tournament: {
    color: colors.primary,
    fontSize: fontSize.xs,
    fontWeight: "600",
    flex: 1,
  },
  surfaceBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 6,
  },
  surfaceText: {
    fontSize: fontSize.xs,
    fontWeight: "600",
  },
  roundRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  roundText: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
  },
  dateText: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
  },
  playersRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.sm,
  },
  playerColumn: {
    flex: 1,
  },
  playerName: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: "600",
  },
  vsText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginHorizontal: spacing.sm,
  },
  scoreRow: {
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  scoreText: {
    color: colors.warning,
    fontSize: fontSize.sm,
    fontWeight: "600",
  },
  predictionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.sm,
  },
  predictionLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  predictionLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
  },
  predictedWinner: {
    color: colors.success,
    fontSize: fontSize.sm,
    fontWeight: "600",
  },
  confidenceBadge: {
    backgroundColor: colors.primary + "20",
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 6,
  },
  confidenceText: {
    color: colors.primary,
    fontSize: fontSize.xs,
    fontWeight: "600",
  },
});

export function TennisScreen() {
  const [selectedCircuit, setSelectedCircuit] = useState<Circuit>("ATP");
  const [selectedSurface, setSelectedSurface] = useState<Surface>("All");

  const {
    data: matches,
    isLoading,
    error,
    refetch,
    isRefetching,
  } = useQuery<TennisMatch[]>({
    queryKey: ["tennis-matches", selectedCircuit, selectedSurface],
    queryFn: async () => {
      const params: Record<string, string> = { circuit: selectedCircuit };
      if (selectedSurface !== "All") {
        params.surface = selectedSurface.toLowerCase();
      }
      const res = await apiClient.get("/tennis/matches", { params });
      return res.data;
    },
  });

  const onRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const filteredMatches = matches ?? [];

  const renderItem = useCallback(
    ({ item }: { item: TennisMatch }) => <TennisMatchCard match={item} />,
    []
  );

  const keyExtractor = useCallback(
    (item: TennisMatch) => item.id.toString(),
    []
  );

  return (
    <View style={styles.container}>
      {/* Circuit Tabs */}
      <View style={styles.circuitTabs}>
        {CIRCUITS.map((circuit) => (
          <TouchableOpacity
            key={circuit}
            style={[
              styles.circuitTab,
              selectedCircuit === circuit && styles.circuitTabActive,
            ]}
            onPress={() => setSelectedCircuit(circuit)}
          >
            <Text
              style={[
                styles.circuitTabText,
                selectedCircuit === circuit && styles.circuitTabTextActive,
              ]}
            >
              {circuit}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Surface Filters */}
      <FlatList
        horizontal
        data={SURFACES}
        keyExtractor={(item) => item}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.surfaceFilters}
        renderItem={({ item: surface }) => (
          <TouchableOpacity
            style={[
              styles.surfaceChip,
              selectedSurface === surface && styles.surfaceChipActive,
            ]}
            onPress={() => setSelectedSurface(surface)}
          >
            <Text
              style={[
                styles.surfaceChipText,
                selectedSurface === surface && styles.surfaceChipTextActive,
              ]}
            >
              {surface}
            </Text>
          </TouchableOpacity>
        )}
      />

      {/* Match List */}
      {isLoading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading tennis matches...</Text>
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>Failed to load matches</Text>
          <TouchableOpacity style={styles.retryButton} onPress={onRefresh}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={filteredMatches}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={
            filteredMatches.length === 0
              ? styles.emptyContainer
              : styles.listContent
          }
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={onRefresh}
              tintColor={colors.primary}
            />
          }
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Text style={styles.emptyTitle}>No matches found</Text>
              <Text style={styles.emptySubtext}>
                No {selectedCircuit} matches
                {selectedSurface !== "All"
                  ? ` on ${selectedSurface.toLowerCase()}`
                  : ""}{" "}
                available right now
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  circuitTabs: {
    flexDirection: "row",
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    gap: spacing.sm,
  },
  circuitTab: {
    flex: 1,
    paddingVertical: spacing.sm + 2,
    borderRadius: 10,
    backgroundColor: colors.surface,
    alignItems: "center",
  },
  circuitTabActive: {
    backgroundColor: colors.primary,
  },
  circuitTabText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    fontWeight: "600",
  },
  circuitTabTextActive: {
    color: colors.white,
  },
  surfaceFilters: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  surfaceChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    borderRadius: 20,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  surfaceChipActive: {
    backgroundColor: colors.primary + "20",
    borderColor: colors.primary,
  },
  surfaceChipText: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
    fontWeight: "500",
  },
  surfaceChipTextActive: {
    color: colors.primary,
  },
  listContent: {
    paddingTop: spacing.xs,
    paddingBottom: spacing.lg,
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: spacing.lg,
  },
  loadingText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginTop: spacing.md,
  },
  errorText: {
    color: colors.danger,
    fontSize: fontSize.md,
    fontWeight: "600",
    marginBottom: spacing.md,
  },
  retryButton: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: 8,
  },
  retryText: {
    color: colors.white,
    fontSize: fontSize.sm,
    fontWeight: "600",
  },
  emptyContainer: {
    flex: 1,
  },
  emptyState: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: spacing.xl,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: "bold",
    marginBottom: spacing.sm,
  },
  emptySubtext: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    textAlign: "center",
  },
});
