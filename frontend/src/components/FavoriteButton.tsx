"use client";

import { Heart } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useFavorites, FavoriteMatch } from "@/hooks/useFavorites";

interface FavoriteButtonProps {
  match: Omit<FavoriteMatch, "addedAt">;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export function FavoriteButton({
  match,
  size = "md",
  showLabel = false,
  className,
}: FavoriteButtonProps) {
  const t = useTranslations("components.favorite");
  const { isFavorite, toggleFavorite } = useFavorites();
  const isActive = isFavorite(match.matchId);

  const sizeClasses = {
    sm: "p-1.5",
    md: "p-2",
    lg: "p-2.5",
  };

  const iconSizes = {
    sm: "w-4 h-4",
    md: "w-5 h-5",
    lg: "w-6 h-6",
  };

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    toggleFavorite(match);
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        "rounded-full transition-all duration-200",
        sizeClasses[size],
        isActive
          ? "bg-red-100 dark:bg-red-500/20 hover:bg-red-200 dark:hover:bg-red-500/30"
          : "bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600",
        showLabel && "flex items-center gap-2",
        className
      )}
      title={isActive ? t("remove") : t("add")}
    >
      <Heart
        className={cn(
          iconSizes[size],
          "transition-colors duration-200",
          isActive
            ? "text-red-500 fill-red-500"
            : "text-gray-400 dark:text-dark-400 hover:text-red-400"
        )}
      />
      {showLabel && (
        <span
          className={cn(
            "text-sm font-medium",
            isActive
              ? "text-red-600 dark:text-red-400"
              : "text-gray-600 dark:text-dark-400"
          )}
        >
          {isActive ? t("active") : t("inactive")}
        </span>
      )}
    </button>
  );
}
