"use client";

import { useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import type { Locale } from "date-fns/locale";
import { useTranslations, useLocale } from "next-intl";
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
  TrendingUp,
  Target,
  Trophy,
  Eye,
  Star,
  Activity,
  ChevronRight,
  BarChart3,
  Settings,
  History,
  CreditCard,
  Sparkles,
  Lock,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import {
  useGetUserStatsApiV1UsersMeStatsGet,
  useUpdateProfileApiV1UsersMePatch,
  getGetCurrentProfileApiV1UsersMeGetQueryKey,
} from "@/lib/api/endpoints/users/users";
import { useListBets } from "@/lib/api/endpoints/bets/bets";
import { cn } from "@/lib/utils";
import { type UserRole } from "@/lib/supabase/types";
import { useQueryClient } from "@tanstack/react-query";
import { Achievements } from "@/components/Achievements";
import { StreakTracker } from "@/components/StreakTracker";

export default function ProfilePage() {
  const { user, profile, loading, isAuthenticated, isPremium, isAdmin, resetPassword } =
    useAuth();
  const queryClient = useQueryClient();
  const t = useTranslations("profile");
  const locale = useLocale();
  const dateLocale: Locale = locale === "fr" ? fr : enUS;

  // Edit mode states
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState("");
  const [showEditSection, setShowEditSection] = useState(false);

  // Password reset states
  const [passwordResetSent, setPasswordResetSent] = useState(false);
  const [passwordResetLoading, setPasswordResetLoading] = useState(false);
  const [passwordResetError, setPasswordResetError] = useState<string | null>(null);

  // Update profile mutation
  const updateProfileMutation = useUpdateProfileApiV1UsersMePatch({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetCurrentProfileApiV1UsersMeGetQueryKey() });
        setIsEditing(false);
        setShowEditSection(false);
      },
    },
  });

  // Fetch user stats
  const { data: statsResponse, isLoading: statsLoading } =
    useGetUserStatsApiV1UsersMeStatsGet({
      query: { enabled: isAuthenticated },
    });

  // Fetch user bets
  const { data: betsResponse, isLoading: betsLoading } = useListBets({
    query: { enabled: isAuthenticated },
  });

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
            {t("loginRequired")}
          </p>
          <Link
            href="/auth/login"
            className="text-primary-600 dark:text-primary-400 hover:underline"
          >
            {t("signIn")}
          </Link>
        </div>
      </div>
    );
  }

  const displayName =
    profile?.full_name || user.user_metadata?.full_name || t("defaultName");
  const email = user.email || "";
  const createdAt = user.created_at ? new Date(user.created_at) : new Date();

  // Get stats from API
  const userStats = statsResponse?.status === 200 ? statsResponse.data : null;
  const bets = betsResponse?.status === 200 ? betsResponse.data : [];

  // Calculate bet statistics
  const wonBets = bets.filter((b) => b.status === "won").length;
  const lostBets = bets.filter((b) => b.status === "lost").length;
  const pendingBets = bets.filter((b) => b.status === "pending").length;
  const winRate = wonBets + lostBets > 0 ? (wonBets / (wonBets + lostBets)) * 100 : 0;

  const handleEditStart = () => {
    setEditedName(displayName);
    setIsEditing(true);
  };

  const handleEditCancel = () => {
    setIsEditing(false);
    setEditedName("");
  };

  const handleEditSave = async () => {
    if (!editedName.trim()) return;
    updateProfileMutation.mutate({ data: { full_name: editedName.trim() } });
  };

  const handlePasswordReset = async () => {
    if (!email) return;
    setPasswordResetLoading(true);
    setPasswordResetError(null);

    const { error } = await resetPassword(email);

    setPasswordResetLoading(false);
    if (error) {
      setPasswordResetError(error.message);
    } else {
      setPasswordResetSent(true);
    }
  };

  const handleOpenEditSection = () => {
    setEditedName(displayName);
    setShowEditSection(true);
  };

  const getRoleBadge = () => {
    if (isAdmin) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300 rounded-full text-sm font-medium">
          <Shield className="w-4 h-4" />
          {t("roles.admin")}
        </span>
      );
    }
    if (isPremium) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300 rounded-full text-sm font-medium">
          <Crown className="w-4 h-4" />
          {t("roles.premium")}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-100 dark:bg-dark-700 text-gray-700 dark:text-dark-300 rounded-full text-sm font-medium">
        <User className="w-4 h-4" />
        {t("roles.free")}
      </span>
    );
  };

  // Get plan info
  const currentRole: UserRole = isAdmin ? "admin" : isPremium ? "premium" : "free";
  // const _permissions = ROLE_PERMISSIONS[currentRole]; // Reserved for future use

  const planDetails = {
    free: {
      name: t("subscription.free"),
      price: "0€",
      color: "gray",
      icon: User,
      features: [
        { label: t("plan.matchAccess"), included: true },
        { label: t("plan.basicStats"), included: true },
        { label: t("plan.picksLimit"), included: true },
        { label: t("plan.detailedPredictions"), included: false },
        { label: t("plan.ragAnalysis"), included: false },
        { label: t("plan.fullHistory"), included: false },
        { label: t("plan.customAlerts"), included: false },
      ],
    },
    premium: {
      name: t("subscription.premium"),
      price: "9.99€",
      color: "yellow",
      icon: Crown,
      features: [
        { label: t("plan.matchAccess"), included: true },
        { label: t("plan.advancedStats"), included: true },
        { label: t("plan.unlimitedPicks"), included: true },
        { label: t("plan.detailedPredictions"), included: true },
        { label: t("plan.ragAnalysis"), included: true },
        { label: t("plan.fullHistory"), included: true },
        { label: t("plan.customAlerts"), included: true },
      ],
    },
    admin: {
      name: t("subscription.admin"),
      price: "∞",
      color: "red",
      icon: Shield,
      features: [
        { label: t("plan.allPremium"), included: true },
        { label: t("plan.adminDashboard"), included: true },
        { label: t("plan.userManagement"), included: true },
        { label: t("plan.dataSync"), included: true },
        { label: t("plan.systemLogs"), included: true },
      ],
    },
  };

  const currentPlan = planDetails[currentRole];

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-8">
        {t("title")}
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Profile Card */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden">
            {/* Header with Avatar */}
            <div className="bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-8">
              <div className="flex items-center gap-4">
                {/* Avatar */}
                <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center text-white text-3xl font-bold ring-4 ring-white/30">
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
                        placeholder={t("yourName")}
                      />
                      <button
                        onClick={handleEditSave}
                        disabled={updateProfileMutation.isPending}
                        className="p-1.5 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
                      >
                        {updateProfileMutation.isPending ? (
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
                        title={t("editName")}
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
                  {t("memberSince")}{" "}
                  {format(createdAt, "d MMMM yyyy", { locale: dateLocale })}
                </span>
              </div>

              {userStats?.member_since_days !== undefined && (
                <div className="flex items-center gap-3 text-gray-700 dark:text-dark-300">
                  <Activity className="w-5 h-5 text-gray-400 dark:text-dark-500" />
                  <span>{t("daysOld", { days: userStats.member_since_days })}</span>
                </div>
              )}

              {userStats?.favorite_competition && (
                <div className="flex items-center gap-3 text-gray-700 dark:text-dark-300">
                  <Star className="w-5 h-5 text-yellow-500" />
                  <span>{t("favoriteCompetition")} {userStats.favorite_competition}</span>
                </div>
              )}

              {/* Edit Profile Button */}
              {!showEditSection && (
                <button
                  onClick={handleOpenEditSection}
                  className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-500/10 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-500/20 transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                  {t("edit.title")}
                </button>
              )}
            </div>

            {/* Edit Profile Section */}
            {showEditSection && (
              <div className="border-t border-gray-200 dark:border-dark-700 p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <Edit2 className="w-5 h-5 text-primary-500" />
                    {t("edit.title")}
                  </h3>
                  <button
                    onClick={() => setShowEditSection(false)}
                    className="p-1.5 text-gray-400 hover:text-gray-600 dark:text-dark-500 dark:hover:text-dark-300 transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-6">
                  {/* Name Field */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-dark-300 mb-2">
                      {t("edit.fullName")}
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={editedName}
                        onChange={(e) => setEditedName(e.target.value)}
                        className="flex-1 px-4 py-2.5 bg-gray-50 dark:bg-dark-800 border border-gray-200 dark:border-dark-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-dark-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder={t("edit.fullNamePlaceholder")}
                      />
                      <button
                        onClick={handleEditSave}
                        disabled={updateProfileMutation.isPending || !editedName.trim()}
                        className="px-4 py-2.5 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-300 dark:disabled:bg-primary-800 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                      >
                        {updateProfileMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Check className="w-4 h-4" />
                        )}
                        {t("edit.save")}
                      </button>
                    </div>
                    {updateProfileMutation.isError && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                        {t("edit.error")}
                      </p>
                    )}
                    {updateProfileMutation.isSuccess && (
                      <p className="mt-2 text-sm text-green-600 dark:text-green-400">
                        {t("edit.success")}
                      </p>
                    )}
                  </div>

                  {/* Email Field (Read-only) */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-dark-300 mb-2">
                      {t("email.label")}
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="email"
                        value={email}
                        disabled
                        className="flex-1 px-4 py-2.5 bg-gray-100 dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-lg text-gray-500 dark:text-dark-400 cursor-not-allowed"
                      />
                      <div className="px-3 py-2.5 text-xs text-gray-500 dark:text-dark-400 bg-gray-100 dark:bg-dark-800 border border-gray-200 dark:border-dark-700 rounded-lg flex items-center">
                        <Lock className="w-4 h-4" />
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-gray-500 dark:text-dark-400">
                      {t("email.cannotChange")}
                    </p>
                  </div>

                  {/* Password Reset */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-dark-300 mb-2">
                      {t("password.label")}
                    </label>
                    {passwordResetSent ? (
                      <div className="p-4 bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded-lg">
                        <p className="text-sm text-green-700 dark:text-green-400 flex items-center gap-2">
                          <Check className="w-4 h-4" />
                          {t("password.resetSent", { email })}
                        </p>
                      </div>
                    ) : (
                      <div className="flex flex-col sm:flex-row gap-3">
                        <div className="flex-1 px-4 py-2.5 bg-gray-100 dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-lg text-gray-500 dark:text-dark-400">
                          ••••••••••••
                        </div>
                        <button
                          onClick={handlePasswordReset}
                          disabled={passwordResetLoading}
                          className="px-4 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-medium rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors flex items-center justify-center gap-2"
                        >
                          {passwordResetLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Lock className="w-4 h-4" />
                          )}
                          {t("password.change")}
                        </button>
                      </div>
                    )}
                    {passwordResetError && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                        {passwordResetError}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-gray-500 dark:text-dark-400">
                      {t("password.resetHint")}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Subscription Plan Section */}
            <div className="border-t border-gray-200 dark:border-dark-700 p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-primary-500" />
                {t("subscription.title")}
              </h3>

              <div className={cn(
                "rounded-xl p-4 border",
                currentRole === "admin"
                  ? "bg-gradient-to-r from-red-50 to-red-100 dark:from-red-500/10 dark:to-red-500/5 border-red-200 dark:border-red-500/30"
                  : currentRole === "premium"
                  ? "bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-500/10 dark:to-orange-500/5 border-yellow-200 dark:border-yellow-500/30"
                  : "bg-gray-50 dark:bg-dark-800 border-gray-200 dark:border-dark-700"
              )}>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-12 h-12 rounded-xl flex items-center justify-center",
                      currentRole === "admin"
                        ? "bg-red-100 dark:bg-red-500/20"
                        : currentRole === "premium"
                        ? "bg-yellow-100 dark:bg-yellow-500/20"
                        : "bg-gray-200 dark:bg-dark-700"
                    )}>
                      <currentPlan.icon className={cn(
                        "w-6 h-6",
                        currentRole === "admin"
                          ? "text-red-600 dark:text-red-400"
                          : currentRole === "premium"
                          ? "text-yellow-600 dark:text-yellow-400"
                          : "text-gray-600 dark:text-dark-400"
                      )} />
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900 dark:text-white text-lg">
                        Plan {currentPlan.name}
                      </h4>
                      <p className="text-sm text-gray-500 dark:text-dark-400">
                        {currentRole === "admin" ? t("subscription.fullAccess") : t("subscription.perMonth", { price: currentPlan.price })}
                      </p>
                    </div>
                  </div>
                  {currentRole === "premium" && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400 rounded-full text-xs font-medium">
                      <Sparkles className="w-3 h-3" />
                      {t("subscription.active")}
                    </span>
                  )}
                </div>

                {/* Features Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
                  {currentPlan.features.map((feature, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm">
                      {feature.included ? (
                        <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                      ) : (
                        <Lock className="w-4 h-4 text-gray-400 dark:text-dark-500 flex-shrink-0" />
                      )}
                      <span className={cn(
                        feature.included
                          ? "text-gray-700 dark:text-dark-300"
                          : "text-gray-400 dark:text-dark-500 line-through"
                      )}>
                        {feature.label}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Upgrade CTA for free users */}
                {!isPremium && !isAdmin && (
                  <div className="pt-4 border-t border-gray-200 dark:border-dark-700">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-dark-400">
                        <Zap className="w-4 h-4 text-yellow-500" />
                        <span>{t("subscription.unlock")}</span>
                      </div>
                      <Link
                        href="/plans"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black font-medium rounded-lg transition-colors text-sm"
                      >
                        <Crown className="w-4 h-4" />
                        {t("subscription.upgrade")}
                        <ArrowRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>
                )}

                {/* Manage subscription for premium users */}
                {isPremium && !isAdmin && (
                  <div className="pt-4 border-t border-yellow-200 dark:border-yellow-500/30">
                    <Link
                      href="/plans"
                      className="text-sm text-yellow-700 dark:text-yellow-400 hover:underline flex items-center gap-1"
                    >
                      {t("subscription.manage")}
                      <ChevronRight className="w-4 h-4" />
                    </Link>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Stats Sidebar */}
        <div className="space-y-6">
          {/* Activity Stats */}
          <div className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl p-6">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary-500" />
              {t("activity.title")}
            </h3>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-600 dark:text-dark-400">
                  <Eye className="w-4 h-4" />
                  <span className="text-sm">{t("activity.predictionsViewed")}</span>
                </div>
                <span className="font-bold text-gray-900 dark:text-white">
                  {statsLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    userStats?.total_predictions_viewed ?? 0
                  )}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-600 dark:text-dark-400">
                  <Target className="w-4 h-4" />
                  <span className="text-sm">{t("activity.betsPlaced")}</span>
                </div>
                <span className="font-bold text-gray-900 dark:text-white">
                  {betsLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    bets.length
                  )}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-600 dark:text-dark-400">
                  <Trophy className="w-4 h-4" />
                  <span className="text-sm">{t("activity.betsWon")}</span>
                </div>
                <span className="font-bold text-primary-600 dark:text-primary-400">
                  {betsLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    wonBets
                  )}
                </span>
              </div>
            </div>
          </div>

          {/* Win Rate Card */}
          {bets.length > 0 && (
            <div className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl p-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-primary-500" />
                {t("performance.title")}
              </h3>

              <div className="text-center mb-4">
                <div className={cn(
                  "text-4xl font-bold",
                  winRate >= 60 ? "text-primary-600 dark:text-primary-400" :
                  winRate >= 50 ? "text-yellow-600 dark:text-yellow-400" :
                  "text-red-600 dark:text-red-400"
                )}>
                  {winRate.toFixed(1)}%
                </div>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {t("performance.winRate")}
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center text-sm">
                <div className="bg-primary-50 dark:bg-primary-500/10 rounded-lg p-2">
                  <div className="font-bold text-primary-600 dark:text-primary-400">{wonBets}</div>
                  <div className="text-gray-500 dark:text-dark-400 text-xs">{t("performance.won")}</div>
                </div>
                <div className="bg-red-50 dark:bg-red-500/10 rounded-lg p-2">
                  <div className="font-bold text-red-600 dark:text-red-400">{lostBets}</div>
                  <div className="text-gray-500 dark:text-dark-400 text-xs">{t("performance.lost")}</div>
                </div>
                <div className="bg-yellow-50 dark:bg-yellow-500/10 rounded-lg p-2">
                  <div className="font-bold text-yellow-600 dark:text-yellow-400">{pendingBets}</div>
                  <div className="text-gray-500 dark:text-dark-400 text-xs">{t("performance.pending")}</div>
                </div>
              </div>
            </div>
          )}

          {/* Quick Links */}
          <div className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden">
            <Link
              href="/plans"
              className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-dark-800 transition-colors border-b border-gray-200 dark:border-dark-700"
            >
              <div className="flex items-center gap-3">
                <Crown className="w-5 h-5 text-yellow-500" />
                <span className="text-gray-700 dark:text-dark-300">{t("links.plans")}</span>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400 dark:text-dark-500" />
            </Link>
            <Link
              href="/settings"
              className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-dark-800 transition-colors border-b border-gray-200 dark:border-dark-700"
            >
              <div className="flex items-center gap-3">
                <Settings className="w-5 h-5 text-gray-400 dark:text-dark-500" />
                <span className="text-gray-700 dark:text-dark-300">{t("links.settings")}</span>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400 dark:text-dark-500" />
            </Link>
            <Link
              href="/picks"
              className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-dark-800 transition-colors border-b border-gray-200 dark:border-dark-700"
            >
              <div className="flex items-center gap-3">
                <Zap className="w-5 h-5 text-yellow-500" />
                <span className="text-gray-700 dark:text-dark-300">{t("links.dailyPicks")}</span>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400 dark:text-dark-500" />
            </Link>
            <Link
              href="/matches"
              className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-dark-800 transition-colors"
            >
              <div className="flex items-center gap-3">
                <History className="w-5 h-5 text-gray-400 dark:text-dark-500" />
                <span className="text-gray-700 dark:text-dark-300">{t("links.allMatches")}</span>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400 dark:text-dark-500" />
            </Link>
          </div>
        </div>
      </div>

      {/* Gamification Section - Hit & Win */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Streak Tracker */}
        <StreakTracker variant="full" />

        {/* Achievements */}
        <Achievements variant="full" maxDisplay={9} />
      </div>

      {/* Recent Bets Section */}
      {bets.length > 0 && (
        <div className="mt-8">
          <div className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Target className="w-5 h-5 text-primary-500" />
                {t("bets.title")}
              </h3>
              <span className="text-sm text-gray-500 dark:text-dark-400">
                {t("bets.total", { count: bets.length })}
              </span>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-dark-700">
              {bets.slice(0, 5).map((bet) => (
                <div
                  key={bet.id}
                  className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-dark-800 transition-colors"
                >
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {t("bets.match", { id: bet.match_id })}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-dark-400">
                      {bet.prediction === "home_win"
                        ? t("bets.homeWin")
                        : bet.prediction === "away_win"
                        ? t("bets.awayWin")
                        : t("bets.draw")}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="font-medium text-gray-900 dark:text-white">
                        {bet.amount?.toFixed(2) ?? "-"} EUR
                      </div>
                      <div className="text-sm text-gray-500 dark:text-dark-400">
                        {t("bets.odds")} {bet.odds?.toFixed(2) ?? "-"}
                      </div>
                    </div>
                    <span
                      className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium",
                        bet.status === "won"
                          ? "bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300"
                          : bet.status === "lost"
                          ? "bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300"
                          : "bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300"
                      )}
                    >
                      {bet.status === "won" ? t("bets.won") : bet.status === "lost" ? t("bets.lost") : t("bets.pending")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
