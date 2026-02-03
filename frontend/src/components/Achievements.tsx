"use client";

import { useState } from "react";
import { Trophy, Lock, Star, Sparkles, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAchievements, Achievement } from "@/hooks/useAchievements";
import { useLocale } from "next-intl";

interface AchievementsProps {
  variant?: "compact" | "full" | "showcase";
  className?: string;
  maxDisplay?: number;
}

const RARITY_STYLES = {
  common: {
    bg: "bg-gray-100 dark:bg-gray-700/50",
    border: "border-gray-300 dark:border-gray-600",
    text: "text-gray-600 dark:text-gray-300",
    glow: "",
  },
  rare: {
    bg: "bg-blue-50 dark:bg-blue-900/30",
    border: "border-blue-300 dark:border-blue-600",
    text: "text-blue-600 dark:text-blue-300",
    glow: "shadow-blue-500/20",
  },
  epic: {
    bg: "bg-purple-50 dark:bg-purple-900/30",
    border: "border-purple-300 dark:border-purple-600",
    text: "text-purple-600 dark:text-purple-300",
    glow: "shadow-purple-500/30",
  },
  legendary: {
    bg: "bg-gradient-to-br from-yellow-50 to-orange-50 dark:from-yellow-900/30 dark:to-orange-900/30",
    border: "border-yellow-400 dark:border-yellow-500",
    text: "text-yellow-600 dark:text-yellow-300",
    glow: "shadow-yellow-500/40 shadow-lg",
  },
};

const RARITY_LABELS = {
  common: { fr: "Commun", en: "Common" },
  rare: { fr: "Rare", en: "Rare" },
  epic: { fr: "Epique", en: "Epic" },
  legendary: { fr: "Legendaire", en: "Legendary" },
};

function AchievementBadge({
  achievement,
  isLocked = false,
  size = "md",
  showDetails = false,
  locale = "fr",
}: {
  achievement: Achievement;
  isLocked?: boolean;
  size?: "sm" | "md" | "lg";
  showDetails?: boolean;
  locale?: string;
}) {
  const styles = RARITY_STYLES[achievement.rarity];
  const sizeClasses = {
    sm: "w-10 h-10 text-lg",
    md: "w-14 h-14 text-2xl",
    lg: "w-20 h-20 text-4xl",
  };

  const name = locale === "en" ? achievement.nameEn : achievement.name;
  const description =
    locale === "en" ? achievement.descriptionEn : achievement.description;
  const rarityLabel =
    RARITY_LABELS[achievement.rarity][locale === "en" ? "en" : "fr"];

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 group",
        showDetails && "p-3"
      )}
    >
      <div
        className={cn(
          "relative rounded-full flex items-center justify-center border-2 transition-all duration-300",
          sizeClasses[size],
          isLocked
            ? "bg-gray-200 dark:bg-gray-800 border-gray-300 dark:border-gray-700 opacity-50"
            : cn(styles.bg, styles.border, styles.glow),
          !isLocked && "hover:scale-110"
        )}
        title={`${name}: ${description}`}
      >
        {isLocked ? (
          <Lock className="w-1/2 h-1/2 text-gray-400 dark:text-gray-500" />
        ) : (
          <span className="select-none">{achievement.icon}</span>
        )}
        {!isLocked && achievement.rarity === "legendary" && (
          <div className="absolute inset-0 rounded-full animate-pulse bg-yellow-400/20" />
        )}
      </div>
      {showDetails && (
        <div className="text-center">
          <p
            className={cn(
              "text-sm font-medium",
              isLocked ? "text-gray-400 dark:text-gray-500" : styles.text
            )}
          >
            {name}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {description}
          </p>
          <div className="flex items-center justify-center gap-2 mt-1">
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded-full",
                isLocked
                  ? "bg-gray-100 dark:bg-gray-800 text-gray-400"
                  : cn(styles.bg, styles.text)
              )}
            >
              {rarityLabel}
            </span>
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Star className="w-3 h-3" />
              {achievement.xp} XP
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function AchievementNotification({
  achievement,
  onDismiss,
  locale = "fr",
}: {
  achievement: Achievement;
  onDismiss: () => void;
  locale?: string;
}) {
  const styles = RARITY_STYLES[achievement.rarity];
  const name = locale === "en" ? achievement.nameEn : achievement.name;
  const description =
    locale === "en" ? achievement.descriptionEn : achievement.description;

  return (
    <div
      className={cn(
        "fixed bottom-4 right-4 z-50 p-4 rounded-xl border-2 shadow-2xl",
        "animate-in slide-in-from-bottom-5 fade-in duration-500",
        styles.bg,
        styles.border,
        styles.glow
      )}
    >
      <button
        onClick={onDismiss}
        className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
      >
        <X className="w-4 h-4" />
      </button>
      <div className="flex items-center gap-4">
        <div
          className={cn(
            "w-16 h-16 rounded-full flex items-center justify-center text-3xl border-2",
            styles.bg,
            styles.border
          )}
        >
          {achievement.icon}
        </div>
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-yellow-500" />
            <span className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
              {locale === "en" ? "Achievement Unlocked!" : "Succes Debloque!"}
            </span>
          </div>
          <p className={cn("text-lg font-bold", styles.text)}>{name}</p>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            {description}
          </p>
          <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
            <Star className="w-3 h-3" />+{achievement.xp} XP
          </p>
        </div>
      </div>
    </div>
  );
}

export function Achievements({
  variant = "compact",
  className,
  maxDisplay = 6,
}: AchievementsProps) {
  const locale = useLocale();
  const [showAll, setShowAll] = useState(false);
  const {
    level,
    totalXP,
    levelProgress,
    xpToNextLevel,
    unlockedAchievements,
    lockedAchievements,
    allAchievements,
    unlockedCount,
    totalCount,
    newUnlock,
    dismissNotification,
    isLoaded,
  } = useAchievements();

  if (!isLoaded) {
    return (
      <div
        className={cn(
          "animate-pulse bg-gray-200 dark:bg-gray-800 rounded-lg h-24",
          className
        )}
      />
    );
  }

  // Compact variant - just shows unlocked count and recent badges
  if (variant === "compact") {
    const recentUnlocked = [...unlockedAchievements]
      .sort(
        (a, b) =>
          new Date(b.unlockedAt!).getTime() - new Date(a.unlockedAt!).getTime()
      )
      .slice(0, 4);

    return (
      <>
        <div
          className={cn(
            "flex items-center gap-3 p-3 rounded-lg",
            "bg-gradient-to-r from-purple-100 dark:from-purple-500/10 to-pink-100 dark:to-pink-500/10",
            "border border-purple-200 dark:border-purple-500/30",
            className
          )}
        >
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-full bg-purple-500/20">
              <Trophy className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {locale === "en" ? "Achievements" : "Succes"}
              </p>
              <p className="text-lg font-bold text-purple-600 dark:text-purple-400">
                {unlockedCount}/{totalCount}
              </p>
            </div>
          </div>
          <div className="flex -space-x-2">
            {recentUnlocked.map((achievement) => (
              <div
                key={achievement.id}
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center border-2 border-white dark:border-gray-800",
                  RARITY_STYLES[achievement.rarity].bg
                )}
                title={locale === "en" ? achievement.nameEn : achievement.name}
              >
                <span className="text-sm">{achievement.icon}</span>
              </div>
            ))}
          </div>
          <div className="ml-auto text-right">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {locale === "en" ? "Level" : "Niveau"}
            </p>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">
              {level}
            </p>
          </div>
        </div>
        {newUnlock && (
          <AchievementNotification
            achievement={newUnlock}
            onDismiss={dismissNotification}
            locale={locale}
          />
        )}
      </>
    );
  }

  // Showcase variant - displays featured achievements
  if (variant === "showcase") {
    const featured = [...unlockedAchievements]
      .sort((a, b) => {
        const rarityOrder = { legendary: 0, epic: 1, rare: 2, common: 3 };
        return rarityOrder[a.rarity] - rarityOrder[b.rarity];
      })
      .slice(0, maxDisplay);

    return (
      <>
        <div className={cn("flex flex-wrap gap-2 justify-center", className)}>
          {featured.map((achievement) => (
            <AchievementBadge
              key={achievement.id}
              achievement={achievement}
              size="sm"
              locale={locale}
            />
          ))}
          {unlockedCount === 0 && (
            <p className="text-sm text-gray-400 dark:text-gray-500">
              {locale === "en"
                ? "No achievements yet"
                : "Aucun succes pour le moment"}
            </p>
          )}
        </div>
        {newUnlock && (
          <AchievementNotification
            achievement={newUnlock}
            onDismiss={dismissNotification}
            locale={locale}
          />
        )}
      </>
    );
  }

  // Full variant - complete achievements panel
  const displayedAchievements = showAll
    ? allAchievements
    : allAchievements.slice(0, maxDisplay);

  return (
    <>
      <div
        className={cn(
          "bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-4 sm:p-6",
          className
        )}
      >
        {/* Header with Level */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Trophy className="w-5 h-5 text-purple-500" />
            {locale === "en" ? "Achievements" : "Succes"}
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {locale === "en" ? "Level" : "Niveau"}
            </span>
            <span className="px-3 py-1 rounded-full bg-purple-100 dark:bg-purple-500/20 text-purple-600 dark:text-purple-300 font-bold">
              {level}
            </span>
          </div>
        </div>

        {/* XP Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600 dark:text-gray-400">
              {totalXP} XP
            </span>
            <span className="text-gray-400 dark:text-gray-500">
              {xpToNextLevel} XP{" "}
              {locale === "en" ? "to next level" : "avant prochain niveau"}
            </span>
          </div>
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
              style={{ width: `${levelProgress}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-2 mb-6">
          {(["common", "rare", "epic", "legendary"] as const).map((rarity) => {
            const count = unlockedAchievements.filter(
              (a) => a.rarity === rarity
            ).length;
            const total = allAchievements.filter(
              (a) => a.rarity === rarity
            ).length;
            return (
              <div
                key={rarity}
                className={cn(
                  "text-center p-2 rounded-lg",
                  RARITY_STYLES[rarity].bg
                )}
              >
                <p className={cn("text-lg font-bold", RARITY_STYLES[rarity].text)}>
                  {count}/{total}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                  {RARITY_LABELS[rarity][locale === "en" ? "en" : "fr"]}
                </p>
              </div>
            );
          })}
        </div>

        {/* Achievements Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {displayedAchievements.map((achievement) => (
            <AchievementBadge
              key={achievement.id}
              achievement={achievement}
              isLocked={!achievement.unlockedAt}
              showDetails
              locale={locale}
            />
          ))}
        </div>

        {/* Show More Button */}
        {allAchievements.length > maxDisplay && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="w-full mt-4 py-2 text-sm text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-500/10 rounded-lg transition-colors"
          >
            {showAll
              ? locale === "en"
                ? "Show less"
                : "Voir moins"
              : locale === "en"
                ? `Show all (${allAchievements.length})`
                : `Voir tout (${allAchievements.length})`}
          </button>
        )}
      </div>

      {/* Achievement Notification */}
      {newUnlock && (
        <AchievementNotification
          achievement={newUnlock}
          onDismiss={dismissNotification}
          locale={locale}
        />
      )}
    </>
  );
}
