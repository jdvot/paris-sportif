import React, { useCallback, useMemo, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  TouchableOpacity,
  RefreshControl,
  ScrollView,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { apiClient } from "../lib/api";
import { Card } from "../components/Card";
import { Badge, getStatusColor } from "../components/Badge";
import { colors, spacing, fontSize } from "../constants/theme";
import { RootStackParamList } from "../navigation/RootNavigator";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type NavigationProp = NativeStackNavigationProp<RootStackParamList, "Main">;

interface TeamInfo {
  id: number;
  name: string;
  short_name: string;
  logo_url?: string | null;
}

type MatchStatus = "scheduled" | "live" | "finished" | "postponed";

interface MatchResponse {
  id: number;
  external_id: string;
  home_team: TeamInfo;
  away_team: TeamInfo;
  competition: string;
  competition_code: string;
  match_date: string;
  status: MatchStatus;
  home_score?: number | null;
  away_score?: number | null;
  matchday?: number | null;
}

interface MatchListResponse {
  matches: MatchResponse[];
  total: number;
  page: number;
  per_page: number;
}

type StatusFilter = "all" | "scheduled" | "live" | "finished";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const FILTER_OPTIONS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "scheduled", label: "Scheduled" },
  { key: "live", label: "Live" },
  { key: "finished", label: "Finished" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMatchDate(dateStr: string): string {
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

function FilterChip({
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

function MatchItem({
  match,
  onPress,
}: {
  match: MatchResponse;
  onPress: () => void;
}) {
  const statusColor = getStatusColor(match.status);
  const hasScore =
    match.status === "finished" &&
    match.home_score != null &&
    match.away_score != null;

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
      <Card style={styles.matchCard}>
        <View style={styles.matchHeader}>
          <Badge label={match.competition_code} />
          <Badge
            label={match.status.toUpperCase()}
            color={statusColor}
            textColor={colors.white}
          />
        </View>

        <View style={styles.teamsRow}>
          <View style={styles.teamColumn}>
            <Text style={styles.teamName} numberOfLines={1}>
              {match.home_team.name}
            </Text>
          </View>

          {hasScore ? (
            <Text style={styles.score}>
              {match.home_score} - {match.away_score}
            </Text>
          ) : (
            <Text style={styles.vs}>vs</Text>
          )}

          <View style={styles.teamColumn}>
            <Text
              style={[styles.teamName, styles.awayTeam]}
              numberOfLines={1}
            >
              {match.away_team.name}
            </Text>
          </View>
        </View>

        <View style={styles.matchFooter}>
          <Text style={styles.matchDate}>
            {formatMatchDate(match.match_date)}
          </Text>
          {match.matchday != null && (
            <Text style={styles.matchday}>MD {match.matchday}</Text>
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export function MatchesScreen() {
  const navigation = useNavigation<NavigationProp>();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const { data, isLoading, error, refetch, isRefetching } =
    useQuery<MatchListResponse>({
      queryKey: ["upcomingMatches"],
      queryFn: () =>
        apiClient.get("/matches/upcoming").then((r) => r.data),
      staleTime: 5 * 60 * 1000,
    });

  const onRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const filteredMatches = useMemo(() => {
    const matches = data?.matches ?? [];
    if (statusFilter === "all") return matches;
    return matches.filter((m) => m.status === statusFilter);
  }, [data, statusFilter]);

  const handleMatchPress = useCallback(
    (match: MatchResponse) => {
      navigation.navigate("MatchDetail", { matchId: match.id });
    },
    [navigation],
  );

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading matches...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Failed to load matches</Text>
        <Text style={styles.errorDetail}>
          {error instanceof Error ? error.message : "Unknown error"}
        </Text>
        <TouchableOpacity style={styles.retryButton} onPress={() => refetch()}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.filterContainer}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filterScroll}
        >
          {FILTER_OPTIONS.map((opt) => (
            <FilterChip
              key={opt.key}
              label={opt.label}
              active={statusFilter === opt.key}
              onPress={() => setStatusFilter(opt.key)}
            />
          ))}
        </ScrollView>
      </View>

      <FlatList
        data={filteredMatches}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <MatchItem match={item} onPress={() => handleMatchPress(item)} />
        )}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={onRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>No matches found</Text>
            <Text style={styles.emptySubtitle}>
              {statusFilter !== "all"
                ? `No ${statusFilter} matches available`
                : "No upcoming matches at the moment"}
            </Text>
          </View>
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
  filterContainer: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  filterScroll: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
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
  listContent: {
    padding: spacing.md,
    gap: spacing.md,
  },
  matchCard: {
    marginBottom: spacing.xs,
  },
  matchHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
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
    fontSize: fontSize.md,
    fontWeight: "bold",
    color: colors.text,
  },
  awayTeam: {
    textAlign: "right",
  },
  vs: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginHorizontal: spacing.sm,
  },
  score: {
    fontSize: fontSize.lg,
    fontWeight: "bold",
    color: colors.primary,
    marginHorizontal: spacing.sm,
  },
  matchFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  matchDate: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
  },
  matchday: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
  },
  emptyContainer: {
    paddingVertical: spacing.xl * 2,
    alignItems: "center",
  },
  emptyTitle: {
    fontSize: fontSize.lg,
    fontWeight: "bold",
    color: colors.text,
    marginBottom: spacing.sm,
  },
  emptySubtitle: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    textAlign: "center",
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
