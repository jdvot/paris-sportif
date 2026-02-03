"use client";

import Script from "next/script";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, Suspense } from "react";

const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

function AnalyticsPageView() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!GA_MEASUREMENT_ID || typeof window.gtag !== "function") return;

    const search = searchParams?.toString();
    const url = pathname + (search ? `?${search}` : "");
    window.gtag("config", GA_MEASUREMENT_ID, {
      page_path: url,
    });
  }, [pathname, searchParams]);

  return null;
}

export function Analytics() {
  if (!GA_MEASUREMENT_ID) return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
        strategy="afterInteractive"
      />
      <Script id="google-analytics" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', '${GA_MEASUREMENT_ID}', {
            page_path: window.location.pathname,
          });
        `}
      </Script>
      <Suspense fallback={null}>
        <AnalyticsPageView />
      </Suspense>
    </>
  );
}

export function trackEvent(action: string, category: string, label?: string, value?: number) {
  if (!GA_MEASUREMENT_ID || typeof window.gtag !== "function") return;

  window.gtag("event", action, {
    event_category: category,
    event_label: label,
    value: value,
  });
}

export const analyticsEvents = {
  viewPrediction: (matchId: string) => trackEvent("view_prediction", "predictions", matchId),
  clickPick: (matchId: string, betType: string) => trackEvent("click_pick", "picks", `${matchId}_${betType}`),
  signup: () => trackEvent("sign_up", "auth"),
  login: () => trackEvent("login", "auth"),
  subscribe: (plan: string) => trackEvent("subscribe", "subscription", plan),
  exportCSV: () => trackEvent("export_csv", "tools"),
};

declare global {
  interface Window {
    gtag: (command: string, ...args: unknown[]) => void;
    dataLayer: unknown[];
  }
}
