import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/AppShell";
import { Analytics } from "@/components/Analytics";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://paris-sportif.vercel.app";

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

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className={inter.variable} suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="font-sans antialiased">
        <Analytics />
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
