"use client";

import { useState, useMemo, useCallback } from "react";
import { Calendar, Dribbble, AlertTriangle } from "lucide-react";
import { format } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { useTranslations, useLocale } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { customInstance } from "@/lib/api/custom-instance";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { isAuthError } from "@/lib/utils";

// TypeScript interfaces for Basketball API responses
interface BasketballTeam {
  id: number;
  name: string;
  logo_url?: string;
}

interface QuarterScores {
  q1_home?: number;
  q1_away?: number;
  q2_home?: number;
  q2_away?: number;
  q3_home?: number;
  q3_away?: number;
  q4_home?: number;
  q4_away?: number;
  ot_home?: number;
  ot_away?: number;
}

interface BasketballPrediction {
  home_win_prob: number;
  away_win_prob: number;
  confidence: number;
  spread?: number;
  over_under?: number;
  recommended_bet?: string;
}

interface BasketballMatch {
  id: number;
  home_team: BasketballTeam;
  away_team: BasketballTeam;
  league: "NBA" | "Euroleague";
  match_date: string;
  status: "scheduled" | "live" | "finished";
  home_score?: number;
  away_score?: number;
  quarter_scores?: QuarterScores;
  home_back_to_back?: boolean;
  away_back_to_back?: boolean;
  prediction?: BasketballPrediction;
}

interface BasketballMatchesResponse {
  matches: BasketballMatch[];
  total: number;
}

type League = "all" | "NBA" | "Euroleague";

const LEAGUE_COLORS: Record<string, string> = {
  NBA: "bg-red-500/20 text-red-600 dark:text-red-400",
  Euroleague: "bg-blue-500/20 text-blue-600 dark:text-blue-400",
};

export default function BasketballPage() {
  const t = useTranslations("basketball");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const dateLocale = locale === "fr" ? fr : enUS;

  const [league, setLeague] = useState<League>("all");

  const { data: response, isLoading, error } = useQuery({
    queryKey: ["basketball-matches", league],
    queryFn: () =>
      customInstance<{ data: BasketballMatchesResponse; status: number }>(
        "/api/v1/basketball/matches",
        {
          params: {
            league: league !== "all" ? league : undefined,
          },
        }
      ),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  const matches = useMemo(() => {
    return (response?.data as BasketballMatchesResponse | undefined)?.matches || [];
  }, [response?.data]);

  const filteredMatches = useMemo(() => {
    if (league === "all") return matches;
    return matches.filter((m) => m.league === league);
  }, [matches, league]);

  const handleLeagueChange = useCallback((value: string) => {
    setLeague(value as League);
  }, []);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 75) return "text-emerald-500";
    if (confidence >= 60) return "text-yellow-500";
    return "text-orange-500";
  };

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <section className="text-center py-6 sm:py-8 px-4">
        <div className="flex items-center justify-center gap-2 mb-2 sm:mb-3">
          <Dribbble className="w-7 h-7 sm:w-8 sm:h-8 text-primary-500" />
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 dark:text-white">
            {t("title")}
          </h1>
        </div>
        <p className="text-gray-600 dark:text-slate-300 text-sm sm:text-base">
          {t("subtitle")}
        </p>
      </section>

      {/* Filters */}
      <section className="px-4 sm:px-0">
        <Tabs defaultValue="all" onValueChange={handleLeagueChange}>
          <TabsList>
            <TabsTrigger value="all">{tCommon("all")}</TabsTrigger>
            <TabsTrigger value="NBA">{t("nba")}</TabsTrigger>
            <TabsTrigger value="Euroleague">{t("euroleague")}</TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="mt-4">
            <MatchList
              matches={filteredMatches}
              isLoading={isLoading}
              error={error}
              t={t}
              tCommon={tCommon}
              dateLocale={dateLocale}
              getConfidenceColor={getConfidenceColor}
            />
          </TabsContent>
          <TabsContent value="NBA" className="mt-4">
            <MatchList
              matches={filteredMatches}
              isLoading={isLoading}
              error={error}
              t={t}
              tCommon={tCommon}
              dateLocale={dateLocale}
              getConfidenceColor={getConfidenceColor}
            />
          </TabsContent>
          <TabsContent value="Euroleague" className="mt-4">
            <MatchList
              matches={filteredMatches}
              isLoading={isLoading}
              error={error}
              t={t}
              tCommon={tCommon}
              dateLocale={dateLocale}
              getConfidenceColor={getConfidenceColor}
            />
          </TabsContent>
        </Tabs>
      </section>
    </div>
  );
}

function MatchList({
  matches,
  isLoading,
  error,
  t,
  tCommon,
  dateLocale,
  getConfidenceColor,
}: {
  matches: BasketballMatch[];
  isLoading: boolean;
  error: Error | null;
  t: ReturnType<typeof useTranslations>;
  tCommon: ReturnType<typeof useTranslations>;
  dateLocale: typeof fr | typeof enUS;
  getConfidenceColor: (confidence: number) => string;
}) {
  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="border-gray-200 dark:border-slate-700">
            <CardContent className="p-4 sm:p-6">
              <div className="animate-pulse space-y-3">
                <div className="flex items-center justify-between">
                  <div className="h-5 bg-gray-200 dark:bg-slate-700 rounded w-16" />
                  <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-24" />
                </div>
                <div className="flex items-center justify-between">
                  <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-32" />
                  <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-12" />
                </div>
                <div className="flex items-center justify-between">
                  <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-32" />
                  <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-12" />
                </div>
                <div className="flex items-center justify-between">
                  <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-20" />
                  <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-20" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // Error state
  if (error && !isAuthError(error)) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 sm:p-8 text-center">
        <Dribbble className="w-10 sm:w-12 h-10 sm:h-12 text-red-400 mx-auto mb-3 sm:mb-4" />
        <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-2">
          {tCommon("errorLoading")}
        </h3>
        <p className="text-gray-500 dark:text-slate-400 mb-3 sm:mb-4 text-sm sm:text-base">
          {error instanceof Error ? error.message : t("loading")}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors text-sm"
        >
          {tCommon("retry")}
        </button>
      </div>
    );
  }

  // Empty state
  if (matches.length === 0) {
    return (
      <div className="text-center py-8 sm:py-12">
        <Dribbble className="w-10 sm:w-12 h-10 sm:h-12 text-gray-400 dark:text-slate-500 mx-auto mb-3 sm:mb-4" />
        <h3 className="text-base sm:text-lg font-medium text-gray-600 dark:text-slate-300 mb-1">
          {t("noMatches")}
        </h3>
        <p className="text-gray-500 dark:text-slate-400 text-sm">
          {t("loading")}
        </p>
      </div>
    );
  }

  // Match cards
  return (
    <div className="space-y-4">
      {matches.map((match) => (
        <BasketballMatchCard
          key={match.id}
          match={match}
          t={t}
          dateLocale={dateLocale}
          getConfidenceColor={getConfidenceColor}
        />
      ))}
    </div>
  );
}

function BasketballMatchCard({
  match,
  t,
  dateLocale,
  getConfidenceColor,
}: {
  match: BasketballMatch;
  t: ReturnType<typeof useTranslations>;
  dateLocale: typeof fr | typeof enUS;
  getConfidenceColor: (confidence: number) => string;
}) {
  const matchDate = new Date(match.match_date);
  const leagueColor = LEAGUE_COLORS[match.league] || LEAGUE_COLORS.NBA;
  const hasBackToBack = match.home_back_to_back || match.away_back_to_back;
  const isFinished = match.status === "finished";
  const isLive = match.status === "live";

  // Build quarter score display
  const quarterScoreColumns = useMemo(() => {
    if (!match.quarter_scores) return null;
    const qs = match.quarter_scores;
    const quarters: { label: string; home: number | undefined; away: number | undefined }[] = [];

    if (qs.q1_home !== undefined) quarters.push({ label: `${t("quarter")}1`, home: qs.q1_home, away: qs.q1_away });
    if (qs.q2_home !== undefined) quarters.push({ label: `${t("quarter")}2`, home: qs.q2_home, away: qs.q2_away });
    if (qs.q3_home !== undefined) quarters.push({ label: `${t("quarter")}3`, home: qs.q3_home, away: qs.q3_away });
    if (qs.q4_home !== undefined) quarters.push({ label: `${t("quarter")}4`, home: qs.q4_home, away: qs.q4_away });
    if (qs.ot_home !== undefined) quarters.push({ label: t("overtime"), home: qs.ot_home, away: qs.ot_away });

    return quarters.length > 0 ? quarters : null;
  }, [match.quarter_scores, t]);

  return (
    <Card className="border-gray-200 dark:border-slate-700 hover:border-primary-500/50 dark:hover:border-primary-500/50 transition-colors">
      <CardHeader className="pb-2 px-4 sm:px-6 pt-4 sm:pt-6">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Badge className={`${leagueColor} text-xs`} variant="secondary">
              {match.league}
            </Badge>
            {isLive && (
              <Badge className="bg-red-500 text-white animate-pulse text-xs">
                LIVE
              </Badge>
            )}
            {isFinished && (
              <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs" variant="secondary">
                FT
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hasBackToBack && (
              <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30 text-xs" variant="outline">
                <AlertTriangle className="w-3 h-3 mr-1" />
                {t("backToBack")}
              </Badge>
            )}
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
              <Calendar className="w-3.5 h-3.5" />
              <span>{format(matchDate, "dd MMM, HH:mm", { locale: dateLocale })}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-4 sm:px-6 pb-4 sm:pb-6">
        {/* Teams and scores */}
        <div className="space-y-2 py-2">
          {/* Home team */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <p className="font-semibold text-sm sm:text-base text-gray-900 dark:text-white truncate">
                {match.home_team.name}
              </p>
              {match.home_back_to_back && (
                <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 text-[10px] px-1.5 py-0" variant="secondary">
                  B2B
                </Badge>
              )}
            </div>
            {(isFinished || isLive) && match.home_score !== undefined && (
              <span className={`text-lg sm:text-xl font-bold ${isLive ? "text-red-500 animate-pulse" : "text-gray-900 dark:text-white"}`}>
                {match.home_score}
              </span>
            )}
          </div>

          {/* Away team */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <p className="font-semibold text-sm sm:text-base text-gray-900 dark:text-white truncate">
                {match.away_team.name}
              </p>
              {match.away_back_to_back && (
                <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 text-[10px] px-1.5 py-0" variant="secondary">
                  B2B
                </Badge>
              )}
            </div>
            {(isFinished || isLive) && match.away_score !== undefined && (
              <span className={`text-lg sm:text-xl font-bold ${isLive ? "text-red-500 animate-pulse" : "text-gray-900 dark:text-white"}`}>
                {match.away_score}
              </span>
            )}
          </div>
        </div>

        {/* Quarter scores */}
        {quarterScoreColumns && (
          <div className="mt-2 pt-2 border-t border-gray-100 dark:border-slate-700/50">
            <div className="flex items-center gap-0 text-xs overflow-x-auto">
              <div className="w-20 sm:w-24 flex-shrink-0" />
              {quarterScoreColumns.map((q, i) => (
                <div key={i} className="flex-1 text-center font-medium text-gray-500 dark:text-slate-400 min-w-[32px]">
                  {q.label}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-0 text-xs mt-1">
              <div className="w-20 sm:w-24 flex-shrink-0 font-medium text-gray-700 dark:text-slate-300 truncate">
                {match.home_team.name}
              </div>
              {quarterScoreColumns.map((q, i) => (
                <div key={i} className="flex-1 text-center font-semibold text-gray-900 dark:text-white min-w-[32px]">
                  {q.home ?? "-"}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-0 text-xs mt-0.5">
              <div className="w-20 sm:w-24 flex-shrink-0 font-medium text-gray-700 dark:text-slate-300 truncate">
                {match.away_team.name}
              </div>
              {quarterScoreColumns.map((q, i) => (
                <div key={i} className="flex-1 text-center font-semibold text-gray-900 dark:text-white min-w-[32px]">
                  {q.away ?? "-"}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Prediction */}
        {match.prediction && (
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-600 dark:text-slate-400 uppercase tracking-wide">
                {t("prediction")}
              </span>
              <span className={`text-xs font-semibold ${getConfidenceColor(match.prediction.confidence)}`}>
                {t("confidence")}: {match.prediction.confidence}%
              </span>
            </div>

            {/* Probability bars */}
            <div className="space-y-1.5 mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-600 dark:text-slate-400 w-24 sm:w-32 truncate">
                  {match.home_team.name}
                </span>
                <div className="flex-1 bg-gray-200 dark:bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-primary-500 h-2 rounded-full transition-all"
                    style={{ width: `${match.prediction.home_win_prob}%` }}
                  />
                </div>
                <span className="text-xs font-semibold text-gray-900 dark:text-white w-12 text-right">
                  {match.prediction.home_win_prob.toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-600 dark:text-slate-400 w-24 sm:w-32 truncate">
                  {match.away_team.name}
                </span>
                <div className="flex-1 bg-gray-200 dark:bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${match.prediction.away_win_prob}%` }}
                  />
                </div>
                <span className="text-xs font-semibold text-gray-900 dark:text-white w-12 text-right">
                  {match.prediction.away_win_prob.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Spread and Over/Under */}
            <div className="flex items-center gap-3 flex-wrap">
              {match.prediction.spread !== undefined && (
                <div className="flex items-center gap-1.5 bg-gray-100 dark:bg-slate-800 rounded-lg px-3 py-1.5">
                  <span className="text-xs text-gray-500 dark:text-slate-400">{t("spread")}:</span>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">
                    {match.prediction.spread > 0 ? "+" : ""}{match.prediction.spread.toFixed(1)}
                  </span>
                </div>
              )}
              {match.prediction.over_under !== undefined && (
                <div className="flex items-center gap-1.5 bg-gray-100 dark:bg-slate-800 rounded-lg px-3 py-1.5">
                  <span className="text-xs text-gray-500 dark:text-slate-400">{t("overUnder")}:</span>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">
                    {match.prediction.over_under.toFixed(1)}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
