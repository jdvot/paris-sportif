"use client";

import { Newspaper, UserX, TrendingUp, TrendingDown, Minus, Loader2, AlertTriangle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEnrichMatch } from "@/lib/api/endpoints/rag/rag";
import type { TeamContext } from "@/lib/api/models";
import { format } from "date-fns";

interface RAGContextProps {
  homeTeam: string;
  awayTeam: string;
  competition: string;
  matchDate: Date;
  className?: string;
}

function SentimentBadge({ label, score }: { label?: string; score?: number }) {
  const normalizedLabel = label?.toLowerCase() || "neutral";

  const config = {
    positive: {
      icon: TrendingUp,
      bg: "bg-green-100 dark:bg-green-500/20",
      text: "text-green-700 dark:text-green-300",
      border: "border-green-300 dark:border-green-500/40",
    },
    negative: {
      icon: TrendingDown,
      bg: "bg-red-100 dark:bg-red-500/20",
      text: "text-red-700 dark:text-red-300",
      border: "border-red-300 dark:border-red-500/40",
    },
    neutral: {
      icon: Minus,
      bg: "bg-gray-100 dark:bg-gray-500/20",
      text: "text-gray-700 dark:text-gray-300",
      border: "border-gray-300 dark:border-gray-500/40",
    },
  };

  const style = config[normalizedLabel as keyof typeof config] || config.neutral;
  const Icon = style.icon;

  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-medium border",
      style.bg,
      style.text,
      style.border
    )}>
      <Icon className="w-3 h-3" />
      {label || "Neutre"}
    </span>
  );
}

function TeamContextSection({ context, teamName }: { context: TeamContext; teamName: string }) {
  const hasNews = context.recent_news && context.recent_news.length > 0;
  const hasInjuries = context.injuries && context.injuries.length > 0;

  if (!hasNews && !hasInjuries) {
    return null;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-700 dark:text-slate-200 truncate max-w-[150px]">
          {teamName}
        </span>
        <SentimentBadge label={context.sentiment_label} score={context.sentiment_score} />
      </div>

      {/* Recent News */}
      {hasNews && (
        <div className="space-y-1">
          {context.recent_news!.slice(0, 2).map((news, i) => (
            <div
              key={i}
              className="flex items-start gap-1.5 text-[10px] sm:text-xs text-gray-600 dark:text-slate-400"
            >
              <Newspaper className="w-3 h-3 mt-0.5 flex-shrink-0 text-blue-500" />
              <span className="line-clamp-1">{news}</span>
            </div>
          ))}
        </div>
      )}

      {/* Injuries */}
      {hasInjuries && (
        <div className="flex flex-wrap gap-1">
          {context.injuries!.slice(0, 3).map((injury, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-100 dark:bg-red-500/20 border border-red-300 dark:border-red-500/40 rounded text-[10px] text-red-700 dark:text-red-300"
            >
              <UserX className="w-2.5 h-2.5" />
              {injury}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function RAGContext({
  homeTeam,
  awayTeam,
  competition,
  matchDate,
  className,
}: RAGContextProps) {
  const { data, isLoading, error } = useEnrichMatch(
    {
      home_team: homeTeam,
      away_team: awayTeam,
      competition: competition,
      match_date: format(matchDate, "yyyy-MM-dd"),
    },
    {
      query: {
        enabled: true,
        staleTime: 5 * 60 * 1000, // 5 minutes
        retry: 1,
      },
    }
  );

  // Extract the actual data from the response
  const ragContext = data?.data;

  if (isLoading) {
    return (
      <div className={cn("flex items-center justify-center py-3", className)}>
        <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
        <span className="ml-2 text-xs text-gray-500 dark:text-slate-400">
          Chargement du contexte...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("flex items-center gap-2 py-2 text-xs text-orange-600 dark:text-orange-400", className)}>
        <AlertTriangle className="w-3.5 h-3.5" />
        <span>Contexte RAG non disponible</span>
      </div>
    );
  }

  if (!ragContext) {
    return null;
  }

  const homeContext = ragContext.home_context;
  const awayContext = ragContext.away_context;

  // Check if there's any meaningful context to display
  const hasHomeContext = homeContext && (
    (homeContext.recent_news && homeContext.recent_news.length > 0) ||
    (homeContext.injuries && homeContext.injuries.length > 0)
  );
  const hasAwayContext = awayContext && (
    (awayContext.recent_news && awayContext.recent_news.length > 0) ||
    (awayContext.injuries && awayContext.injuries.length > 0)
  );

  if (!hasHomeContext && !hasAwayContext) {
    return (
      <div className={cn("flex items-center gap-2 py-2 text-xs text-gray-500 dark:text-slate-400", className)}>
        <Info className="w-3.5 h-3.5" />
        <span>Aucune actualité récente</span>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 dark:text-slate-300">
        <Newspaper className="w-3.5 h-3.5" />
        <span>Contexte du match</span>
        {ragContext.is_derby && (
          <span className="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-500/20 border border-purple-300 dark:border-purple-500/40 rounded text-[10px] text-purple-700 dark:text-purple-300">
            Derby
          </span>
        )}
        {ragContext.match_importance && ragContext.match_importance !== "normal" && (
          <span className={cn(
            "px-1.5 py-0.5 rounded text-[10px] border",
            ragContext.match_importance === "high" || ragContext.match_importance === "critical"
              ? "bg-amber-100 dark:bg-amber-500/20 border-amber-300 dark:border-amber-500/40 text-amber-700 dark:text-amber-300"
              : "bg-gray-100 dark:bg-gray-500/20 border-gray-300 dark:border-gray-500/40 text-gray-700 dark:text-gray-300"
          )}>
            {ragContext.match_importance === "high" ? "Important" :
             ragContext.match_importance === "critical" ? "Crucial" :
             ragContext.match_importance}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {hasHomeContext && (
          <TeamContextSection context={homeContext} teamName={homeTeam} />
        )}
        {hasAwayContext && (
          <TeamContextSection context={awayContext} teamName={awayTeam} />
        )}
      </div>
    </div>
  );
}
