"use client";

import { useState } from "react";
import { useLiveScores, type LiveMatch } from "@/lib/hooks/useLiveScores";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Radio, ChevronRight, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import Link from "next/link";

const STATUS_COLORS: Record<string, string> = {
  "1H": "bg-green-500",
  "2H": "bg-green-500",
  HT: "bg-yellow-500",
  ET: "bg-orange-500",
  PEN: "bg-red-500",
  FT: "bg-dark-500",
};

const STATUS_LABELS: Record<string, string> = {
  "1H": "1ère MT",
  "2H": "2ème MT",
  HT: "Mi-temps",
  ET: "Prolongations",
  PEN: "Tirs au but",
  FT: "Terminé",
};

function LiveMatchCard({ match }: { match: LiveMatch }) {
  const isLive = ["1H", "2H", "HT", "ET", "PEN"].includes(match.status);

  return (
    <div
      className={cn(
        "p-3 rounded-lg border transition-colors",
        isLive
          ? "bg-dark-800/50 border-green-500/30 hover:border-green-500/50"
          : "bg-dark-800/30 border-dark-700 hover:border-dark-600"
      )}
    >
      {/* Competition & Status */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-dark-400 truncate max-w-[120px]">
          {match.competition}
        </span>
        <div className="flex items-center gap-2">
          {isLive && match.minute !== null && (
            <span className="text-xs font-medium text-green-400">
              {match.minute}&apos;
            </span>
          )}
          <Badge
            variant="outline"
            className={cn(
              "text-[10px] px-1.5 py-0 h-5",
              STATUS_COLORS[match.status] || "bg-dark-600",
              "text-white border-0"
            )}
          >
            {STATUS_LABELS[match.status] || match.status}
          </Badge>
        </div>
      </div>

      {/* Teams & Score */}
      <div className="space-y-1.5">
        {/* Home Team */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {match.home_team.logo_url ? (
              <img
                src={match.home_team.logo_url}
                alt={match.home_team.name}
                className="w-5 h-5 object-contain"
              />
            ) : (
              <div className="w-5 h-5 bg-dark-700 rounded-full" />
            )}
            <span className="text-sm text-white truncate">
              {match.home_team.short_name || match.home_team.name}
            </span>
          </div>
          <span
            className={cn(
              "text-lg font-bold tabular-nums",
              match.home_score > match.away_score
                ? "text-green-400"
                : "text-white"
            )}
          >
            {match.home_score}
          </span>
        </div>

        {/* Away Team */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {match.away_team.logo_url ? (
              <img
                src={match.away_team.logo_url}
                alt={match.away_team.name}
                className="w-5 h-5 object-contain"
              />
            ) : (
              <div className="w-5 h-5 bg-dark-700 rounded-full" />
            )}
            <span className="text-sm text-white truncate">
              {match.away_team.short_name || match.away_team.name}
            </span>
          </div>
          <span
            className={cn(
              "text-lg font-bold tabular-nums",
              match.away_score > match.home_score
                ? "text-green-400"
                : "text-white"
            )}
          >
            {match.away_score}
          </span>
        </div>
      </div>

      {/* Recent Events */}
      {match.events.length > 0 && (
        <div className="mt-2 pt-2 border-t border-dark-700">
          <div className="flex flex-wrap gap-1">
            {match.events.slice(0, 3).map((event, idx) => (
              <Badge
                key={idx}
                variant="outline"
                className="text-[10px] px-1.5 py-0 h-4 bg-dark-700/50 border-dark-600"
              >
                {event.minute}&apos;{" "}
                {event.type === "goal"
                  ? "⚽"
                  : event.type === "yellow_card"
                    ? "🟨"
                    : event.type === "red_card"
                      ? "🟥"
                      : "🔄"}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface LiveScoresSectionProps {
  maxMatches?: number;
  showHeader?: boolean;
  className?: string;
}

export function LiveScoresSection({
  maxMatches = 4,
  showHeader = true,
  className,
}: LiveScoresSectionProps) {
  const t = useTranslations("liveScores");
  const [selectedCompetition] = useState<string | undefined>(undefined);

  const { data, isLoading, error, dataUpdatedAt } = useLiveScores(
    selectedCompetition,
    {
      refetchInterval: 30000,
    }
  );

  // Filter to show only live matches first, then recent finished
  const sortedMatches = data?.matches
    ?.slice()
    .sort((a, b) => {
      const liveStatuses = ["1H", "2H", "HT", "ET", "PEN"];
      const aIsLive = liveStatuses.includes(a.status);
      const bIsLive = liveStatuses.includes(b.status);
      if (aIsLive && !bIsLive) return -1;
      if (!aIsLive && bIsLive) return 1;
      return 0;
    })
    .slice(0, maxMatches);

  const liveCount =
    data?.matches?.filter((m) =>
      ["1H", "2H", "HT", "ET", "PEN"].includes(m.status)
    ).length || 0;

  if (isLoading) {
    return (
      <Card className={cn("bg-dark-900 border-dark-700", className)}>
        {showHeader && (
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Radio className="w-4 h-4 text-green-500" />
              {t("title")}
            </CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={cn("bg-dark-900 border-dark-700", className)}>
        {showHeader && (
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Radio className="w-4 h-4 text-dark-500" />
              {t("title")}
            </CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-dark-400">
            <AlertCircle className="w-8 h-8 mb-2" />
            <p className="text-sm">{t("error")}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!sortedMatches || sortedMatches.length === 0) {
    return (
      <Card className={cn("bg-dark-900 border-dark-700", className)}>
        {showHeader && (
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Radio className="w-4 h-4 text-dark-500" />
              {t("title")}
            </CardTitle>
          </CardHeader>
        )}
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-dark-400">
            <p className="text-sm">{t("noMatches")}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("bg-dark-900 border-dark-700", className)}>
      {showHeader && (
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Radio
                className={cn(
                  "w-4 h-4",
                  liveCount > 0 ? "text-green-500 animate-pulse" : "text-dark-500"
                )}
              />
              {t("title")}
              {liveCount > 0 && (
                <Badge
                  variant="outline"
                  className="ml-2 bg-green-500/20 text-green-400 border-green-500/30"
                >
                  {liveCount} {t("live")}
                </Badge>
              )}
            </CardTitle>
            <Link
              href="/matches"
              className="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1"
            >
              {t("viewAll")}
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          {dataUpdatedAt && (
            <p className="text-xs text-dark-500 mt-1">
              {t("updatedAt", {
                time: new Date(dataUpdatedAt).toLocaleTimeString(),
              })}
            </p>
          )}
        </CardHeader>
      )}
      <CardContent className="pt-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {sortedMatches.map((match) => (
            <LiveMatchCard key={match.id} match={match} />
          ))}
        </div>

        {/* Data Source Warning */}
        {data?.data_source?.is_fallback && data.data_source.warning && (
          <div className="mt-3 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
            <p className="text-xs text-yellow-400">
              ⚠️ {data.data_source.warning}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
