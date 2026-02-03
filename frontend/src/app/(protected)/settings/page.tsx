"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import {
  Sun,
  Moon,
  Bell,
  BellOff,
  Globe,
  Lock,
  Trash2,
  Loader2,
  AlertTriangle,
  ChevronRight,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface ToggleSwitchProps {
  enabled: boolean;
  onToggle: () => void;
  disabled?: boolean;
  label: string;
}

function ToggleSwitch({ enabled, onToggle, disabled = false, label }: ToggleSwitchProps) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      role="switch"
      aria-checked={enabled}
      aria-label={label}
      className={`
        relative inline-flex h-6 w-11 items-center rounded-full transition-colors
        ${enabled ? "bg-primary-500" : "bg-gray-300 dark:bg-dark-600"}
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
      `}
    >
      <span
        className={`
          inline-block h-4 w-4 transform rounded-full bg-white transition-transform
          ${enabled ? "translate-x-6" : "translate-x-1"}
        `}
      />
    </button>
  );
}

export default function SettingsPage() {
  const t = useTranslations("settings");
  const tCommon = useTranslations("common");
  const { user, loading, isAuthenticated, resetPassword, deleteAccount } = useAuth();
  const { theme, setTheme } = useTheme();
  const router = useRouter();

  // Notification preferences (stored in localStorage for now)
  const [notifications, setNotifications] = useState({
    dailyPicks: true,
    alerts: true,
    promos: false,
  });

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isResettingPassword, setIsResettingPassword] = useState(false);
  const [resetPasswordSent, setResetPasswordSent] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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

  const isDarkMode = theme === "dark";

  const handleThemeToggle = () => {
    setTheme(isDarkMode ? "light" : "dark");
  };

  const handleNotificationToggle = (key: keyof typeof notifications) => {
    setNotifications((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleResetPassword = async () => {
    if (!user.email) return;
    setIsResettingPassword(true);
    await resetPassword(user.email);
    setIsResettingPassword(false);
    setResetPasswordSent(true);
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    setDeleteError(null);

    const { error } = await deleteAccount();

    if (error) {
      setIsDeleting(false);
      setDeleteError(tCommon("errorDelete"));
      return;
    }

    // Redirect to home after successful deletion
    router.push("/");
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-8">
        {t("title")}
      </h1>

      {/* Appearance Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            {t("appearance.title")}
          </h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isDarkMode ? (
                <Moon className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              ) : (
                <Sun className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              )}
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {t("appearance.darkMode")}
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {isDarkMode ? t("appearance.enabled") : t("appearance.disabled")}
                </p>
              </div>
            </div>
            <ToggleSwitch enabled={isDarkMode} onToggle={handleThemeToggle} label={t("appearance.toggleDarkMode")} />
          </div>
        </div>
      </section>

      {/* Notifications Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            {t("notifications.title")}
          </h2>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-dark-700">
          <div className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {t("notifications.dailyPicks")}
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {t("notifications.dailyPicksDesc")}
                </p>
              </div>
            </div>
            <ToggleSwitch
              enabled={notifications.dailyPicks}
              onToggle={() => handleNotificationToggle("dailyPicks")}
              label={t("notifications.toggleDailyPicks")}
            />
          </div>

          <div className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              <BellOff className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {t("notifications.alerts")}
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {t("notifications.alertsDesc")}
                </p>
              </div>
            </div>
            <ToggleSwitch
              enabled={notifications.alerts}
              onToggle={() => handleNotificationToggle("alerts")}
              label={t("notifications.toggleAlerts")}
            />
          </div>

          <div className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {t("notifications.promos")}
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {t("notifications.promosDesc")}
                </p>
              </div>
            </div>
            <ToggleSwitch
              enabled={notifications.promos}
              onToggle={() => handleNotificationToggle("promos")}
              label={t("notifications.togglePromos")}
            />
          </div>
        </div>
      </section>

      {/* Language Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">{t("language.title")}</h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between opacity-50">
            <div className="flex items-center gap-3">
              <Globe className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {t("language.french")}
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {t("language.comingSoon")}
                </p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            {t("security.title")}
          </h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Lock className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {t("security.password")}
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {t("security.passwordDesc")}
                </p>
              </div>
            </div>
            {resetPasswordSent ? (
              <span className="text-sm text-primary-600 dark:text-primary-400">
                {t("security.emailSent")}
              </span>
            ) : (
              <button
                onClick={handleResetPassword}
                disabled={isResettingPassword}
                className="px-4 py-2 text-sm font-medium text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-500/10 rounded-lg transition-colors"
              >
                {isResettingPassword ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  t("security.reset")
                )}
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="bg-white dark:bg-dark-900 border border-red-200 dark:border-red-500/30 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10">
          <h2 className="font-semibold text-red-700 dark:text-red-400">
            {t("dangerZone.title")}
          </h2>
        </div>
        <div className="p-6">
          {showDeleteConfirm ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-700 dark:text-red-400">
                    {t("dangerZone.areYouSure")}
                  </p>
                  <p className="text-sm text-red-600 dark:text-red-300 mt-1">
                    {t("dangerZone.warningMessage")}
                  </p>
                </div>
              </div>
              {deleteError && (
                <p className="text-sm text-red-600 dark:text-red-400">{deleteError}</p>
              )}
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={isDeleting}
                  className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-dark-300 bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600 rounded-lg transition-colors disabled:opacity-50"
                >
                  {t("dangerZone.cancel")}
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={isDeleting}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t("dangerZone.deleting")}
                    </>
                  ) : (
                    t("dangerZone.deletePermanently")
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Trash2 className="w-5 h-5 text-red-500" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {t("dangerZone.deleteAccount")}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-dark-400">
                    {t("dangerZone.deleteAccountDesc")}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
              >
                {t("dangerZone.delete")}
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
