import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "WinRate AI - Predictions Football IA",
    short_name: "WinRate AI",
    description:
      "Predictions de paris sportifs football analysees par IA. 5 picks premium par jour.",
    start_url: "/",
    display: "standalone",
    background_color: "#0f172a",
    theme_color: "#3b82f6",
    orientation: "portrait-primary",
    scope: "/",
    lang: "fr",
    categories: ["sports", "entertainment", "lifestyle"],
    icons: [
      {
        src: "/icons/icon-192x192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icons/icon-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-192x192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
    ],
    screenshots: [
      {
        src: "/screenshots/home.png",
        sizes: "1280x720",
        type: "image/png",
        form_factor: "wide",
        label: "Page d'accueil WinRate AI",
      },
      {
        src: "/screenshots/picks.png",
        sizes: "750x1334",
        type: "image/png",
        form_factor: "narrow",
        label: "Picks du jour",
      },
    ],
    shortcuts: [
      {
        name: "Picks du jour",
        short_name: "Picks",
        description: "Voir les 5 meilleurs picks du jour",
        url: "/picks",
        icons: [{ src: "/icons/shortcut-picks.png", sizes: "96x96" }],
      },
      {
        name: "Tous les matchs",
        short_name: "Matchs",
        description: "Liste des matchs a venir",
        url: "/matches",
        icons: [{ src: "/icons/shortcut-matches.png", sizes: "96x96" }],
      },
    ],
    related_applications: [],
    prefer_related_applications: false,
  };
}
