"use client";

import { DailyPicks } from "@/components/DailyPicks";
import { UpcomingMatches } from "@/components/UpcomingMatches";
import { NewsFeed } from "@/components/NewsFeed";
import { LiveScoresSection } from "@/components/LiveScoresSection";
import { MyClubSection } from "@/components/MyClubSection";
import { TrustpilotWidget } from "@/components/TrustpilotWidget";
import { Newspaper } from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { useUserPreferences } from "@/lib/hooks/useUserPreferences";

export default function Home() {
  const t = useTranslations("home");
  const locale = useLocale();

  // Get user's favorite team for personalized news
  const { data: preferences } = useUserPreferences({ enabled: true });
  const favoriteTeamName = preferences?.favorite_team?.name;

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Hero Section - Title at top */}
      <section className="text-center py-6 sm:py-8">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 dark:text-white mb-3 sm:mb-4">
          {t("hero.headline")}
        </h1>
        <p className="text-gray-600 dark:text-dark-300 text-sm sm:text-base lg:text-lg max-w-2xl mx-auto px-4">
          {t("hero.subheadline")}
        </p>
        <div className="mt-4 flex justify-center">
          <TrustpilotWidget />
        </div>
      </section>

      {/* Live Scores Section */}
      <section className="px-4 sm:px-0">
        <LiveScoresSection maxMatches={4} />
      </section>

      {/* My Club Section - Favorite team news & summary */}
      <section className="px-4 sm:px-0">
        <MyClubSection />
      </section>

      {/* News Section - Personalized with favorite team if set */}
      <section>
        <div className="flex items-center gap-2 mb-4 px-4 sm:px-0">
          <Newspaper className="w-5 h-5 text-primary-500" />
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            {favoriteTeamName
              ? `${t("sections.news")} - ${favoriteTeamName}`
              : t("sections.news") || "Actualités"}
          </h2>
        </div>
        <NewsFeed team={favoriteTeamName} limit={5} showTitle={false} />
      </section>

      {/* Daily Picks */}
      <section>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 sm:mb-6 gap-2 sm:gap-0 px-4 sm:px-0">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            {t("sections.dailyPicks")}
          </h2>
          <span className="text-gray-500 dark:text-dark-400 text-xs sm:text-sm">
            {t("sections.updated")}: {new Date().toLocaleDateString(locale === "fr" ? "fr-FR" : "en-US")}
          </span>
        </div>
        <DailyPicks />
      </section>

      {/* Upcoming Matches */}
      <section>
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-4 sm:mb-6 px-4 sm:px-0">
          {t("sections.upcomingMatches")}
        </h2>
        <UpcomingMatches />
      </section>
    </div>
  );
}
