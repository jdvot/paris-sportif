"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Heart,
  Loader2,
  AlertCircle,
  ChevronRight,
  Calendar,
  Trophy,
  Sparkles,
  Newspaper,
  MapPin,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import { useUserPreferences } from "@/lib/hooks/useUserPreferences";
import { useTeamNews, useTeamSummary } from "@/lib/hooks/useTeamNews";
import { FavoriteTeamModal } from "@/components/FavoriteTeamModal";
import Link from "next/link";

// Form result badges
const FORM_COLORS: Record<string, string> = {
  W: "bg-green-500 text-white",
  D: "bg-yellow-500 text-white",
  L: "bg-red-500 text-white",
};

function FormBadges({ form }: { form: string[] }) {
  if (!form || form.length === 0) return null;

  return (
    <div className="flex gap-1">
      {form.map((result, idx) => (
        <span
          key={idx}
          className={cn(
            "w-6 h-6 flex items-center justify-center rounded text-xs font-bold",
            FORM_COLORS[result] || "bg-dark-600 text-dark-300"
          )}
        >
          {result}
        </span>
      ))}
    </div>
  );
}

interface MyClubSectionProps {
  className?: string;
}

export function MyClubSection({ className }: MyClubSectionProps) {
  const t = useTranslations("myClub");
  const [showModal, setShowModal] = useState(false);

  const { data: preferences, isLoading: prefsLoading } = useUserPreferences();
  const favoriteTeam = preferences?.favorite_team;
  const teamId = preferences?.favorite_team_id ?? null;

  const { data: newsData, isLoading: newsLoading } = useTeamNews(teamId, { limit: 3 });
  const { data: summary, isLoading: summaryLoading } = useTeamSummary(teamId);

  // Show nothing if user is not logged in or preferences are still loading
  if (prefsLoading) {
    return (
      <Card className={cn("bg-dark-900 border-dark-700", className)}>
        <CardContent className="py-8">
          <div className="flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show prompt to select favorite team if not set
  if (!favoriteTeam) {
    return (
      <>
        <Card className={cn("bg-dark-900 border-dark-700", className)}>
          <CardContent className="py-8">
            <div className="flex flex-col items-center text-center">
              <div className="p-3 bg-primary-500/10 rounded-full mb-4">
                <Heart className="w-8 h-8 text-primary-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                {t("noClubSelected")}
              </h3>
              <p className="text-sm text-dark-400 mb-4 max-w-sm">
                {t("title")}
              </p>
              <Button
                onClick={() => setShowModal(true)}
                className="bg-primary-500 hover:bg-primary-600"
              >
                <Heart className="w-4 h-4 mr-2" />
                {t("selectClub")}
              </Button>
            </div>
          </CardContent>
        </Card>
        <FavoriteTeamModal forceOpen={showModal} onClose={() => setShowModal(false)} />
      </>
    );
  }

  const isLoading = newsLoading || summaryLoading;

  return (
    <>
      <Card className={cn("bg-dark-900 border-dark-700", className)}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-3">
              {favoriteTeam.logo_url && (
                <img
                  src={favoriteTeam.logo_url}
                  alt={favoriteTeam.name}
                  className="w-8 h-8 object-contain"
                />
              )}
              <div>
                <span className="text-white">{favoriteTeam.name}</span>
                {favoriteTeam.country && (
                  <span className="text-sm text-dark-400 ml-2">
                    {favoriteTeam.country}
                  </span>
                )}
              </div>
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowModal(true)}
              className="text-dark-400 hover:text-white"
            >
              {t("selectClub")}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
            </div>
          ) : (
            <>
              {/* Team Stats */}
              {summary && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {/* Form */}
                  <div className="p-3 bg-dark-800/50 rounded-lg">
                    <p className="text-xs text-dark-400 mb-1">{t("form")}</p>
                    {summary.form ? (
                      <FormBadges form={summary.form} />
                    ) : (
                      <span className="text-sm text-dark-500">-</span>
                    )}
                  </div>

                  {/* Position */}
                  <div className="p-3 bg-dark-800/50 rounded-lg">
                    <p className="text-xs text-dark-400 mb-1">{t("position")}</p>
                    <div className="flex items-baseline gap-1">
                      <span className="text-xl font-bold text-white">
                        {summary.position || "-"}
                      </span>
                      {summary.position && (
                        <span className="text-xs text-dark-400">e</span>
                      )}
                    </div>
                  </div>

                  {/* Points */}
                  {summary.points !== null && (
                    <div className="p-3 bg-dark-800/50 rounded-lg">
                      <p className="text-xs text-dark-400 mb-1">Points</p>
                      <div className="flex items-center gap-2">
                        <Trophy className="w-4 h-4 text-yellow-400" />
                        <span className="text-xl font-bold text-white">
                          {summary.points}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Competition */}
                  {summary.competition && (
                    <div className="p-3 bg-dark-800/50 rounded-lg">
                      <p className="text-xs text-dark-400 mb-1">Ligue</p>
                      <span className="text-sm font-medium text-white truncate block">
                        {summary.competition}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Next Match */}
              {summary?.next_match && (
                <div className="p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-primary-400" />
                      <span className="text-sm font-medium text-white">
                        Prochain match
                      </span>
                    </div>
                    <Badge variant="outline" className="text-primary-400 border-primary-500/30">
                      {summary.next_match.is_home ? (
                        <MapPin className="w-3 h-3 mr-1" />
                      ) : null}
                      {summary.next_match.is_home ? "Domicile" : "Extérieur"}
                    </Badge>
                  </div>
                  <div className="mt-2">
                    <p className="text-white font-medium">
                      vs {summary.next_match.opponent}
                    </p>
                    <p className="text-sm text-dark-400">
                      {new Date(summary.next_match.date).toLocaleDateString("fr-FR", {
                        weekday: "long",
                        day: "numeric",
                        month: "long",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>
              )}

              {/* AI Summary */}
              {summary?.summary && (
                <div className="p-3 bg-dark-800/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-accent-400" />
                    <span className="text-sm font-medium text-white">
                      {t("summary")}
                    </span>
                  </div>
                  <p className="text-sm text-dark-300 leading-relaxed">
                    {summary.summary}
                  </p>
                  {summary.key_insights && summary.key_insights.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {summary.key_insights.map((insight, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-2 text-sm text-dark-400"
                        >
                          <span className="text-primary-400">•</span>
                          {insight}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* News Section */}
              {newsData?.news && newsData.news.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Newspaper className="w-4 h-4 text-dark-400" />
                      <span className="text-sm font-medium text-white">
                        {t("news")}
                      </span>
                    </div>
                    <Link
                      href="/search"
                      className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1"
                    >
                      {t("viewAllNews")}
                      <ChevronRight className="w-3 h-3" />
                    </Link>
                  </div>
                  <div className="space-y-2">
                    {newsData.news.map((news) => (
                      <div
                        key={news.id}
                        className="p-3 bg-dark-800/30 hover:bg-dark-800/50 rounded-lg transition-colors cursor-pointer"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-white font-medium line-clamp-2">
                              {news.title}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge
                                variant="outline"
                                className={cn(
                                  "text-[10px] px-1.5 py-0 h-4",
                                  news.sentiment === "positive"
                                    ? "text-green-400 border-green-500/30"
                                    : news.sentiment === "negative"
                                      ? "text-red-400 border-red-500/30"
                                      : "text-dark-400 border-dark-600"
                                )}
                              >
                                {news.category}
                              </Badge>
                              <span className="text-xs text-dark-500">
                                {new Date(news.published_at).toLocaleDateString("fr-FR")}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* No news fallback */}
              {(!newsData?.news || newsData.news.length === 0) && !summaryLoading && (
                <div className="text-center py-4">
                  <AlertCircle className="w-6 h-6 text-dark-500 mx-auto mb-2" />
                  <p className="text-sm text-dark-400">{t("noNews")}</p>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
      <FavoriteTeamModal forceOpen={showModal} onClose={() => setShowModal(false)} />
    </>
  );
}
