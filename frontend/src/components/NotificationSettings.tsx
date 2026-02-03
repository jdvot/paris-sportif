"use client";

import { Bell, BellOff, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { usePushNotifications } from "@/hooks/useServiceWorker";

export function NotificationSettings() {
  const t = useTranslations("notifications");
  const {
    isSupported,
    permission,
    isSubscribed,
    isLoading,
    error,
    subscribe,
    unsubscribe,
  } = usePushNotifications();

  if (!isSupported) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <BellOff className="h-4 w-4" />
        <span>{t("notSupported")}</span>
      </div>
    );
  }

  if (permission === "denied") {
    return (
      <div className="flex items-center gap-2 text-sm text-red-500">
        <BellOff className="h-4 w-4" />
        <span>{t("blocked")}</span>
      </div>
    );
  }

  const handleToggle = async () => {
    if (isSubscribed) {
      await unsubscribe();
    } else {
      await subscribe();
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isSubscribed ? (
            <Bell className="h-4 w-4 text-green-500" />
          ) : (
            <BellOff className="h-4 w-4 text-slate-400" />
          )}
          <span className="text-sm">
            {isSubscribed ? t("enabled") : t("disabled")}
          </span>
        </div>
        <Button
          variant={isSubscribed ? "outline" : "default"}
          size="sm"
          onClick={handleToggle}
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isSubscribed ? (
            t("disable")
          ) : (
            t("enable")
          )}
        </Button>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

export function NotificationBanner() {
  const t = useTranslations("notifications");
  const { isSupported, permission, isSubscribed, isLoading, subscribe } =
    usePushNotifications();

  // Don't show if not supported, already subscribed, or permission denied
  if (!isSupported || isSubscribed || permission === "denied") {
    return null;
  }

  // Check if user dismissed the banner recently
  if (typeof window !== "undefined") {
    const dismissed = localStorage.getItem("notification-banner-dismissed");
    if (dismissed) {
      const dismissedAt = parseInt(dismissed, 10);
      const daysSince = (Date.now() - dismissedAt) / (1000 * 60 * 60 * 24);
      if (daysSince < 7) return null;
    }
  }

  const handleDismiss = () => {
    localStorage.setItem("notification-banner-dismissed", Date.now().toString());
  };

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-md rounded-lg border border-slate-700 bg-slate-900 p-4 shadow-lg md:left-auto md:right-4">
      <div className="flex items-start gap-3">
        <Bell className="mt-0.5 h-5 w-5 text-blue-500" />
        <div className="flex-1">
          <p className="text-sm font-medium text-white">{t("bannerTitle")}</p>
          <p className="mt-1 text-xs text-slate-400">{t("bannerDescription")}</p>
          <div className="mt-3 flex gap-2">
            <Button size="sm" onClick={subscribe} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                t("enable")
              )}
            </Button>
            <Button size="sm" variant="ghost" onClick={handleDismiss}>
              {t("later")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
