import { MetadataRoute } from "next";

interface Match {
  id: number;
  match_date?: string;
}

interface MatchesResponse {
  data?: Match[];
}

async function fetchUpcomingMatches(): Promise<Match[]> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(`${apiUrl}/api/v1/matches?limit=100`, {
      next: { revalidate: 3600 }, // Cache for 1 hour
    });

    if (!response.ok) {
      return [];
    }

    const result: MatchesResponse = await response.json();
    return result.data || [];
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://paris-sportif.vercel.app";

  // Static pages
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${siteUrl}/matches`,
      lastModified: new Date(),
      changeFrequency: "hourly",
      priority: 0.9,
    },
    {
      url: `${siteUrl}/picks`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${siteUrl}/stats`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.7,
    },
    {
      url: `${siteUrl}/plans`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.6,
    },
  ];

  // Dynamic match pages
  const matches = await fetchUpcomingMatches();
  const matchPages: MetadataRoute.Sitemap = matches.map((match) => ({
    url: `${siteUrl}/match/${match.id}`,
    lastModified: match.match_date ? new Date(match.match_date) : new Date(),
    changeFrequency: "daily" as const,
    priority: 0.8,
  }));

  return [...staticPages, ...matchPages];
}
