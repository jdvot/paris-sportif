"use client";

import { useState, useCallback } from "react";
import { Newspaper } from "lucide-react";
import { useTranslations } from "next-intl";
import { NewsFeed } from "@/components/NewsFeed";
import { CompetitionFilter } from "@/components/CompetitionFilter";
import { COMPETITIONS as COMPETITIONS_DATA } from "@/lib/constants";

const COMPETITIONS = COMPETITIONS_DATA.map((c) => ({ id: c.code, name: c.name }));

export default function NewsPage() {
  const t = useTranslations("newsFeed");
  const [selectedCompetitions, setSelectedCompetitions] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  const toggleCompetition = useCallback((competitionId: string) => {
    setSelectedCompetitions((prev) =>
      prev.includes(competitionId)
        ? prev.filter((c) => c !== competitionId)
        : [...prev, competitionId]
    );
  }, []);

  const clearCompetitions = useCallback(() => {
    setSelectedCompetitions([]);
  }, []);

  // Map selected competition codes to names for the NewsFeed component
  const selectedCompetitionName =
    selectedCompetitions.length === 1
      ? COMPETITIONS.find((c) => c.id === selectedCompetitions[0])?.name
      : undefined;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <Newspaper className="w-8 h-8 text-primary-500" />
          {t("title")}
        </h1>
        <p className="text-gray-600 dark:text-dark-400 mt-1">
          {t("subtitle")}
        </p>
      </div>

      {/* Competition Filter */}
      <CompetitionFilter
        competitions={COMPETITIONS}
        selected={selectedCompetitions}
        onToggle={toggleCompetition}
        onClear={clearCompetitions}
        isOpen={showFilters}
        onToggleOpen={() => setShowFilters((prev) => !prev)}
      />

      {/* News Feed */}
      <NewsFeed
        competition={selectedCompetitionName}
        limit={20}
        showTitle={false}
      />
    </div>
  );
}
