"use client";

import { useEffect, useState } from "react";

interface ServiceWorkerState {
  isSupported: boolean;
  isRegistered: boolean;
  isOffline: boolean;
  registration: ServiceWorkerRegistration | null;
  updateAvailable: boolean;
}

export function useServiceWorker(): ServiceWorkerState {
  const [state, setState] = useState<ServiceWorkerState>({
    isSupported: false,
    isRegistered: false,
    isOffline: false,
    registration: null,
    updateAvailable: false,
  });

  useEffect(() => {
    // Check if service workers are supported
    const isSupported = "serviceWorker" in navigator;
    setState((prev) => ({ ...prev, isSupported }));

    if (!isSupported) return;

    // Track online/offline status
    const handleOnline = () => setState((prev) => ({ ...prev, isOffline: false }));
    const handleOffline = () => setState((prev) => ({ ...prev, isOffline: true }));

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Set initial offline state
    setState((prev) => ({ ...prev, isOffline: !navigator.onLine }));

    // Register service worker
    const registerSW = async () => {
      try {
        const registration = await navigator.serviceWorker.register("/sw.js", {
          scope: "/",
        });

        setState((prev) => ({
          ...prev,
          isRegistered: true,
          registration,
        }));

        // Check for updates
        registration.addEventListener("updatefound", () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener("statechange", () => {
              if (
                newWorker.state === "installed" &&
                navigator.serviceWorker.controller
              ) {
                setState((prev) => ({ ...prev, updateAvailable: true }));
              }
            });
          }
        });

        // Check for updates periodically (every hour)
        setInterval(() => {
          registration.update();
        }, 60 * 60 * 1000);

        console.log("[PWA] Service worker registered");
      } catch (error) {
        console.error("[PWA] Service worker registration failed:", error);
      }
    };

    registerSW();

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return state;
}

export function useInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstallable, setIsInstallable] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    // Check if already installed
    const checkInstalled = () => {
      if (window.matchMedia("(display-mode: standalone)").matches) {
        setIsInstalled(true);
        return true;
      }
      // iOS standalone check
      if ((navigator as Navigator & { standalone?: boolean }).standalone) {
        setIsInstalled(true);
        return true;
      }
      return false;
    };

    if (checkInstalled()) return;

    // Listen for install prompt
    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setIsInstallable(true);
    };

    // Listen for successful install
    const handleAppInstalled = () => {
      setIsInstalled(true);
      setIsInstallable(false);
      setDeferredPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  const promptInstall = async (): Promise<boolean> => {
    if (!deferredPrompt) return false;

    try {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;

      if (outcome === "accepted") {
        setIsInstalled(true);
        setIsInstallable(false);
      }

      setDeferredPrompt(null);
      return outcome === "accepted";
    } catch (error) {
      console.error("[PWA] Install prompt failed:", error);
      return false;
    }
  };

  const dismissPrompt = () => {
    setIsInstallable(false);
    // Store dismissal in localStorage to not show again for 7 days
    localStorage.setItem("pwa-install-dismissed", Date.now().toString());
  };

  return {
    isInstallable,
    isInstalled,
    promptInstall,
    dismissPrompt,
  };
}

// Type for beforeinstallprompt event
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

// VAPID public key from environment
const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || "";

interface PushNotificationState {
  isSupported: boolean;
  permission: NotificationPermission | "unsupported";
  isSubscribed: boolean;
  isLoading: boolean;
  error: string | null;
}

export function usePushNotifications() {
  const [state, setState] = useState<PushNotificationState>({
    isSupported: false,
    permission: "unsupported",
    isSubscribed: false,
    isLoading: false,
    error: null,
  });
  const { registration } = useServiceWorker();

  useEffect(() => {
    // Check if push notifications are supported
    const isSupported =
      "Notification" in window &&
      "PushManager" in window &&
      "serviceWorker" in navigator;

    if (!isSupported) {
      setState((prev) => ({ ...prev, isSupported: false }));
      return;
    }

    setState((prev) => ({
      ...prev,
      isSupported: true,
      permission: Notification.permission,
    }));

    // Check if already subscribed
    const checkSubscription = async () => {
      if (!registration) return;

      try {
        const subscription = await registration.pushManager.getSubscription();
        setState((prev) => ({
          ...prev,
          isSubscribed: subscription !== null,
        }));
      } catch (error) {
        console.error("[Push] Error checking subscription:", error);
      }
    };

    checkSubscription();
  }, [registration]);

  const subscribe = async (): Promise<boolean> => {
    if (!registration || !VAPID_PUBLIC_KEY) {
      setState((prev) => ({
        ...prev,
        error: "Push notifications not configured",
      }));
      return false;
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Request permission if not granted
      if (Notification.permission === "default") {
        const permission = await Notification.requestPermission();
        setState((prev) => ({ ...prev, permission }));

        if (permission !== "granted") {
          setState((prev) => ({
            ...prev,
            isLoading: false,
            error: "Permission denied",
          }));
          return false;
        }
      }

      if (Notification.permission === "denied") {
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: "Notifications blocked",
        }));
        return false;
      }

      // Subscribe to push
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      });

      // Send subscription to backend
      const response = await fetch("/api/v1/notifications/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(subscription.toJSON()),
      });

      if (!response.ok) {
        throw new Error("Failed to save subscription");
      }

      setState((prev) => ({
        ...prev,
        isSubscribed: true,
        isLoading: false,
      }));

      return true;
    } catch (error) {
      console.error("[Push] Subscription failed:", error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : "Subscription failed",
      }));
      return false;
    }
  };

  const unsubscribe = async (): Promise<boolean> => {
    if (!registration) return false;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        // Unsubscribe from push
        await subscription.unsubscribe();

        // Notify backend
        await fetch("/api/v1/notifications/unsubscribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ endpoint: subscription.endpoint }),
        });
      }

      setState((prev) => ({
        ...prev,
        isSubscribed: false,
        isLoading: false,
      }));

      return true;
    } catch (error) {
      console.error("[Push] Unsubscribe failed:", error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : "Unsubscribe failed",
      }));
      return false;
    }
  };

  return {
    ...state,
    subscribe,
    unsubscribe,
  };
}

// Helper to convert VAPID key
function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray as Uint8Array<ArrayBuffer>;
}
