"use client";

import { useState, useMemo, useCallback } from "react";
import { Calendar, CircleDot } from "lucide-react";
import { format } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { useTranslations, useLocale } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { customInstance } from "@/lib/api/custom-instance";
import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { isAuthError } from "@/lib/utils";

// TypeScript interfaces matching backend TennisMatchResponse
interface TennisPlayer {
  id: number;
  name: string;
  country?: string | null;
  photo_url?: string | null;
  circuit: string;
  atp_ranking?: number | null;
  wta_ranking?: number | null;
  elo_hard: number;
  elo_clay: number;
  elo_grass: number;
  elo_indoor: number;
  win_rate_ytd?: number | null;
}

interface TennisTournament {
  id: number;
  name: string;
  category: string;
  surface: string;
  country?: string | null;
  circuit: string;
}

interface TennisMatch {
  id: number;
  player1: TennisPlayer;
  player2: TennisPlayer;
  tournament: TennisTournament;
  round?: string | null;
  match_date: string;
  surface: string;
  status: string;
  winner_id?: number | null;
  score?: string | null;
  sets_player1?: number | null;
  sets_player2?: number | null;
  odds_player1?: number | null;
  odds_player2?: number | null;
  pred_player1_prob?: number | null;
  pred_player2_prob?: number | null;
  pred_confidence?: number | null;
  pred_explanation?: string | null;
}

interface TennisMatchesResponse {
  matches: TennisMatch[];
  count: number;
}

type Circuit = "all" | "ATP" | "WTA";
type Surface = "all" | "hard" | "clay" | "grass" | "indoor";

const SURFACE_COLORS: Record<string, string> = {
  hard: "bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30",
  clay: "bg-orange-500/20 text-orange-600 dark:text-orange-400 border-orange-500/30",
  grass: "bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30",
  indoor: "bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/30",
};

export default function TennisPage() {
  const t = useTranslations("tennis");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const dateLocale = locale === "fr" ? fr : enUS;

  const [circuit, setCircuit] = useState<Circuit>("all");
  const [surface, setSurface] = useState<Surface>("all");

  const { data: response, isLoading, error } = useQuery({
    queryKey: ["tennis-matches", circuit, surface],
    queryFn: () =>
      customInstance<{ data: TennisMatchesResponse; status: number }>(
        "/api/v1/tennis/matches",
        {
          params: {
            circuit: circuit !== "all" ? circuit : undefined,
            surface: surface !== "all" ? surface : undefined,
          },
        }
      ),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  const matches = useMemo(() => {
    return (response?.data as TennisMatchesResponse | undefined)?.matches || [];
  }, [response?.data]);

  const filteredMatches = useMemo(() => {
    let result = matches;
    if (circuit !== "all") {
      result = result.filter((m) => m.tournament.circuit === circuit);
    }
    if (surface !== "all") {
      result = result.filter((m) => m.surface.toLowerCase() === surface);
    }
    return result;
  }, [matches, circuit, surface]);

  const handleCircuitChange = useCallback((value: string) => {
    setCircuit(value as Circuit);
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
          <CircleDot className="w-7 h-7 sm:w-8 sm:h-8 text-primary-500" />
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
        <Tabs defaultValue="all" onValueChange={handleCircuitChange}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <TabsList>
              <TabsTrigger value="all">{tCommon("all")}</TabsTrigger>
              <TabsTrigger value="ATP">{t("atp")}</TabsTrigger>
              <TabsTrigger value="WTA">{t("wta")}</TabsTrigger>
            </TabsList>

            <Select value={surface} onValueChange={(v) => setSurface(v as Surface)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder={t("allSurfaces")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t("allSurfaces")}</SelectItem>
                <SelectItem value="hard">{t("hard")}</SelectItem>
                <SelectItem value="clay">{t("clay")}</SelectItem>
                <SelectItem value="grass">{t("grass")}</SelectItem>
                <SelectItem value="indoor">{t("indoor")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

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
          <TabsContent value="ATP" className="mt-4">
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
          <TabsContent value="WTA" className="mt-4">
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
  matches: TennisMatch[];
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
                  <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-32" />
                  <div className="h-5 bg-gray-200 dark:bg-slate-700 rounded w-16" />
                </div>
                <div className="flex items-center justify-center gap-4">
                  <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-28" />
                  <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-6" />
                  <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-28" />
                </div>
                <div className="flex items-center justify-between">
                  <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-20" />
                  <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-24" />
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
        <CircleDot className="w-10 sm:w-12 h-10 sm:h-12 text-red-400 mx-auto mb-3 sm:mb-4" />
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
        <CircleDot className="w-10 sm:w-12 h-10 sm:h-12 text-gray-400 dark:text-slate-500 mx-auto mb-3 sm:mb-4" />
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
        <TennisMatchCard
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

function TennisMatchCard({
  match,
  t,
  dateLocale,
  getConfidenceColor,
}: {
  match: TennisMatch;
  t: ReturnType<typeof useTranslations>;
  dateLocale: typeof fr | typeof enUS;
  getConfidenceColor: (confidence: number) => string;
}) {
  const matchDate = new Date(match.match_date);
  const surfaceKey = match.surface.toLowerCase();
  const surfaceColor = SURFACE_COLORS[surfaceKey] || SURFACE_COLORS.hard;

  return (
    <Link href={`/tennis/${match.id}`}>
      <Card className="border-gray-200 dark:border-slate-700 hover:border-primary-500/50 dark:hover:border-primary-500/50 transition-colors cursor-pointer">
        <CardHeader className="pb-2 px-4 sm:px-6 pt-4 sm:pt-6">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                {match.tournament.circuit}
              </Badge>
              <span className="text-sm text-gray-600 dark:text-slate-400">
                {match.tournament.name}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={`border ${surfaceColor} text-xs`} variant="outline">
                {t(surfaceKey as "hard" | "clay" | "grass" | "indoor")}
              </Badge>
              {match.status === "live" && (
                <Badge className="bg-red-500 text-white animate-pulse text-xs">
                  LIVE
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 sm:px-6 pb-4 sm:pb-6">
          {/* Players */}
          <div className="flex items-center justify-center gap-3 sm:gap-6 py-3 sm:py-4">
            <div className="flex-1 text-right">
              <p className="font-semibold text-sm sm:text-base text-gray-900 dark:text-white">
                {match.player1.name}
              </p>
              {match.player1.atp_ranking && (
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  #{match.player1.atp_ranking}
                </p>
              )}
            </div>

            <div className="flex flex-col items-center flex-shrink-0">
              {match.score ? (
                <span className="text-sm sm:text-base font-bold text-primary-500">
                  {match.score}
                </span>
              ) : (
                <span className="text-xs sm:text-sm text-gray-500 dark:text-slate-400 font-medium">
                  {t("vs")}
                </span>
              )}
            </div>

            <div className="flex-1 text-left">
              <p className="font-semibold text-sm sm:text-base text-gray-900 dark:text-white">
                {match.player2.name}
              </p>
              {match.player2.atp_ranking && (
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  #{match.player2.atp_ranking}
                </p>
              )}
            </div>
          </div>

          {/* Match info */}
          <div className="flex items-center justify-between text-xs sm:text-sm border-t border-gray-100 dark:border-slate-700/50 pt-3 mt-1">
            <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400">
              <Calendar className="w-3.5 h-3.5" />
              <span>
                {format(matchDate, "dd MMM yyyy, HH:mm", { locale: dateLocale })}
              </span>
            </div>
            <span className="text-gray-500 dark:text-slate-400">
              {t("round")}: {match.round}
            </span>
          </div>

          {/* Odds */}
          {(match.odds_player1 != null || match.odds_player2 != null) && (
            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700/50">
              <div className="flex items-center justify-center gap-4">
                <div className="flex items-center gap-1.5 bg-gray-100 dark:bg-slate-800 rounded-lg px-3 py-1.5">
                  <span className="text-xs text-gray-500 dark:text-slate-400">
                    {match.player1.name.split(" ").pop()}
                  </span>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">
                    {match.odds_player1?.toFixed(2) ?? "-"}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 bg-gray-100 dark:bg-slate-800 rounded-lg px-3 py-1.5">
                  <span className="text-xs text-gray-500 dark:text-slate-400">
                    {match.player2.name.split(" ").pop()}
                  </span>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">
                    {match.odds_player2?.toFixed(2) ?? "-"}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Prediction */}
          {match.pred_player1_prob != null && match.pred_player2_prob != null && (
            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-600 dark:text-slate-400 uppercase tracking-wide">
                  {t("prediction")}
                </span>
                {match.pred_confidence != null && (
                  <span className={`text-xs font-semibold ${getConfidenceColor(match.pred_confidence * 100)}`}>
                    {t("confidence")}: {(match.pred_confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-600 dark:text-slate-400 w-24 sm:w-32 truncate">
                    {match.player1.name}
                  </span>
                  <div className="flex-1 bg-gray-200 dark:bg-slate-700 rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full transition-all"
                      style={{ width: `${match.pred_player1_prob * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white w-12 text-right">
                    {(match.pred_player1_prob * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-600 dark:text-slate-400 w-24 sm:w-32 truncate">
                    {match.player2.name}
                  </span>
                  <div className="flex-1 bg-gray-200 dark:bg-slate-700 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all"
                      style={{ width: `${match.pred_player2_prob * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white w-12 text-right">
                    {(match.pred_player2_prob * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
