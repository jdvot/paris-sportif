"use client";

import { useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import {
  User,
  Mail,
  Calendar,
  Crown,
  Shield,
  Edit2,
  Check,
  X,
  Loader2,
  Zap,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function ProfilePage() {
  const { user, profile, role, loading, isAuthenticated, isPremium, isAdmin } =
    useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 dark:text-dark-400 mb-4">
            Vous devez etre connecte pour acceder a cette page.
          </p>
          <Link
            href="/auth/login"
            className="text-primary-600 dark:text-primary-400 hover:underline"
          >
            Se connecter
          </Link>
        </div>
      </div>
    );
  }

  const displayName =
    profile?.full_name || user.user_metadata?.full_name || "Utilisateur";
  const email = user.email || "";
  const createdAt = user.created_at ? new Date(user.created_at) : new Date();

  const handleEditStart = () => {
    setEditedName(displayName);
    setIsEditing(true);
  };

  const handleEditCancel = () => {
    setIsEditing(false);
    setEditedName("");
  };

  const handleEditSave = async () => {
    setIsSaving(true);
    // TODO: Implement profile update via API
    // For now, just simulate a save
    await new Promise((resolve) => setTimeout(resolve, 500));
    setIsSaving(false);
    setIsEditing(false);
  };

  const getRoleBadge = () => {
    if (isAdmin) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300 rounded-full text-sm font-medium">
          <Shield className="w-4 h-4" />
          Admin
        </span>
      );
    }
    if (isPremium) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300 rounded-full text-sm font-medium">
          <Crown className="w-4 h-4" />
          Premium
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-100 dark:bg-dark-700 text-gray-700 dark:text-dark-300 rounded-full text-sm font-medium">
        <User className="w-4 h-4" />
        Gratuit
      </span>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-8">
        Mon Profil
      </h1>

      {/* Profile Card */}
      <div className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden">
        {/* Header with Avatar */}
        <div className="bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-8">
          <div className="flex items-center gap-4">
            {/* Avatar */}
            <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center text-white text-3xl font-bold">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1">
              {isEditing ? (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={editedName}
                    onChange={(e) => setEditedName(e.target.value)}
                    className="px-3 py-1.5 bg-white/20 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
                    placeholder="Votre nom"
                  />
                  <button
                    onClick={handleEditSave}
                    disabled={isSaving}
                    className="p-1.5 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
                  >
                    {isSaving ? (
                      <Loader2 className="w-5 h-5 text-white animate-spin" />
                    ) : (
                      <Check className="w-5 h-5 text-white" />
                    )}
                  </button>
                  <button
                    onClick={handleEditCancel}
                    className="p-1.5 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5 text-white" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <h2 className="text-xl sm:text-2xl font-bold text-white">
                    {displayName}
                  </h2>
                  <button
                    onClick={handleEditStart}
                    className="p-1.5 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
                  >
                    <Edit2 className="w-4 h-4 text-white" />
                  </button>
                </div>
              )}
              <div className="mt-2">{getRoleBadge()}</div>
            </div>
          </div>
        </div>

        {/* Info Section */}
        <div className="p-6 space-y-4">
          <div className="flex items-center gap-3 text-gray-700 dark:text-dark-300">
            <Mail className="w-5 h-5 text-gray-400 dark:text-dark-500" />
            <span>{email}</span>
          </div>

          <div className="flex items-center gap-3 text-gray-700 dark:text-dark-300">
            <Calendar className="w-5 h-5 text-gray-400 dark:text-dark-500" />
            <span>
              Membre depuis le{" "}
              {format(createdAt, "d MMMM yyyy", { locale: fr })}
            </span>
          </div>
        </div>

        {/* Upgrade CTA for free users */}
        {!isPremium && !isAdmin && (
          <div className="border-t border-gray-200 dark:border-dark-700 p-6">
            <div className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-500/10 dark:to-orange-500/10 border border-yellow-200 dark:border-yellow-500/30 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <Zap className="w-6 h-6 text-yellow-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                    Passez a Premium
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-dark-400 mb-3">
                    Debloquez toutes les predictions detaillees et les 5 picks
                    quotidiens IA.
                  </p>
                  <Link
                    href="/plans"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black font-medium rounded-lg transition-colors"
                  >
                    <Crown className="w-4 h-4" />
                    Voir les offres
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="mt-6 grid grid-cols-2 gap-4">
        <Link
          href="/settings"
          className="flex items-center justify-center gap-2 p-4 bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl hover:border-primary-500/50 transition-colors"
        >
          <span className="text-gray-700 dark:text-dark-300">Parametres</span>
        </Link>
        <Link
          href="/picks"
          className="flex items-center justify-center gap-2 p-4 bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl hover:border-primary-500/50 transition-colors"
        >
          <span className="text-gray-700 dark:text-dark-300">Mes Picks</span>
        </Link>
      </div>
    </div>
  );
}
