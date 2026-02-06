"use client";

import { useEffect, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

const TRUSTPILOT_SCRIPT_URL =
  "https://widget.trustpilot.com/bootstrap/v5/tp.widget.bootstrap.min.js";

const TRUSTPILOT_TEMPLATE_ID = "5419b6a8b0d04a076446a9ad"; // micro-review-count / mini

interface TrustpilotWidgetProps {
  className?: string;
}

/**
 * Loads the official Trustpilot TrustBox widget.
 *
 * Requires `NEXT_PUBLIC_TRUSTPILOT_BUSINESS_ID` to be set.
 * If the env var is missing, the component renders nothing.
 */
export function TrustpilotWidget({ className }: TrustpilotWidgetProps) {
  const t = useTranslations("trustpilot");
  const trustBoxRef = useRef<HTMLDivElement>(null);
  const scriptLoadedRef = useRef(false);

  const businessId = process.env.NEXT_PUBLIC_TRUSTPILOT_BUSINESS_ID;

  const initializeTrustBox = useCallback(() => {
    const tp = (window as WindowWithTrustpilot).Trustpilot;
    if (trustBoxRef.current && typeof window !== "undefined" && tp) {
      tp.loadFromElement(trustBoxRef.current, true);
    }
  }, []);

  useEffect(() => {
    if (!businessId) return;

    // If the script is already on the page, just initialize
    const existingScript = document.querySelector(
      `script[src="${TRUSTPILOT_SCRIPT_URL}"]`
    );

    if (existingScript) {
      scriptLoadedRef.current = true;
      initializeTrustBox();
      return;
    }

    // Load the Trustpilot bootstrap script once
    const script = document.createElement("script");
    script.src = TRUSTPILOT_SCRIPT_URL;
    script.async = true;

    script.onload = () => {
      scriptLoadedRef.current = true;
      initializeTrustBox();
    };

    document.head.appendChild(script);

    return () => {
      // Cleanup: only remove the script if we added it
      if (!scriptLoadedRef.current) {
        script.remove();
      }
    };
  }, [businessId, initializeTrustBox]);

  // Don't render anything if no business ID is configured
  if (!businessId) {
    return null;
  }

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 dark:border-dark-700 dark:bg-dark-800/50",
        className
      )}
    >
      <span className="text-xs font-medium text-gray-500 dark:text-dark-400">
        {t("ratedOn")}
      </span>
      <div
        ref={trustBoxRef}
        className="trustpilot-widget"
        data-locale="en-US"
        data-template-id={TRUSTPILOT_TEMPLATE_ID}
        data-businessunit-id={businessId}
        data-style-height="20px"
        data-style-width="100%"
        data-theme="dark"
      >
        <a
          href={`https://www.trustpilot.com/review/${businessId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-semibold text-green-600 hover:underline dark:text-green-400"
        >
          Trustpilot
        </a>
      </div>
    </div>
  );
}

/** Extend Window to include the Trustpilot global */
interface WindowWithTrustpilot extends Window {
  Trustpilot?: {
    loadFromElement: (element: HTMLElement, useNewApi: boolean) => void;
  };
}
