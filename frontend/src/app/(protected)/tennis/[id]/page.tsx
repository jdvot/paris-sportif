"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { format } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { useTranslations, useLocale } from "next-intl";
import { ArrowLeft, Calendar, CircleDot, Trophy, BarChart3 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { customInstance } from "@/lib/api/custom-instance";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { isAuthError } from "@/lib/utils";

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

const SURFACE_COLORS: Record<string, string> = {
  hard: "bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30",
  clay: "bg-orange-500/20 text-orange-600 dark:text-orange-400 border-orange-500/30",
  grass: "bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30",
  indoor: "bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/30",
};

export default function TennisMatchDetailPage() {
  const params = useParams();
  const idValue = Array.isArray(params.id) ? params.id[0] : params.id;
  const id = Number(idValue);
  const t = useTranslations("tennis");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const dateLocale = locale === "fr" ? fr : enUS;

  const { data: response, isLoading, error } = useQuery({
    queryKey: [`tennis-match-${id}`],
    queryFn: () =>
      customInstance<{ data: TennisMatch; status: number }>(
        `/api/v1/tennis/matches/${id}`
      ),
    enabled: id > 0,
    staleTime: 5 * 60 * 1000,
  });

  const match = (response?.data as TennisMatch | undefined) ?? null;

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto space-y-6 px-4 py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-48" />
          <div className="h-48 bg-gray-200 dark:bg-slate-700 rounded-xl" />
          <div className="h-64 bg-gray-200 dark:bg-slate-700 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error && !isAuthError(error)) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <Link href="/tennis" className="inline-flex items-center gap-2 text-primary-500 hover:text-primary-600 mb-6">
          <ArrowLeft className="w-4 h-4" />
          {t("title")}
        </Link>
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-8 text-center">
          <CircleDot className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {tCommon("errorLoading")}
          </h3>
        </div>
      </div>
    );
  }

  if (!match) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <Link href="/tennis" className="inline-flex items-center gap-2 text-primary-500 hover:text-primary-600 mb-6">
          <ArrowLeft className="w-4 h-4" />
          {t("title")}
        </Link>
        <div className="text-center py-12">
          <CircleDot className="w-12 h-12 text-gray-400 dark:text-slate-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-600 dark:text-slate-300">
            {t("noMatches")}
          </h3>
        </div>
      </div>
    );
  }

  const matchDate = new Date(match.match_date);
  const surfaceKey = match.surface.toLowerCase();
  const surfaceColor = SURFACE_COLORS[surfaceKey] || SURFACE_COLORS.hard;
  const isFinished = match.status === "finished";
  const isLive = match.status === "live";

  const getEloForSurface = (player: TennisPlayer) => {
    switch (surfaceKey) {
      case "clay": return player.elo_clay;
      case "grass": return player.elo_grass;
      case "indoor": return player.elo_indoor;
      default: return player.elo_hard;
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 px-4 py-8">
      {/* Back link */}
      <Link href="/tennis" className="inline-flex items-center gap-2 text-primary-500 hover:text-primary-600 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        {t("title")}
      </Link>

      {/* Match header */}
      <Card className="border-gray-200 dark:border-slate-700">
        <CardHeader className="pb-3">
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
              {isLive && (
                <Badge className="bg-red-500 text-white animate-pulse text-xs">LIVE</Badge>
              )}
              {isFinished && (
                <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs" variant="secondary">
                  FT
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Players and score */}
          <div className="flex items-center justify-center gap-6 py-6">
            <div className="flex-1 text-right space-y-1">
              <p className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                {match.player1.name}
              </p>
              {match.player1.country && (
                <p className="text-xs text-gray-500 dark:text-slate-400">{match.player1.country}</p>
              )}
              {(match.player1.atp_ranking ?? match.player1.wta_ranking) && (
                <p className="text-sm text-primary-500 font-medium">
                  #{match.player1.atp_ranking ?? match.player1.wta_ranking}
                </p>
              )}
            </div>

            <div className="flex flex-col items-center flex-shrink-0">
              {match.score ? (
                <div className="text-center">
                  <span className="text-2xl font-bold text-primary-500">{match.score}</span>
                  {match.sets_player1 != null && match.sets_player2 != null && (
                    <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                      ({match.sets_player1} - {match.sets_player2})
                    </p>
                  )}
                </div>
              ) : (
                <span className="text-sm text-gray-500 dark:text-slate-400 font-medium">{t("vs")}</span>
              )}
            </div>

            <div className="flex-1 text-left space-y-1">
              <p className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                {match.player2.name}
              </p>
              {match.player2.country && (
                <p className="text-xs text-gray-500 dark:text-slate-400">{match.player2.country}</p>
              )}
              {(match.player2.atp_ranking ?? match.player2.wta_ranking) && (
                <p className="text-sm text-primary-500 font-medium">
                  #{match.player2.atp_ranking ?? match.player2.wta_ranking}
                </p>
              )}
            </div>
          </div>

          {/* Match meta */}
          <div className="flex items-center justify-center gap-6 text-sm text-gray-500 dark:text-slate-400 border-t border-gray-100 dark:border-slate-700/50 pt-4">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              <span>{format(matchDate, "EEEE dd MMMM yyyy, HH:mm", { locale: dateLocale })}</span>
            </div>
            {match.round && (
              <div className="flex items-center gap-1.5">
                <Trophy className="w-4 h-4" />
                <span>{match.round}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Player comparison - ELO per surface */}
      <Card className="border-gray-200 dark:border-slate-700">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-primary-500" />
            {t("playerComparison")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Surface ELO */}
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                ELO ({t(surfaceKey as "hard" | "clay" | "grass" | "indoor")})
              </p>
              <div className="flex items-center gap-4">
                <span className="text-sm font-semibold text-gray-900 dark:text-white w-24 text-right truncate">
                  {match.player1.name.split(" ").pop()}
                </span>
                <div className="flex-1 flex items-center gap-2">
                  <span className="text-sm font-bold text-primary-500 w-12 text-right">
                    {getEloForSurface(match.player1).toFixed(0)}
                  </span>
                  <div className="flex-1 bg-gray-200 dark:bg-slate-700 rounded-full h-3 relative">
                    <div
                      className="bg-primary-500 h-3 rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, (getEloForSurface(match.player1) / (getEloForSurface(match.player1) + getEloForSurface(match.player2))) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm font-bold text-blue-500 w-12">
                    {getEloForSurface(match.player2).toFixed(0)}
                  </span>
                </div>
                <span className="text-sm font-semibold text-gray-900 dark:text-white w-24 truncate">
                  {match.player2.name.split(" ").pop()}
                </span>
              </div>
            </div>

            {/* Win rate YTD */}
            {(match.player1.win_rate_ytd != null || match.player2.win_rate_ytd != null) && (
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  {t("winRate")}
                </p>
                <div className="flex items-center justify-center gap-8">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {match.player1.win_rate_ytd != null ? `${(match.player1.win_rate_ytd * 100).toFixed(0)}%` : "-"}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-slate-400">{match.player1.name.split(" ").pop()}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {match.player2.win_rate_ytd != null ? `${(match.player2.win_rate_ytd * 100).toFixed(0)}%` : "-"}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-slate-400">{match.player2.name.split(" ").pop()}</p>
                  </div>
                </div>
              </div>
            )}

            {/* All surface ELOs */}
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                ELO {tCommon("all")} surfaces
              </p>
              <div className="grid grid-cols-4 gap-2 text-center">
                {(["hard", "clay", "grass", "indoor"] as const).map((s) => {
                  const p1Elo = s === "hard" ? match.player1.elo_hard : s === "clay" ? match.player1.elo_clay : s === "grass" ? match.player1.elo_grass : match.player1.elo_indoor;
                  const p2Elo = s === "hard" ? match.player2.elo_hard : s === "clay" ? match.player2.elo_clay : s === "grass" ? match.player2.elo_grass : match.player2.elo_indoor;
                  const isActive = s === surfaceKey;
                  return (
                    <div key={s} className={`rounded-lg p-2 ${isActive ? "bg-primary-500/10 border border-primary-500/30" : "bg-gray-50 dark:bg-slate-800/50"}`}>
                      <p className="text-[10px] uppercase font-medium text-gray-500 dark:text-slate-400 mb-1">
                        {t(s)}
                      </p>
                      <p className="text-xs font-bold text-primary-500">{p1Elo.toFixed(0)}</p>
                      <p className="text-xs font-bold text-blue-500">{p2Elo.toFixed(0)}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Odds */}
      {(match.odds_player1 != null || match.odds_player2 != null) && (
        <Card className="border-gray-200 dark:border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("odds")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center gap-6">
              <div className="text-center">
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">{match.player1.name}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {match.odds_player1?.toFixed(2) ?? "-"}
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">{match.player2.name}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {match.odds_player2?.toFixed(2) ?? "-"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Prediction */}
      {match.pred_player1_prob != null && match.pred_player2_prob != null && (
        <Card className="border-gray-200 dark:border-slate-700 bg-gradient-to-br from-primary-50 to-blue-50 dark:from-primary-500/5 dark:to-blue-500/5">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-primary-500" />
                {t("prediction")}
              </CardTitle>
              {match.pred_confidence != null && (
                <Badge className="bg-primary-500/20 text-primary-600 dark:text-primary-400 text-xs" variant="secondary">
                  {t("confidence")}: {(match.pred_confidence * 100).toFixed(0)}%
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Probability bars */}
            <div className="space-y-3">
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-gray-900 dark:text-white">{match.player1.name}</span>
                  <span className="font-bold text-primary-500">{(match.pred_player1_prob * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-3">
                  <div
                    className="bg-primary-500 h-3 rounded-full transition-all"
                    style={{ width: `${match.pred_player1_prob * 100}%` }}
                  />
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-gray-900 dark:text-white">{match.player2.name}</span>
                  <span className="font-bold text-blue-500">{(match.pred_player2_prob * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-3">
                  <div
                    className="bg-blue-500 h-3 rounded-full transition-all"
                    style={{ width: `${match.pred_player2_prob * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Explanation */}
            {match.pred_explanation && (
              <div className="mt-4 p-4 bg-white/60 dark:bg-slate-800/60 rounded-lg border border-gray-200 dark:border-slate-700">
                <p className="text-sm text-gray-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                  {match.pred_explanation}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
