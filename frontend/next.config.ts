import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  // Enable React strict mode for development
  reactStrictMode: true,

  // Output standalone for Docker deployment
  output: "standalone",

  // Security headers
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
          {
            key: "X-Frame-Options",
            value: "SAMEORIGIN",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https://crests.football-data.org",
              "font-src 'self' data:",
              "connect-src 'self' https://*.supabase.co wss://*.supabase.co https://*.sentry.io https://*.onrender.com",
              "frame-ancestors 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },

  // API rewrites for development
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
          : "http://localhost:8000/api/:path*",
      },
    ];
  },

  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "crests.football-data.org",
      },
    ],
  },
};

// Wrap with Sentry for error tracking
export default withSentryConfig(withNextIntl(nextConfig), {
  // Sentry options
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  // Suppress logs during build
  silent: true,

  // Upload source maps for better error traces
  widenClientFileUpload: true,

  // Hide source maps from clients
  hideSourceMaps: true,

  // Tree shake Sentry for smaller bundle
  disableLogger: true,
});
