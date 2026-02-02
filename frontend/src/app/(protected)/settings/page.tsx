"use client";

import { useState } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
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
}

function ToggleSwitch({ enabled, onToggle, disabled = false }: ToggleSwitchProps) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
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
  const { user, loading, isAuthenticated, resetPassword } = useAuth();
  const { theme, setTheme } = useTheme();

  // Notification preferences (stored in localStorage for now)
  const [notifications, setNotifications] = useState({
    dailyPicks: true,
    alerts: true,
    promos: false,
  });

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isResettingPassword, setIsResettingPassword] = useState(false);
  const [resetPasswordSent, setResetPasswordSent] = useState(false);

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

  const handleDeleteAccount = () => {
    // TODO: Implement account deletion
    console.log("Delete account requested");
    setShowDeleteConfirm(false);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-8">
        Parametres
      </h1>

      {/* Appearance Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            Apparence
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
                  Mode sombre
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {isDarkMode ? "Active" : "Desactive"}
                </p>
              </div>
            </div>
            <ToggleSwitch enabled={isDarkMode} onToggle={handleThemeToggle} />
          </div>
        </div>
      </section>

      {/* Notifications Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            Notifications
          </h2>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-dark-700">
          <div className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  Picks quotidiens
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  Recevoir les nouveaux picks chaque jour
                </p>
              </div>
            </div>
            <ToggleSwitch
              enabled={notifications.dailyPicks}
              onToggle={() => handleNotificationToggle("dailyPicks")}
            />
          </div>

          <div className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              <BellOff className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  Alertes importantes
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  Mises a jour de securite et compte
                </p>
              </div>
            </div>
            <ToggleSwitch
              enabled={notifications.alerts}
              onToggle={() => handleNotificationToggle("alerts")}
            />
          </div>

          <div className="flex items-center justify-between p-6">
            <div className="flex items-center gap-3">
              <Bell className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  Offres promotionnelles
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  Recevoir les offres speciales
                </p>
              </div>
            </div>
            <ToggleSwitch
              enabled={notifications.promos}
              onToggle={() => handleNotificationToggle("promos")}
            />
          </div>
        </div>
      </section>

      {/* Language Section */}
      <section className="bg-white dark:bg-dark-900 border border-gray-200 dark:border-dark-700 rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">Langue</h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between opacity-50">
            <div className="flex items-center gap-3">
              <Globe className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  Francais
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  Bientot disponible
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
            Securite
          </h2>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Lock className="w-5 h-5 text-gray-500 dark:text-dark-400" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  Mot de passe
                </p>
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  Reinitialiser votre mot de passe
                </p>
              </div>
            </div>
            {resetPasswordSent ? (
              <span className="text-sm text-primary-600 dark:text-primary-400">
                Email envoye!
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
                  "Reinitialiser"
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
            Zone de danger
          </h2>
        </div>
        <div className="p-6">
          {showDeleteConfirm ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-700 dark:text-red-400">
                    Etes-vous sur?
                  </p>
                  <p className="text-sm text-red-600 dark:text-red-300 mt-1">
                    Cette action est irreversible. Toutes vos donnees seront
                    supprimees.
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-dark-300 bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600 rounded-lg transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleDeleteAccount}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
                >
                  Supprimer definitivement
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Trash2 className="w-5 h-5 text-red-500" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    Supprimer mon compte
                  </p>
                  <p className="text-sm text-gray-500 dark:text-dark-400">
                    Supprimer definitivement votre compte et vos donnees
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
              >
                Supprimer
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
