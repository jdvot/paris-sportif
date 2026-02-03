"use client";

import { useEffect } from "react";
import { PWAInstallPrompt, PWAUpdatePrompt, OfflineIndicator } from "./PWAInstallPrompt";

export function PWAProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Register service worker
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker
        .register("/sw.js")
        .then((registration) => {
          console.log("[PWA] Service Worker registered with scope:", registration.scope);

          // Check for updates on page load
          registration.update();
        })
        .catch((error) => {
          console.error("[PWA] Service Worker registration failed:", error);
        });
    }
  }, []);

  return (
    <>
      <OfflineIndicator />
      {children}
      <PWAInstallPrompt />
      <PWAUpdatePrompt />
    </>
  );
}
