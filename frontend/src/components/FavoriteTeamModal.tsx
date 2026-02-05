"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Heart, Search, X, Loader2, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import {
  useUserPreferences,
  useUpdatePreferences,
  useTeamSearch,
  type TeamSearchResult,
} from "@/lib/hooks/useUserPreferences";

const FAVORITE_TEAM_MODAL_KEY = "paris-sportif-favorite-team-asked";

interface FavoriteTeamModalProps {
  /** Force open the modal (for settings page) */
  forceOpen?: boolean;
  /** Callback when modal closes */
  onClose?: () => void;
}

export function FavoriteTeamModal({ forceOpen, onClose }: FavoriteTeamModalProps) {
  const t = useTranslations("favoriteTeam");
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTeam, setSelectedTeam] = useState<TeamSearchResult | null>(null);

  const { data: preferences, isLoading: prefsLoading } = useUserPreferences();
  const { data: searchResults, isLoading: searchLoading } = useTeamSearch(searchQuery);
  const updatePrefs = useUpdatePreferences();

  // Check if we should show the modal after login
  useEffect(() => {
    if (forceOpen) {
      setIsOpen(true);
      return;
    }

    // Don't show if preferences are loading
    if (prefsLoading) return;

    // Don't show if user already has a favorite team
    if (preferences?.favorite_team_id) return;

    // Don't show if we already asked
    const alreadyAsked = localStorage.getItem(FAVORITE_TEAM_MODAL_KEY);
    if (alreadyAsked) return;

    // Show the modal
    const timer = setTimeout(() => setIsOpen(true), 1000);
    return () => clearTimeout(timer);
  }, [forceOpen, prefsLoading, preferences?.favorite_team_id]);

  // Pre-select current favorite team if editing
  useEffect(() => {
    if (preferences?.favorite_team && !selectedTeam) {
      setSelectedTeam({
        id: preferences.favorite_team.id,
        name: preferences.favorite_team.name,
        short_name: preferences.favorite_team.short_name,
        logo_url: preferences.favorite_team.logo_url,
        country: preferences.favorite_team.country,
      });
    }
  }, [preferences?.favorite_team, selectedTeam]);

  const handleClose = useCallback(() => {
    localStorage.setItem(FAVORITE_TEAM_MODAL_KEY, "true");
    setIsOpen(false);
    onClose?.();
  }, [onClose]);

  const handleSkip = useCallback(() => {
    handleClose();
  }, [handleClose]);

  const handleConfirm = useCallback(async () => {
    if (!selectedTeam) return;

    try {
      await updatePrefs.mutateAsync({
        favorite_team_id: selectedTeam.id,
      });
      handleClose();
    } catch (error) {
      console.error("Failed to save favorite team:", error);
    }
  }, [selectedTeam, updatePrefs, handleClose]);

  const handleTeamSelect = useCallback((team: TeamSearchResult) => {
    setSelectedTeam(team);
    setSearchQuery("");
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedTeam(null);
  }, []);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-md bg-dark-900 border-dark-700">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <Heart className="w-5 h-5 text-red-500" />
            {t("title")}
          </DialogTitle>
          <DialogDescription className="text-dark-400">
            {t("description")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Selected Team Display */}
          {selectedTeam && (
            <div className="flex items-center justify-between p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg">
              <div className="flex items-center gap-3">
                {selectedTeam.logo_url && (
                  <img
                    src={selectedTeam.logo_url}
                    alt={selectedTeam.name}
                    className="w-10 h-10 object-contain"
                  />
                )}
                <div>
                  <p className="font-medium text-white">{selectedTeam.name}</p>
                  {selectedTeam.country && (
                    <p className="text-xs text-dark-400">{selectedTeam.country}</p>
                  )}
                </div>
              </div>
              <button
                onClick={handleClearSelection}
                className="p-1 hover:bg-dark-700 rounded-full transition-colors"
              >
                <X className="w-4 h-4 text-dark-400" />
              </button>
            </div>
          )}

          {/* Search Input */}
          {!selectedTeam && (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
              <input
                type="text"
                placeholder={t("searchPlaceholder")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={cn(
                  "w-full pl-10 pr-4 py-3 rounded-lg",
                  "bg-dark-800 border border-dark-700",
                  "text-white placeholder-dark-400",
                  "focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
                )}
                autoFocus
              />
            </div>
          )}

          {/* Search Results */}
          {!selectedTeam && searchQuery.length >= 2 && (
            <div className="max-h-64 overflow-y-auto space-y-1">
              {searchLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
                </div>
              ) : searchResults?.teams && searchResults.teams.length > 0 ? (
                searchResults.teams.map((team) => (
                  <button
                    key={team.id}
                    onClick={() => handleTeamSelect(team)}
                    className={cn(
                      "w-full flex items-center gap-3 p-3 rounded-lg",
                      "hover:bg-dark-700/50 transition-colors",
                      "text-left"
                    )}
                  >
                    {team.logo_url ? (
                      <img
                        src={team.logo_url}
                        alt={team.name}
                        className="w-8 h-8 object-contain"
                      />
                    ) : (
                      <div className="w-8 h-8 bg-dark-700 rounded-full flex items-center justify-center">
                        <span className="text-xs text-dark-400">
                          {team.short_name || team.name.slice(0, 2).toUpperCase()}
                        </span>
                      </div>
                    )}
                    <div>
                      <p className="text-white">{team.name}</p>
                      {team.country && (
                        <p className="text-xs text-dark-400">{team.country}</p>
                      )}
                    </div>
                  </button>
                ))
              ) : (
                <p className="text-center py-8 text-dark-400">{t("noResults")}</p>
              )}
            </div>
          )}

          {/* Instructions when no search */}
          {!selectedTeam && searchQuery.length < 2 && (
            <p className="text-center py-4 text-sm text-dark-400">
              {t("searchHint")}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <Button
            variant="outline"
            onClick={handleSkip}
            className="flex-1 border-dark-600 text-dark-300 hover:bg-dark-800"
          >
            {t("skip")}
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!selectedTeam || updatePrefs.isPending}
            className="flex-1 bg-primary-500 hover:bg-primary-600"
          >
            {updatePrefs.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                {t("confirm")}
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
