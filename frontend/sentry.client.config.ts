import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Performance monitoring
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

  // Session replay for debugging
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Environment
  environment: process.env.NODE_ENV,

  // Only enable in production
  enabled: process.env.NODE_ENV === "production",

  // Filter out noisy errors
  ignoreErrors: [
    "ResizeObserver loop",
    "Non-Error promise rejection",
    "Load failed",
  ],

  beforeSend(event) {
    // Don't send events in development
    if (process.env.NODE_ENV !== "production") {
      return null;
    }
    return event;
  },
});
