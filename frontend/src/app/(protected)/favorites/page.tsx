"use client";

import { Heart, Trash2, ArrowLeft, Calendar } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { useFavorites } from "@/hooks/useFavorites";
import { cn } from "@/lib/utils";

export default function FavoritesPage() {
  const { favorites, isLoaded, removeFavorite, clearFavorites } = useFavorites();

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Heart className="w-8 h-8 text-red-500 fill-red-500" />
            Mes Favoris
          </h1>
          <p className="text-gray-600 dark:text-dark-400 mt-1">
            {favorites.length} match{favorites.length !== 1 ? "s" : ""} sauvegarde
            {favorites.length !== 1 ? "s" : ""}
          </p>
        </div>
        {favorites.length > 0 && (
          <button
            onClick={() => {
              if (confirm("Voulez-vous vraiment supprimer tous les favoris ?")) {
                clearFavorites();
              }
            }}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Tout supprimer
          </button>
        )}
      </div>

      {/* Empty State */}
      {favorites.length === 0 && (
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-8 sm:p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-dark-700 flex items-center justify-center">
            <Heart className="w-8 h-8 text-gray-400 dark:text-dark-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Aucun favori
          </h3>
          <p className="text-gray-600 dark:text-dark-400 mb-6 max-w-sm mx-auto">
            Ajoutez des matchs a vos favoris pour les retrouver facilement ici.
          </p>
          <Link
            href="/picks"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Voir les picks
          </Link>
        </div>
      )}

      {/* Favorites List */}
      {favorites.length > 0 && (
        <div className="grid gap-3">
          {favorites
            .sort((a, b) => new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime())
            .map((favorite) => (
              <div
                key={favorite.matchId}
                className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-5 hover:border-primary-400 dark:hover:border-primary-500/50 transition-colors"
              >
                <div className="flex items-center justify-between gap-4">
                  <Link
                    href={`/match/${favorite.matchId}`}
                    className="flex-1 min-w-0"
                  >
                    <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                      {favorite.homeTeam} vs {favorite.awayTeam}
                    </h3>
                    <div className="flex items-center gap-3 mt-1 text-sm text-gray-600 dark:text-dark-400">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {format(new Date(favorite.matchDate), "d MMM yyyy, HH:mm", {
                          locale: fr,
                        })}
                      </span>
                      {favorite.competition && (
                        <span className="px-2 py-0.5 bg-gray-100 dark:bg-dark-700 rounded text-xs">
                          {favorite.competition}
                        </span>
                      )}
                    </div>
                  </Link>
                  <button
                    onClick={() => removeFavorite(favorite.matchId)}
                    className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    title="Retirer des favoris"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
        </div>
      )}

      {/* Info */}
      <div className="bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30 rounded-xl p-4">
        <p className="text-sm text-blue-800 dark:text-blue-300">
          💡 Les favoris sont sauvegardes localement et expires automatiquement apres 7 jours.
        </p>
      </div>
    </div>
  );
}
