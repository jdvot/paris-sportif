import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/AppShell";
import { Analytics } from "@/components/Analytics";
import { PWAProvider } from "@/components/PWAProvider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://paris-sportif.vercel.app";

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#3b82f6" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Paris Sportif - Predictions Football IA",
    template: "%s | Paris Sportif",
  },
  description:
    "Predictions de paris sportifs football analysees par IA. Modeles Poisson, ELO, xG et Machine Learning. 5 picks premium par jour sur les championnats europeens.",
  keywords: [
    "paris sportifs",
    "football",
    "predictions",
    "pronostics",
    "betting",
    "IA",
    "machine learning",
    "Premier League",
    "Ligue 1",
    "La Liga",
    "Serie A",
    "Bundesliga",
  ],
  authors: [{ name: "Paris Sportif" }],
  creator: "Paris Sportif",
  publisher: "Paris Sportif",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "fr_FR",
    url: siteUrl,
    siteName: "Paris Sportif",
    title: "Paris Sportif - Predictions Football IA",
    description:
      "Predictions de paris sportifs football analysees par IA. 5 picks premium par jour.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Paris Sportif - Predictions Football",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Paris Sportif - Predictions Football IA",
    description:
      "Predictions de paris sportifs football analysees par IA. 5 picks premium par jour.",
    images: ["/og-image.png"],
  },
  alternates: {
    canonical: siteUrl,
  },
  category: "sports",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Paris Sportif",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192x192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512x512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [
      { url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "Paris Sportif",
  description:
    "Application de predictions de paris sportifs sur le football europeen analysees par IA",
  url: siteUrl,
  applicationCategory: "SportsApplication",
  operatingSystem: "Web",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "EUR",
  },
  author: {
    "@type": "Organization",
    name: "Paris Sportif",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} className={inter.variable} suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="font-sans antialiased">
        <Analytics />
        <NextIntlClientProvider messages={messages}>
          <Providers>
            <PWAProvider>
              <AppShell>{children}</AppShell>
            </PWAProvider>
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
