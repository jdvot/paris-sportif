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

type League = "NBA" | "Euroleague";

interface BasketballPrediction {
  home_win_probability: number;
  away_win_probability: number;
  predicted_winner: string;
  confidence: number;
}

interface QuarterScores {
  q1_home: number;
  q1_away: number;
  q2_home: number;
  q2_away: number;
  q3_home: number;
  q3_away: number;
  q4_home: number;
  q4_away: number;
}

interface BasketballMatch {
  id: number;
  home_team: string;
  away_team: string;
  league: string;
  date: string;
  status: string;
  home_score?: number | null;
  away_score?: number | null;
  quarter_scores?: QuarterScores | null;
  is_back_to_back_home?: boolean;
  is_back_to_back_away?: boolean;
  prediction?: BasketballPrediction | null;
}

const LEAGUES: League[] = ["NBA", "Euroleague"];

function getLeagueColor(league: string): string {
  switch (league.toUpperCase()) {
    case "NBA":
      return "#c9082a";
    case "EUROLEAGUE":
      return "#f68b1f";
    default:
      return colors.primary;
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

function QuarterScoresRow({ scores }: { scores: QuarterScores }) {
  const quarters = [
    { label: "Q1", home: scores.q1_home, away: scores.q1_away },
    { label: "Q2", home: scores.q2_home, away: scores.q2_away },
    { label: "Q3", home: scores.q3_home, away: scores.q3_away },
    { label: "Q4", home: scores.q4_home, away: scores.q4_away },
  ];

  return (
    <View style={quarterStyles.container}>
      {quarters.map((q) => (
        <View key={q.label} style={quarterStyles.quarterBox}>
          <Text style={quarterStyles.quarterLabel}>{q.label}</Text>
          <Text style={quarterStyles.quarterScore}>
            {q.home}-{q.away}
          </Text>
        </View>
      ))}
    </View>
  );
}

const quarterStyles = StyleSheet.create({
  container: {
    flexDirection: "row",
    justifyContent: "space-around",
    backgroundColor: colors.surfaceLight,
    borderRadius: 8,
    padding: spacing.sm,
    marginBottom: spacing.sm,
  },
  quarterBox: {
    alignItems: "center",
  },
  quarterLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
    marginBottom: 2,
  },
  quarterScore: {
    color: colors.text,
    fontSize: fontSize.xs,
    fontWeight: "600",
  },
});

function BasketballMatchCard({ match }: { match: BasketballMatch }) {
  const leagueColor = getLeagueColor(match.league);
  const hasBackToBack = match.is_back_to_back_home || match.is_back_to_back_away;

  return (
    <View style={cardStyles.container}>
      <View style={cardStyles.header}>
        <View
          style={[
            cardStyles.leagueBadge,
            { backgroundColor: leagueColor + "20" },
          ]}
        >
          <Text style={[cardStyles.leagueText, { color: leagueColor }]}>
            {match.league}
          </Text>
        </View>
        <Text style={cardStyles.dateText}>{formatDate(match.date)}</Text>
      </View>

      {hasBackToBack && (
        <View style={cardStyles.b2bRow}>
          {match.is_back_to_back_home && (
            <View style={cardStyles.b2bBadge}>
              <Text style={cardStyles.b2bText}>B2B {match.home_team}</Text>
            </View>
          )}
          {match.is_back_to_back_away && (
            <View style={cardStyles.b2bBadge}>
              <Text style={cardStyles.b2bText}>B2B {match.away_team}</Text>
            </View>
          )}
        </View>
      )}

      <View style={cardStyles.teamsRow}>
        <View style={cardStyles.teamColumn}>
          <Text style={cardStyles.teamName}>{match.home_team}</Text>
          <Text style={cardStyles.homeLabel}>HOME</Text>
        </View>

        <View style={cardStyles.scoreColumn}>
          {match.home_score != null && match.away_score != null ? (
            <Text style={cardStyles.scoreText}>
              {match.home_score} - {match.away_score}
            </Text>
          ) : (
            <Text style={cardStyles.vsText}>VS</Text>
          )}
        </View>

        <View style={cardStyles.teamColumn}>
          <Text style={[cardStyles.teamName, { textAlign: "right" }]}>
            {match.away_team}
          </Text>
          <Text style={[cardStyles.homeLabel, { textAlign: "right" }]}>
            AWAY
          </Text>
        </View>
      </View>

      {match.quarter_scores && (
        <QuarterScoresRow scores={match.quarter_scores} />
      )}

      {match.prediction && (
        <View style={cardStyles.predictionRow}>
          <View style={cardStyles.predictionLeft}>
            <Text style={cardStyles.predictionLabel}>Prediction:</Text>
            <Text style={cardStyles.predictedWinner}>
              {match.prediction.predicted_winner}
            </Text>
          </View>
          <View style={cardStyles.probsRow}>
            <Text style={cardStyles.probText}>
              {Math.round(match.prediction.home_win_probability * 100)}%
            </Text>
            <Text style={cardStyles.probSeparator}>-</Text>
            <Text style={cardStyles.probText}>
              {Math.round(match.prediction.away_win_probability * 100)}%
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
    marginBottom: spacing.sm,
  },
  leagueBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 6,
  },
  leagueText: {
    fontSize: fontSize.xs,
    fontWeight: "700",
  },
  dateText: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
  },
  b2bRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  b2bBadge: {
    backgroundColor: colors.warning + "20",
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 6,
  },
  b2bText: {
    color: colors.warning,
    fontSize: fontSize.xs,
    fontWeight: "600",
  },
  teamsRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.sm,
  },
  teamColumn: {
    flex: 1,
  },
  teamName: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: "600",
  },
  homeLabel: {
    color: colors.textSecondary,
    fontSize: 10,
    fontWeight: "500",
    marginTop: 2,
  },
  scoreColumn: {
    paddingHorizontal: spacing.md,
    alignItems: "center",
  },
  scoreText: {
    color: colors.text,
    fontSize: fontSize.xl,
    fontWeight: "bold",
  },
  vsText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
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
  probsRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  probText: {
    color: colors.primary,
    fontSize: fontSize.xs,
    fontWeight: "600",
  },
  probSeparator: {
    color: colors.textSecondary,
    fontSize: fontSize.xs,
    marginHorizontal: spacing.xs,
  },
});

export function BasketballScreen() {
  const [selectedLeague, setSelectedLeague] = useState<League>("NBA");

  const {
    data: matches,
    isLoading,
    error,
    refetch,
    isRefetching,
  } = useQuery<BasketballMatch[]>({
    queryKey: ["basketball-matches", selectedLeague],
    queryFn: async () => {
      const res = await apiClient.get("/basketball/matches", {
        params: { league: selectedLeague },
      });
      return res.data;
    },
  });

  const onRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const matchList = matches ?? [];

  const renderItem = useCallback(
    ({ item }: { item: BasketballMatch }) => (
      <BasketballMatchCard match={item} />
    ),
    []
  );

  const keyExtractor = useCallback(
    (item: BasketballMatch) => item.id.toString(),
    []
  );

  return (
    <View style={styles.container}>
      {/* League Tabs */}
      <View style={styles.leagueTabs}>
        {LEAGUES.map((league) => (
          <TouchableOpacity
            key={league}
            style={[
              styles.leagueTab,
              selectedLeague === league && styles.leagueTabActive,
            ]}
            onPress={() => setSelectedLeague(league)}
          >
            <Text
              style={[
                styles.leagueTabText,
                selectedLeague === league && styles.leagueTabTextActive,
              ]}
            >
              {league}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Match List */}
      {isLoading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading basketball matches...</Text>
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
          data={matchList}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={
            matchList.length === 0 ? styles.emptyContainer : styles.listContent
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
                No {selectedLeague} matches available right now
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
  leagueTabs: {
    flexDirection: "row",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  leagueTab: {
    flex: 1,
    paddingVertical: spacing.sm + 2,
    borderRadius: 10,
    backgroundColor: colors.surface,
    alignItems: "center",
  },
  leagueTabActive: {
    backgroundColor: colors.primary,
  },
  leagueTabText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    fontWeight: "600",
  },
  leagueTabTextActive: {
    color: colors.white,
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
