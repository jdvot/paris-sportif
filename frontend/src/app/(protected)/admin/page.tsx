"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import {
  Users,
  Crown,
  TrendingUp,
  BarChart3,
  RefreshCw,
  Database,
  Settings,
  FileText,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Shield,
  Search,
  ChevronLeft,
  ChevronRight,
  UserCog,
  Activity,
  Calendar,
  Target,
  Percent,
  Trophy,
  Clock,
  Server,
  Zap,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useGetAdminStatsApiV1AdminStatsGet, useListUsersApiV1AdminUsersGet, useUpdateUserRoleApiV1AdminUsersUserIdRolePost } from "@/lib/api/endpoints/admin/admin";
import { useGetPredictionStats } from "@/lib/api/endpoints/predictions/predictions";
import {
  useSyncWeeklyDataApiV1SyncWeeklyPost,
  useSyncMatchesOnlyApiV1SyncMatchesPost,
  useSyncStandingsOnlyApiV1SyncStandingsPost,
} from "@/lib/api/endpoints/data-sync/data-sync";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  trendUp?: boolean;
  subtitle?: string;
}

function StatCard({ title, value, icon, trend, trendUp, subtitle }: StatCardProps) {
  return (
    <div className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-dark-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {value}
          </p>
          {trend && (
            <p
              className={`text-sm mt-1 ${
                trendUp
                  ? "text-primary-600 dark:text-primary-400"
                  : "text-red-600 dark:text-red-400"
              }`}
            >
              {trendUp ? "+" : ""}
              {trend}
            </p>
          )}
          {subtitle && (
            <p className="text-xs text-gray-400 dark:text-dark-500 mt-1">
              {subtitle}
            </p>
          )}
        </div>
        <div className="p-3 bg-primary-100 dark:bg-primary-500/20 rounded-lg">
          {icon}
        </div>
      </div>
    </div>
  );
}

interface SyncOption {
  id: string;
  label: string;
  description: string;
  checked: boolean;
}

export default function AdminPage() {
  const router = useRouter();
  const { loading, isAuthenticated, isAdmin } = useAuth();
  const [syncResult, setSyncResult] = useState<"success" | "error" | null>(null);
  const [userSearchQuery, setUserSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const usersPerPage = 10;

  const [syncOptions, setSyncOptions] = useState<SyncOption[]>([
    {
      id: "matches",
      label: "Matchs",
      description: "Synchroniser les matchs depuis football-data.org",
      checked: true,
    },
    {
      id: "standings",
      label: "Classements",
      description: "Mettre a jour les classements des ligues",
      checked: true,
    },
    {
      id: "xg",
      label: "xG Data",
      description: "Recuperer les donnees Expected Goals",
      checked: false,
    },
  ]);

  // Fetch admin stats from API
  const { data: statsResponse, isLoading: statsLoading, refetch: refetchStats } =
    useGetAdminStatsApiV1AdminStatsGet({
      query: { enabled: isAuthenticated && isAdmin },
    });

  // Fetch prediction stats
  const { data: predictionStatsResponse, isLoading: predictionStatsLoading } =
    useGetPredictionStats(undefined, {
      query: { enabled: isAuthenticated && isAdmin },
    });

  // Fetch users list
  const { data: usersResponse, isLoading: usersLoading, refetch: refetchUsers } =
    useListUsersApiV1AdminUsersGet(
      { page: currentPage, per_page: usersPerPage },
      { query: { enabled: isAuthenticated && isAdmin } }
    );

  // Update user role mutation
  const updateUserRole = useUpdateUserRoleApiV1AdminUsersUserIdRolePost();

  // Sync mutations
  const weeklySync = useSyncWeeklyDataApiV1SyncWeeklyPost();
  const matchesSync = useSyncMatchesOnlyApiV1SyncMatchesPost();
  const standingsSync = useSyncStandingsOnlyApiV1SyncStandingsPost();

  const isSyncing =
    weeklySync.isPending || matchesSync.isPending || standingsSync.isPending;

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  // Auth check - redirect if not admin
  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Acces refuse
          </h1>
          <p className="text-gray-600 dark:text-dark-400 mb-4">
            Vous n'avez pas les droits pour acceder a cette page.
          </p>
          <button
            onClick={() => router.push("/")}
            className="text-primary-600 dark:text-primary-400 hover:underline"
          >
            Retour a l'accueil
          </button>
        </div>
      </div>
    );
  }

  const handleSyncToggle = (optionId: string) => {
    setSyncOptions((prev) =>
      prev.map((opt) =>
        opt.id === optionId ? { ...opt, checked: !opt.checked } : opt
      )
    );
  };

  const handleSync = async () => {
    const selectedOptions = syncOptions.filter((opt) => opt.checked);
    if (selectedOptions.length === 0) return;

    setSyncResult(null);

    try {
      const hasMatches = selectedOptions.some((o) => o.id === "matches");
      const hasStandings = selectedOptions.some((o) => o.id === "standings");

      if (hasMatches && hasStandings) {
        await weeklySync.mutateAsync({ params: { days: 7, include_standings: true } });
      } else if (hasMatches) {
        await matchesSync.mutateAsync({ params: { days: 7 } });
      } else if (hasStandings) {
        await standingsSync.mutateAsync();
      }

      setSyncResult("success");
      refetchStats();
    } catch (error) {
      setSyncResult("error");
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    setUpdatingUserId(userId);
    try {
      await updateUserRole.mutateAsync({
        userId,
        params: { role: newRole },
      });
      refetchUsers();
    } catch (error) {
      console.error("Failed to update role:", error);
    } finally {
      setUpdatingUserId(null);
    }
  };

  // Get stats from API response
  const apiStats = statsResponse?.status === 200 ? statsResponse.data : null;
  const predictionStats = predictionStatsResponse?.status === 200 ? predictionStatsResponse.data : null;
  const usersData = usersResponse?.status === 200 ? usersResponse.data : null;

  const stats = {
    totalUsers: apiStats?.total_users ?? 0,
    premiumUsers: apiStats?.premium_users ?? 0,
    totalPredictions: apiStats?.total_predictions ?? 0,
    successRate: apiStats?.success_rate ?? 0,
    totalMatches: apiStats?.total_matches ?? 0,
    lastMatchSync: apiStats?.last_match_sync ?? null,
  };

  // Filter users by search query
  const filteredUsers = usersData?.users?.filter(
    (user) =>
      user.email.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
      user.role.toLowerCase().includes(userSearchQuery.toLowerCase())
  ) ?? [];

  const totalPages = Math.ceil((usersData?.total ?? 0) / usersPerPage);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 bg-red-100 dark:bg-red-500/20 rounded-lg">
          <Shield className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
          Administration
        </h1>
      </div>

      {/* Stats Grid - Row 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <StatCard
          title="Utilisateurs totaux"
          value={statsLoading ? "..." : stats.totalUsers.toLocaleString()}
          icon={<Users className="w-6 h-6 text-primary-600 dark:text-primary-400" />}
        />
        <StatCard
          title="Utilisateurs Premium"
          value={statsLoading ? "..." : stats.premiumUsers}
          icon={<Crown className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />}
          subtitle={stats.totalUsers > 0 ? `${((stats.premiumUsers / stats.totalUsers) * 100).toFixed(1)}% du total` : undefined}
        />
        <StatCard
          title="Predictions generees"
          value={statsLoading ? "..." : stats.totalPredictions.toLocaleString()}
          icon={<TrendingUp className="w-6 h-6 text-primary-600 dark:text-primary-400" />}
        />
        <StatCard
          title="Taux de reussite"
          value={statsLoading ? "..." : `${stats.successRate}%`}
          icon={<BarChart3 className="w-6 h-6 text-primary-600 dark:text-primary-400" />}
        />
      </div>

      {/* Stats Grid - Row 2 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Matchs en base"
          value={statsLoading ? "..." : stats.totalMatches.toLocaleString()}
          icon={<Activity className="w-6 h-6 text-blue-600 dark:text-blue-400" />}
        />
        <StatCard
          title="Derniere sync"
          value={stats.lastMatchSync ? format(new Date(stats.lastMatchSync), "dd/MM HH:mm") : "Jamais"}
          icon={<Clock className="w-6 h-6 text-purple-600 dark:text-purple-400" />}
        />
        {predictionStats && (
          <>
            <StatCard
              title="Predictions correctes"
              value={predictionStatsLoading ? "..." : predictionStats.correct_predictions}
              icon={<Target className="w-6 h-6 text-primary-600 dark:text-primary-400" />}
              subtitle={`sur ${predictionStats.total_predictions} predictions`}
            />
            <StatCard
              title="ROI simule"
              value={predictionStatsLoading ? "..." : `${(predictionStats.roi_simulated * 100).toFixed(1)}%`}
              icon={<Trophy className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />}
            />
          </>
        )}
      </div>

      {/* Prediction Performance by Competition */}
      {predictionStats?.by_competition && Object.keys(predictionStats.by_competition).length > 0 && (
        <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-8">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center gap-2">
            <Percent className="w-5 h-5 text-gray-500 dark:text-dark-400" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Performance par competition
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {Object.entries(predictionStats.by_competition).map(([comp, data]) => (
                <div
                  key={comp}
                  className="bg-gray-50 dark:bg-dark-800 rounded-lg p-4 text-center"
                >
                  <p className="text-xs text-gray-500 dark:text-dark-400 mb-1">{comp}</p>
                  <p className={cn(
                    "text-2xl font-bold",
                    (data as { accuracy?: number }).accuracy && (data as { accuracy: number }).accuracy >= 60
                      ? "text-primary-600 dark:text-primary-400"
                      : (data as { accuracy?: number }).accuracy && (data as { accuracy: number }).accuracy >= 50
                      ? "text-yellow-600 dark:text-yellow-400"
                      : "text-red-600 dark:text-red-400"
                  )}>
                    {(data as { accuracy?: number }).accuracy?.toFixed(1) ?? "-"}%
                  </p>
                  <p className="text-xs text-gray-400 dark:text-dark-500 mt-1">
                    {(data as { total?: number }).total ?? 0} predictions
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Data Sync Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center gap-2">
          <Database className="w-5 h-5 text-gray-500 dark:text-dark-400" />
          <h2 className="font-semibold text-gray-900 dark:text-white">
            Synchronisation des donnees
          </h2>
        </div>
        <div className="p-6">
          <div className="space-y-4 mb-6">
            {syncOptions.map((option) => (
              <label
                key={option.id}
                className="flex items-start gap-3 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={option.checked}
                  onChange={() => handleSyncToggle(option.id)}
                  className="mt-1 w-4 h-4 rounded border-gray-300 dark:border-dark-600 text-primary-500 focus:ring-primary-500"
                />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {option.label}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-dark-400">
                    {option.description}
                  </p>
                </div>
              </label>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={handleSync}
              disabled={
                isSyncing || syncOptions.filter((o) => o.checked).length === 0
              }
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
            >
              {isSyncing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {isSyncing ? "Synchronisation..." : "Lancer la synchronisation"}
            </button>

            {syncResult === "success" && (
              <span className="inline-flex items-center gap-1.5 text-sm text-primary-600 dark:text-primary-400">
                <CheckCircle className="w-4 h-4" />
                Synchronisation reussie
              </span>
            )}

            {syncResult === "error" && (
              <span className="inline-flex items-center gap-1.5 text-sm text-red-600 dark:text-red-400">
                <AlertTriangle className="w-4 h-4" />
                Erreur de synchronisation
              </span>
            )}
          </div>
        </div>
      </section>

      {/* User Management Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <UserCog className="w-5 h-5 text-gray-500 dark:text-dark-400" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Gestion des utilisateurs
            </h2>
          </div>
          <span className="text-sm text-gray-500 dark:text-dark-400">
            {usersData?.total ?? 0} utilisateurs
          </span>
        </div>

        {/* Search */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher par email ou role..."
              value={userSearchQuery}
              onChange={(e) => setUserSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-dark-800 border border-gray-200 dark:border-dark-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        {/* Users Table */}
        <div className="overflow-x-auto">
          {usersLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-12">
              <Users className="w-12 h-12 text-gray-300 dark:text-dark-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-dark-400">
                Aucun utilisateur trouve
              </p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 dark:bg-dark-800">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-400 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-400 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-400 uppercase tracking-wider">
                    Date d'inscription
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-dark-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-dark-700">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-dark-800 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-500/20 flex items-center justify-center text-primary-600 dark:text-primary-400 font-medium text-sm">
                          {user.email.charAt(0).toUpperCase()}
                        </div>
                        <span className="text-gray-900 dark:text-white text-sm">
                          {user.email}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium",
                          user.role === "admin"
                            ? "bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300"
                            : user.role === "premium"
                            ? "bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300"
                            : "bg-gray-100 dark:bg-dark-700 text-gray-700 dark:text-dark-300"
                        )}
                      >
                        {user.role === "admin" && <Shield className="w-3 h-3" />}
                        {user.role === "premium" && <Crown className="w-3 h-3" />}
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-dark-400">
                      {format(new Date(user.created_at), "dd MMM yyyy", { locale: fr })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.id, e.target.value)}
                        disabled={updatingUserId === user.id}
                        className="text-sm bg-gray-50 dark:bg-dark-800 border border-gray-200 dark:border-dark-700 rounded-lg px-3 py-1.5 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                      >
                        <option value="free">Gratuit</option>
                        <option value="premium">Premium</option>
                        <option value="admin">Admin</option>
                      </select>
                      {updatingUserId === user.id && (
                        <Loader2 className="w-4 h-4 animate-spin inline-block ml-2 text-primary-500" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 dark:border-dark-700 flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-dark-400">
              Page {currentPage} sur {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-lg border border-gray-200 dark:border-dark-700 hover:bg-gray-50 dark:hover:bg-dark-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-dark-400" />
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-2 rounded-lg border border-gray-200 dark:border-dark-700 hover:bg-gray-50 dark:hover:bg-dark-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4 text-gray-600 dark:text-dark-400" />
              </button>
            </div>
          </div>
        )}
      </section>

      {/* System Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Quick Actions */}
        <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-500" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Actions rapides
            </h2>
          </div>
          <div className="p-6 space-y-3">
            <button
              onClick={() => router.push("/picks")}
              className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-800 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-700 transition-colors"
            >
              <span className="text-gray-700 dark:text-dark-300">Voir les picks du jour</span>
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
            <button
              onClick={() => router.push("/matches")}
              className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-800 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-700 transition-colors"
            >
              <span className="text-gray-700 dark:text-dark-300">Gerer les matchs</span>
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
            <button
              onClick={() => router.push("/standings")}
              className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-800 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-700 transition-colors"
            >
              <span className="text-gray-700 dark:text-dark-300">Voir les classements</span>
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </section>

        {/* System Status */}
        <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center gap-2">
            <Server className="w-5 h-5 text-gray-500 dark:text-dark-400" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Statut systeme
            </h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-dark-400">API Backend</span>
              <span className="inline-flex items-center gap-1.5 text-sm text-primary-600 dark:text-primary-400">
                <span className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
                En ligne
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-dark-400">Base de donnees</span>
              <span className="inline-flex items-center gap-1.5 text-sm text-primary-600 dark:text-primary-400">
                <span className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
                Connectee
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-dark-400">Cache Redis</span>
              <span className="inline-flex items-center gap-1.5 text-sm text-primary-600 dark:text-primary-400">
                <span className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
                Actif
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-dark-400">ML Models</span>
              <span className="inline-flex items-center gap-1.5 text-sm text-primary-600 dark:text-primary-400">
                <span className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
                Charges
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
