"use client";

import { useState, useEffect } from "react";
import {
  Settings,
  Bell,
  Globe,
  Palette,
  Trophy,
  Save,
  Check,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import {
  useGetPreferencesApiV1UserPreferencesGet,
  useUpdatePreferencesApiV1UserPreferencesPut,
} from "@/lib/api/endpoints/user-data/user-data";

interface PreferenceToggleProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function PreferenceToggle({
  label,
  description,
  checked,
  onChange,
}: PreferenceToggleProps) {
  return (
    <div className="flex items-center justify-between py-3">
      <div>
        <p className="font-medium text-gray-900 dark:text-white">{label}</p>
        {description && (
          <p className="text-sm text-gray-600 dark:text-dark-400">
            {description}
          </p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
          checked ? "bg-primary-500" : "bg-gray-200 dark:bg-dark-600"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}

const COMPETITIONS = [
  { code: "PL", name: "Premier League", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
  { code: "PD", name: "La Liga", flag: "🇪🇸" },
  { code: "BL1", name: "Bundesliga", flag: "🇩🇪" },
  { code: "SA", name: "Serie A", flag: "🇮🇹" },
  { code: "FL1", name: "Ligue 1", flag: "🇫🇷" },
  { code: "CL", name: "Champions League", flag: "🇪🇺" },
];

export default function PreferencesPage() {
  const t = useTranslations("preferences");
  const locale = useLocale();
  const router = useRouter();

  // API hooks
  const { data: prefsResponse, isLoading } =
    useGetPreferencesApiV1UserPreferencesGet();
  const updateMutation = useUpdatePreferencesApiV1UserPreferencesPut();

  // Local state for form - matching API model
  const [emailDailyPicks, setEmailDailyPicks] = useState(true);
  const [emailMatchResults, setEmailMatchResults] = useState(true);
  const [pushDailyPicks, setPushDailyPicks] = useState(true);
  const [pushMatchStart, setPushMatchStart] = useState(true);
  const [pushBetResults, setPushBetResults] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [competitions, setCompetitions] = useState<string[]>([
    "PL", "PD", "BL1", "SA", "FL1", "CL",
  ]);
  const [hasChanges, setHasChanges] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">("idle");

  // Load preferences from API
  useEffect(() => {
    if (prefsResponse?.status === 200 && prefsResponse.data) {
      const prefs = prefsResponse.data;
      setEmailDailyPicks(prefs.email_daily_picks);
      setEmailMatchResults(prefs.email_match_results);
      setPushDailyPicks(prefs.push_daily_picks);
      setPushMatchStart(prefs.push_match_start);
      setPushBetResults(prefs.push_bet_results);
      setDarkMode(prefs.dark_mode);
      setCompetitions(prefs.favorite_competitions);
    }
  }, [prefsResponse]);

  const toggleCompetition = (code: string) => {
    setCompetitions((prev) => {
      if (prev.includes(code)) {
        if (prev.length === 1) return prev;
        return prev.filter((c) => c !== code);
      }
      return [...prev, code];
    });
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      await updateMutation.mutateAsync({
        data: {
          email_daily_picks: emailDailyPicks,
          email_match_results: emailMatchResults,
          push_daily_picks: pushDailyPicks,
          push_match_start: pushMatchStart,
          push_bet_results: pushBetResults,
          dark_mode: darkMode,
          favorite_competitions: competitions,
        },
      });
      setSaveStatus("success");
      setHasChanges(false);
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Settings className="w-8 h-8 text-primary-500" />
            {t("title")}
          </h1>
          <p className="text-gray-600 dark:text-dark-400 mt-1">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-3">
          {saveStatus === "success" && (
            <span className="inline-flex items-center gap-1.5 text-sm text-green-600 dark:text-green-400">
              <CheckCircle className="w-4 h-4" />
              {locale === "fr" ? "Enregistre" : "Saved"}
            </span>
          )}
          {saveStatus === "error" && (
            <span className="inline-flex items-center gap-1.5 text-sm text-red-600 dark:text-red-400">
              <XCircle className="w-4 h-4" />
              {locale === "fr" ? "Erreur" : "Error"}
            </span>
          )}
          {hasChanges && (
            <button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 transition-colors"
            >
              {updateMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {t("save")}
            </button>
          )}
        </div>
      </div>

      {/* Notifications Section */}
      <section className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Bell className="w-5 h-5 text-primary-500" />
          {t("notifications.title")}
        </h2>
        <div className="divide-y divide-gray-100 dark:divide-dark-700">
          <PreferenceToggle
            label={t("notifications.dailyPicks")}
            description={t("notifications.dailyPicksDesc")}
            checked={emailDailyPicks}
            onChange={(v) => {
              setEmailDailyPicks(v);
              setHasChanges(true);
            }}
          />
          <PreferenceToggle
            label={t("notifications.matchAlerts")}
            description={t("notifications.matchAlertsDesc")}
            checked={pushMatchStart}
            onChange={(v) => {
              setPushMatchStart(v);
              setHasChanges(true);
            }}
          />
          <PreferenceToggle
            label={t("notifications.resultUpdates")}
            description={t("notifications.resultUpdatesDesc")}
            checked={emailMatchResults}
            onChange={(v) => {
              setEmailMatchResults(v);
              setHasChanges(true);
            }}
          />
          <PreferenceToggle
            label={t("notifications.promotions")}
            description={t("notifications.promotionsDesc")}
            checked={pushBetResults}
            onChange={(v) => {
              setPushBetResults(v);
              setHasChanges(true);
            }}
          />
        </div>
      </section>

      {/* Display Section */}
      <section className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Palette className="w-5 h-5 text-primary-500" />
          {t("display.title")}
        </h2>
        <div className="divide-y divide-gray-100 dark:divide-dark-700">
          <PreferenceToggle
            label={locale === "fr" ? "Mode sombre" : "Dark mode"}
            description={locale === "fr" ? "Activer le theme sombre" : "Enable dark theme"}
            checked={darkMode}
            onChange={(v) => {
              setDarkMode(v);
              setHasChanges(true);
            }}
          />
        </div>
      </section>

      {/* Competitions Section */}
      <section className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Trophy className="w-5 h-5 text-primary-500" />
          {t("competitions.title")}
        </h2>
        <p className="text-sm text-gray-600 dark:text-dark-400 mb-4">
          {t("competitions.description")}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {COMPETITIONS.map((comp) => {
            const selected = competitions.includes(comp.code);
            return (
              <button
                key={comp.code}
                onClick={() => toggleCompetition(comp.code)}
                className={`flex items-center gap-2 p-3 rounded-lg border transition-colors ${
                  selected
                    ? "bg-primary-50 dark:bg-primary-500/10 border-primary-300 dark:border-primary-500/50"
                    : "bg-gray-50 dark:bg-dark-700 border-gray-200 dark:border-dark-600 hover:border-gray-300 dark:hover:border-dark-500"
                }`}
              >
                <span className="text-lg">{comp.flag}</span>
                <span
                  className={`text-sm font-medium ${
                    selected
                      ? "text-primary-700 dark:text-primary-300"
                      : "text-gray-700 dark:text-dark-300"
                  }`}
                >
                  {comp.name}
                </span>
                {selected && (
                  <Check className="w-4 h-4 text-primary-500 ml-auto" />
                )}
              </button>
            );
          })}
        </div>
      </section>

      {/* Language Section */}
      <section className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Globe className="w-5 h-5 text-primary-500" />
          {t("language.title")}
        </h2>
        <p className="text-sm text-gray-600 dark:text-dark-400 mb-4">
          {t("language.description")}
        </p>
        <div className="flex gap-3">
          {[
            { code: "fr", name: "Francais", flag: "🇫🇷" },
            { code: "en", name: "English", flag: "🇬🇧" },
            { code: "nl", name: "Nederlands", flag: "🇳🇱" },
          ].map((lang) => (
            <button
              key={lang.code}
              onClick={() => router.push(`/${lang.code}/profile/preferences`)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                locale === lang.code
                  ? "bg-primary-50 dark:bg-primary-500/10 border-primary-300 dark:border-primary-500/50"
                  : "bg-gray-50 dark:bg-dark-700 border-gray-200 dark:border-dark-600 hover:border-gray-300 dark:hover:border-dark-500"
              }`}
            >
              <span>{lang.flag}</span>
              <span
                className={`text-sm font-medium ${
                  locale === lang.code
                    ? "text-primary-700 dark:text-primary-300"
                    : "text-gray-700 dark:text-dark-300"
                }`}
              >
                {lang.name}
              </span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
