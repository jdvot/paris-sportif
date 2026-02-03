"use client";

import { useState, useEffect } from "react";
import { X, Download, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useInstallPrompt } from "@/hooks/useServiceWorker";

export function PWAInstallPrompt() {
  const { isInstallable, isInstalled, promptInstall, dismissPrompt } = useInstallPrompt();
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    // Check if user dismissed the prompt recently
    const dismissed = localStorage.getItem("pwa-install-dismissed");
    if (dismissed) {
      const dismissedTime = parseInt(dismissed, 10);
      const sevenDays = 7 * 24 * 60 * 60 * 1000;
      if (Date.now() - dismissedTime < sevenDays) {
        return;
      }
    }

    // Show prompt after a delay if installable
    if (isInstallable && !isInstalled) {
      const timer = setTimeout(() => setShowPrompt(true), 3000);
      return () => clearTimeout(timer);
    }
  }, [isInstallable, isInstalled]);

  const handleInstall = async () => {
    const installed = await promptInstall();
    if (installed) {
      setShowPrompt(false);
    }
  };

  const handleDismiss = () => {
    dismissPrompt();
    setShowPrompt(false);
  };

  if (!showPrompt || isInstalled) return null;

  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 animate-in slide-in-from-bottom-4 md:bottom-6 md:left-auto md:right-6 md:w-96">
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 shadow-xl">
        <button
          onClick={handleDismiss}
          className="absolute right-2 top-2 rounded-full p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          aria-label="Fermer"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-600">
            <Smartphone className="h-6 w-6 text-white" />
          </div>

          <div className="flex-1">
            <h3 className="font-semibold text-white">
              Installer WinRate AI
            </h3>
            <p className="mt-1 text-sm text-slate-400">
              Acces rapide depuis votre ecran d&apos;accueil. Fonctionne hors ligne.
            </p>

            <div className="mt-3 flex gap-2">
              <Button
                onClick={handleInstall}
                size="sm"
                className="gap-1.5"
              >
                <Download className="h-4 w-4" />
                Installer
              </Button>
              <Button
                onClick={handleDismiss}
                variant="ghost"
                size="sm"
                className="text-slate-400 hover:text-white"
              >
                Plus tard
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function PWAUpdatePrompt() {
  const [showUpdate, setShowUpdate] = useState(false);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    const checkForUpdates = async () => {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration?.waiting) {
        setShowUpdate(true);
      }
    };

    // Listen for new service worker
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      window.location.reload();
    });

    checkForUpdates();
  }, []);

  const handleUpdate = async () => {
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: "SKIP_WAITING" });
    }
  };

  if (!showUpdate) return null;

  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 md:bottom-6 md:left-auto md:right-6 md:w-96">
      <div className="rounded-lg border border-blue-500/50 bg-blue-950/90 p-4 shadow-xl backdrop-blur">
        <div className="flex items-center justify-between">
          <p className="text-sm text-blue-100">
            Nouvelle version disponible
          </p>
          <Button
            onClick={handleUpdate}
            size="sm"
            variant="secondary"
          >
            Mettre a jour
          </Button>
        </div>
      </div>
    </div>
  );
}

export function OfflineIndicator() {
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    setIsOffline(!navigator.onLine);

    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!isOffline) return null;

  return (
    <div className="fixed left-0 right-0 top-0 z-50 bg-amber-600 px-4 py-2 text-center text-sm font-medium text-white">
      Vous etes hors ligne. Certaines fonctionnalites peuvent etre limitees.
    </div>
  );
}
