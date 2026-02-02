"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useGetAdminStatsApiV1AdminStatsGet } from "@/lib/api/endpoints/admin/admin";
import {
  useSyncWeeklyDataApiV1SyncWeeklyPost,
  useSyncMatchesOnlyApiV1SyncMatchesPost,
  useSyncStandingsOnlyApiV1SyncStandingsPost,
} from "@/lib/api/endpoints/data-sync/data-sync";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  trendUp?: boolean;
}

function StatCard({ title, value, icon, trend, trendUp }: StatCardProps) {
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
  const [syncResult, setSyncResult] = useState<"success" | "error" | null>(
    null
  );

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
  const { data: statsResponse, isLoading: statsLoading } =
    useGetAdminStatsApiV1AdminStatsGet({
      query: { enabled: isAuthenticated && isAdmin },
    });

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
        // Sync both via weekly endpoint
        await weeklySync.mutateAsync({ params: { days: 7, include_standings: true } });
      } else if (hasMatches) {
        await matchesSync.mutateAsync({ params: { days: 7 } });
      } else if (hasStandings) {
        await standingsSync.mutateAsync();
      }

      setSyncResult("success");
    } catch (error) {
      setSyncResult("error");
    }
  };

  // Get stats from API response
  const apiStats = statsResponse?.status === 200 ? statsResponse.data : null;
  const stats = {
    totalUsers: apiStats?.total_users ?? 0,
    premiumUsers: apiStats?.premium_users ?? 0,
    totalPredictions: apiStats?.total_predictions ?? 0,
    successRate: apiStats?.success_rate ?? 0,
    totalMatches: apiStats?.total_matches ?? 0,
    lastMatchSync: apiStats?.last_match_sync ?? null,
  };

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

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Utilisateurs totaux"
          value={stats.totalUsers.toLocaleString()}
          icon={<Users className="w-6 h-6 text-primary-600 dark:text-primary-400" />}
          trend="12% ce mois"
          trendUp={true}
        />
        <StatCard
          title="Utilisateurs Premium"
          value={stats.premiumUsers}
          icon={<Crown className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />}
          trend="5 nouveaux"
          trendUp={true}
        />
        <StatCard
          title="Predictions generees"
          value={stats.totalPredictions.toLocaleString()}
          icon={
            <TrendingUp className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          }
        />
        <StatCard
          title="Taux de reussite"
          value={`${stats.successRate}%`}
          icon={
            <BarChart3 className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          }
          trend="2.1%"
          trendUp={true}
        />
      </div>

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

      {/* Placeholders for future features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* User Management */}
        <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center gap-2">
            <Users className="w-5 h-5 text-gray-500 dark:text-dark-400" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Gestion des utilisateurs
            </h2>
          </div>
          <div className="p-6">
            <div className="text-center py-8">
              <Settings className="w-12 h-12 text-gray-300 dark:text-dark-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-dark-400">
                Bientot disponible
              </p>
              <p className="text-sm text-gray-400 dark:text-dark-500 mt-1">
                Gestion des roles et permissions
              </p>
            </div>
          </div>
        </section>

        {/* System Logs */}
        <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700 flex items-center gap-2">
            <FileText className="w-5 h-5 text-gray-500 dark:text-dark-400" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Logs systeme
            </h2>
          </div>
          <div className="p-6">
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-300 dark:text-dark-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-dark-400">
                Bientot disponible
              </p>
              <p className="text-sm text-gray-400 dark:text-dark-500 mt-1">
                Consultation des logs et erreurs
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
