import type { Metadata } from "next";

type Props = {
  params: Promise<{ id: string }>;
  children: React.ReactNode;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id: matchId } = await params;

  // Default metadata
  let title = "Prediction de match - WinRate AI";
  let description = "Analyse et prediction de match de football avec intelligence artificielle.";
  let homeTeam = "Equipe";
  let awayTeam = "Equipe";

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(`${apiUrl}/api/v1/predictions/${matchId}`, {
      next: { revalidate: 300 },
    });

    if (response.ok) {
      const data = await response.json();
      homeTeam = data.home_team || homeTeam;
      awayTeam = data.away_team || awayTeam;
      const confidence = Math.round((data.confidence || 0.7) * 100);

      title = `${homeTeam} vs ${awayTeam} - Prediction WinRate AI`;
      description = `Prediction pour ${homeTeam} vs ${awayTeam}. Confiance: ${confidence}%. Analyse ML et IA avancée.`;
    }
  } catch {
    // Use defaults
  }

  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "https://paris-sportif.vercel.app";

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      url: `${baseUrl}/match/${matchId}`,
      siteName: "WinRate AI",
      images: [
        {
          url: `${baseUrl}/match/${matchId}/opengraph-image`,
          width: 1200,
          height: 630,
          alt: `${homeTeam} vs ${awayTeam} - Prediction`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [`${baseUrl}/match/${matchId}/opengraph-image`],
    },
  };
}

export default function MatchLayout({ children }: Props) {
  return <>{children}</>;
}
