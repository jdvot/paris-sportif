"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { format } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { useTranslations, useLocale } from "next-intl";
import { ArrowLeft, Calendar, Dribbble, AlertTriangle, BarChart3 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { customInstance } from "@/lib/api/custom-instance";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { isAuthError } from "@/lib/utils";

interface BasketballTeam {
  id: number;
  name: string;
  short_name?: string | null;
  country?: string | null;
  logo_url?: string | null;
  league: string;
  elo_rating: number;
  offensive_rating?: number | null;
  defensive_rating?: number | null;
  pace?: number | null;
  win_rate_ytd?: number | null;
}

interface BasketballMatch {
  id: number;
  home_team: BasketballTeam;
  away_team: BasketballTeam;
  league: string;
  match_date: string;
  status: string;
  home_score?: number | null;
  away_score?: number | null;
  home_q1?: number | null;
  away_q1?: number | null;
  home_q2?: number | null;
  away_q2?: number | null;
  home_q3?: number | null;
  away_q3?: number | null;
  home_q4?: number | null;
  away_q4?: number | null;
  odds_home?: number | null;
  odds_away?: number | null;
  spread?: number | null;
  over_under?: number | null;
  pred_home_prob?: number | null;
  pred_away_prob?: number | null;
  pred_confidence?: number | null;
  pred_explanation?: string | null;
  is_back_to_back_home: boolean;
  is_back_to_back_away: boolean;
}

const LEAGUE_COLORS: Record<string, string> = {
  NBA: "bg-red-500/20 text-red-600 dark:text-red-400",
  Euroleague: "bg-blue-500/20 text-blue-600 dark:text-blue-400",
};

export default function BasketballMatchDetailPage() {
  const params = useParams();
  const idValue = Array.isArray(params.id) ? params.id[0] : params.id;
  const id = Number(idValue);
  const t = useTranslations("basketball");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const dateLocale = locale === "fr" ? fr : enUS;

  const { data: response, isLoading, error } = useQuery({
    queryKey: [`basketball-match-${id}`],
    queryFn: () =>
      customInstance<{ data: BasketballMatch; status: number }>(
        `/api/v1/basketball/matches/${id}`
      ),
    enabled: id > 0,
    staleTime: 5 * 60 * 1000,
  });

  const match = (response?.data as BasketballMatch | undefined) ?? null;

  const quarterScoreColumns = useMemo(() => {
    if (!match) return null;
    const quarters: { label: string; home: number | undefined | null; away: number | undefined | null }[] = [];
    if (match.home_q1 != null) quarters.push({ label: "Q1", home: match.home_q1, away: match.away_q1 });
    if (match.home_q2 != null) quarters.push({ label: "Q2", home: match.home_q2, away: match.away_q2 });
    if (match.home_q3 != null) quarters.push({ label: "Q3", home: match.home_q3, away: match.away_q3 });
    if (match.home_q4 != null) quarters.push({ label: "Q4", home: match.home_q4, away: match.away_q4 });
    return quarters.length > 0 ? quarters : null;
  }, [match]);

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
        <Link href="/basketball" className="inline-flex items-center gap-2 text-primary-500 hover:text-primary-600 mb-6">
          <ArrowLeft className="w-4 h-4" />
          {t("title")}
        </Link>
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-8 text-center">
          <Dribbble className="w-12 h-12 text-red-400 mx-auto mb-4" />
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
        <Link href="/basketball" className="inline-flex items-center gap-2 text-primary-500 hover:text-primary-600 mb-6">
          <ArrowLeft className="w-4 h-4" />
          {t("title")}
        </Link>
        <div className="text-center py-12">
          <Dribbble className="w-12 h-12 text-gray-400 dark:text-slate-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-600 dark:text-slate-300">
            {t("noMatches")}
          </h3>
        </div>
      </div>
    );
  }

  const matchDate = new Date(match.match_date);
  const leagueColor = LEAGUE_COLORS[match.league] || LEAGUE_COLORS.NBA;
  const isFinished = match.status === "finished";
  const isLive = match.status === "live";
  const hasBackToBack = match.is_back_to_back_home || match.is_back_to_back_away;

  return (
    <div className="max-w-3xl mx-auto space-y-6 px-4 py-8">
      {/* Back link */}
      <Link href="/basketball" className="inline-flex items-center gap-2 text-primary-500 hover:text-primary-600 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        {t("title")}
      </Link>

      {/* Match header */}
      <Card className="border-gray-200 dark:border-slate-700">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Badge className={`${leagueColor} text-xs`} variant="secondary">
                {match.league}
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
            <div className="flex items-center gap-2">
              {hasBackToBack && (
                <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30 text-xs" variant="outline">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  {t("backToBack")}
                </Badge>
              )}
              <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
                <Calendar className="w-3.5 h-3.5" />
                <span>{format(matchDate, "EEEE dd MMMM yyyy, HH:mm", { locale: dateLocale })}</span>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Teams and score */}
          <div className="space-y-4 py-4">
            {/* Home team */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <p className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white truncate">
                  {match.home_team.name}
                </p>
                {match.is_back_to_back_home && (
                  <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 text-[10px] px-1.5 py-0 flex-shrink-0" variant="secondary">
                    B2B
                  </Badge>
                )}
              </div>
              {(isFinished || isLive) && match.home_score != null && (
                <span className={`text-3xl font-bold ml-4 ${isLive ? "text-red-500 animate-pulse" : "text-gray-900 dark:text-white"}`}>
                  {match.home_score}
                </span>
              )}
            </div>

            {/* Away team */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <p className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white truncate">
                  {match.away_team.name}
                </p>
                {match.is_back_to_back_away && (
                  <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 text-[10px] px-1.5 py-0 flex-shrink-0" variant="secondary">
                    B2B
                  </Badge>
                )}
              </div>
              {(isFinished || isLive) && match.away_score != null && (
                <span className={`text-3xl font-bold ml-4 ${isLive ? "text-red-500 animate-pulse" : "text-gray-900 dark:text-white"}`}>
                  {match.away_score}
                </span>
              )}
            </div>
          </div>

          {/* Quarter scores */}
          {quarterScoreColumns && (
            <div className="border-t border-gray-100 dark:border-slate-700/50 pt-4">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="text-left text-xs font-medium text-gray-500 dark:text-slate-400 w-32" />
                    {quarterScoreColumns.map((q) => (
                      <th key={q.label} className="text-center text-xs font-medium text-gray-500 dark:text-slate-400">
                        {q.label}
                      </th>
                    ))}
                    <th className="text-center text-xs font-bold text-gray-700 dark:text-slate-300">T</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="text-left font-medium text-gray-700 dark:text-slate-300 truncate py-1">
                      {match.home_team.short_name ?? match.home_team.name}
                    </td>
                    {quarterScoreColumns.map((q) => (
                      <td key={q.label} className="text-center font-semibold text-gray-900 dark:text-white">
                        {q.home ?? "-"}
                      </td>
                    ))}
                    <td className="text-center font-bold text-gray-900 dark:text-white">{match.home_score ?? "-"}</td>
                  </tr>
                  <tr>
                    <td className="text-left font-medium text-gray-700 dark:text-slate-300 truncate py-1">
                      {match.away_team.short_name ?? match.away_team.name}
                    </td>
                    {quarterScoreColumns.map((q) => (
                      <td key={q.label} className="text-center font-semibold text-gray-900 dark:text-white">
                        {q.away ?? "-"}
                      </td>
                    ))}
                    <td className="text-center font-bold text-gray-900 dark:text-white">{match.away_score ?? "-"}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Team comparison */}
      <Card className="border-gray-200 dark:border-slate-700">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-primary-500" />
            {t("teamComparison")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* ELO */}
            <StatRow
              label="ELO"
              home={match.home_team.elo_rating.toFixed(0)}
              away={match.away_team.elo_rating.toFixed(0)}
              homeRatio={match.home_team.elo_rating / (match.home_team.elo_rating + match.away_team.elo_rating)}
              homeName={match.home_team.short_name ?? match.home_team.name.slice(0, 3)}
              awayName={match.away_team.short_name ?? match.away_team.name.slice(0, 3)}
            />

            {/* Offensive Rating */}
            {match.home_team.offensive_rating != null && match.away_team.offensive_rating != null && (
              <StatRow
                label={t("offRating")}
                home={match.home_team.offensive_rating.toFixed(1)}
                away={match.away_team.offensive_rating.toFixed(1)}
                homeRatio={match.home_team.offensive_rating / (match.home_team.offensive_rating + match.away_team.offensive_rating)}
                homeName={match.home_team.short_name ?? match.home_team.name.slice(0, 3)}
                awayName={match.away_team.short_name ?? match.away_team.name.slice(0, 3)}
              />
            )}

            {/* Defensive Rating */}
            {match.home_team.defensive_rating != null && match.away_team.defensive_rating != null && (
              <StatRow
                label={t("defRating")}
                home={match.home_team.defensive_rating.toFixed(1)}
                away={match.away_team.defensive_rating.toFixed(1)}
                homeRatio={match.away_team.defensive_rating / (match.home_team.defensive_rating + match.away_team.defensive_rating)}
                homeName={match.home_team.short_name ?? match.home_team.name.slice(0, 3)}
                awayName={match.away_team.short_name ?? match.away_team.name.slice(0, 3)}
              />
            )}

            {/* Pace */}
            {match.home_team.pace != null && match.away_team.pace != null && (
              <StatRow
                label={t("pace")}
                home={match.home_team.pace.toFixed(1)}
                away={match.away_team.pace.toFixed(1)}
                homeRatio={match.home_team.pace / (match.home_team.pace + match.away_team.pace)}
                homeName={match.home_team.short_name ?? match.home_team.name.slice(0, 3)}
                awayName={match.away_team.short_name ?? match.away_team.name.slice(0, 3)}
              />
            )}

            {/* Win Rate */}
            {(match.home_team.win_rate_ytd != null || match.away_team.win_rate_ytd != null) && (
              <div className="flex items-center justify-center gap-8 pt-2 border-t border-gray-100 dark:border-slate-700/50">
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {match.home_team.win_rate_ytd != null ? `${(match.home_team.win_rate_ytd * 100).toFixed(0)}%` : "-"}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{t("winRate")}</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {match.away_team.win_rate_ytd != null ? `${(match.away_team.win_rate_ytd * 100).toFixed(0)}%` : "-"}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{t("winRate")}</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Odds */}
      {(match.odds_home != null || match.odds_away != null) && (
        <Card className="border-gray-200 dark:border-slate-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("odds")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center gap-6 flex-wrap">
              <div className="text-center">
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">{match.home_team.name}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {match.odds_home?.toFixed(2) ?? "-"}
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">{match.away_team.name}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {match.odds_away?.toFixed(2) ?? "-"}
                </p>
              </div>
              {match.spread != null && (
                <div className="text-center">
                  <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">{t("spread")}</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {match.spread > 0 ? "+" : ""}{match.spread.toFixed(1)}
                  </p>
                </div>
              )}
              {match.over_under != null && (
                <div className="text-center">
                  <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">{t("overUnder")}</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {match.over_under.toFixed(1)}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Prediction */}
      {match.pred_home_prob != null && match.pred_away_prob != null && (
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
                  <span className="font-medium text-gray-900 dark:text-white">{match.home_team.name}</span>
                  <span className="font-bold text-primary-500">{(match.pred_home_prob * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-3">
                  <div
                    className="bg-primary-500 h-3 rounded-full transition-all"
                    style={{ width: `${match.pred_home_prob * 100}%` }}
                  />
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-gray-900 dark:text-white">{match.away_team.name}</span>
                  <span className="font-bold text-blue-500">{(match.pred_away_prob * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-3">
                  <div
                    className="bg-blue-500 h-3 rounded-full transition-all"
                    style={{ width: `${match.pred_away_prob * 100}%` }}
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

function StatRow({
  label,
  home,
  away,
  homeRatio,
  homeName,
  awayName,
}: {
  label: string;
  home: string;
  away: string;
  homeRatio: number;
  homeName: string;
  awayName: string;
}) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold text-gray-900 dark:text-white w-10 text-right">{homeName}</span>
        <span className="text-sm font-bold text-primary-500 w-12 text-right">{home}</span>
        <div className="flex-1 bg-gray-200 dark:bg-slate-700 rounded-full h-2.5 relative">
          <div
            className="bg-primary-500 h-2.5 rounded-full transition-all"
            style={{ width: `${Math.min(100, homeRatio * 100)}%` }}
          />
        </div>
        <span className="text-sm font-bold text-blue-500 w-12">{away}</span>
        <span className="text-xs font-semibold text-gray-900 dark:text-white w-10">{awayName}</span>
      </div>
    </div>
  );
}
