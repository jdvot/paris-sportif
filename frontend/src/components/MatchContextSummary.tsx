"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Newspaper, Clock } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import type { PredictionResponseNewsSources } from "@/lib/api/models";

interface MatchContextSummaryProps {
  summary: string | null | undefined;
  sources?: PredictionResponseNewsSources;
  generatedAt?: string | null;
  className?: string;
}

export function MatchContextSummary({
  summary,
  sources,
  generatedAt,
  className,
}: MatchContextSummaryProps) {
  const t = useTranslations("matchContext");

  if (!summary) {
    return null;
  }

  // Format time ago
  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return t("minutesAgo", { count: diffMinutes });
    } else if (diffHours < 24) {
      return t("hoursAgo", { count: diffHours });
    } else {
      const diffDays = Math.floor(diffHours / 24);
      return t("daysAgo", { count: diffDays });
    }
  };

  return (
    <Card className={cn("bg-dark-900 border-dark-700", className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-accent-400" />
          {t("title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Summary text */}
        <p className="text-sm text-dark-200 leading-relaxed">
          {summary}
        </p>

        {/* Footer with sources and timestamp */}
        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-dark-700">
          {/* News sources */}
          {sources && sources.length > 0 && (
            <div className="flex items-center gap-2">
              <Newspaper className="w-3.5 h-3.5 text-dark-400" />
              <div className="flex flex-wrap gap-1">
                {sources.map((source, idx) => (
                  <Badge
                    key={idx}
                    variant="outline"
                    className="text-[10px] px-1.5 py-0 h-4 text-dark-400 border-dark-600"
                  >
                    {source.source || Object.values(source)[0] || "Source"}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Generated timestamp */}
          {generatedAt && (
            <div className="flex items-center gap-1 text-xs text-dark-500 ml-auto">
              <Clock className="w-3 h-3" />
              {t("updatedAgo", { time: formatTimeAgo(generatedAt) })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
