import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Performance Monitoring
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

  // Session Replay
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Environment
  environment: process.env.NODE_ENV,

  // Release tracking
  release: process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA,

  // Filter out non-actionable errors
  ignoreErrors: [
    "Failed to fetch",
    "NetworkError",
    "Load failed",
    /^chrome-extension:\/\//,
    /^moz-extension:\/\//,
    "Minified React error",
    "Hydration failed",
  ],

  enabled: process.env.NODE_ENV === "production",
});
