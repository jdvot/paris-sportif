import type { Metadata } from "next";

type Props = {
  params: Promise<{ id: string }>;
  children: React.ReactNode;
};

interface PredictionData {
  home_team?: string;
  away_team?: string;
  match_date?: string;
  competition?: string;
  confidence?: number;
  probabilities?: {
    home_win?: number;
    draw?: number;
    away_win?: number;
  };
}

async function fetchPrediction(matchId: string): Promise<PredictionData | null> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(`${apiUrl}/api/v1/predictions/${matchId}`, {
      next: { revalidate: 300 },
    });

    if (response.ok) {
      return await response.json();
    }
  } catch {
    // Ignore errors
  }
  return null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id: matchId } = await params;

  // Default metadata
  let title = "Prediction de match - WinRate AI";
  let description = "Analyse et prediction de match de football avec intelligence artificielle.";
  let homeTeam = "Equipe";
  let awayTeam = "Equipe";

  const data = await fetchPrediction(matchId);
  if (data) {
    homeTeam = data.home_team || homeTeam;
    awayTeam = data.away_team || awayTeam;
    const confidence = Math.round((data.confidence || 0.7) * 100);

    title = `${homeTeam} vs ${awayTeam} - Prediction WinRate AI`;
    description = `Prediction pour ${homeTeam} vs ${awayTeam}. Confiance: ${confidence}%. Analyse ML et IA avancée.`;
  }

  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "https://paris-sportif.vercel.app";

  return {
    title,
    description,
    alternates: {
      canonical: `${baseUrl}/match/${matchId}`,
    },
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

function SportsEventJsonLd({
  matchId,
  homeTeam,
  awayTeam,
  matchDate,
  competition,
  baseUrl,
}: {
  matchId: string;
  homeTeam: string;
  awayTeam: string;
  matchDate?: string;
  competition?: string;
  baseUrl: string;
}) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    name: `${homeTeam} vs ${awayTeam}`,
    description: `Match de football: ${homeTeam} contre ${awayTeam}${competition ? ` - ${competition}` : ""}`,
    url: `${baseUrl}/match/${matchId}`,
    startDate: matchDate || new Date().toISOString(),
    eventStatus: "https://schema.org/EventScheduled",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    sport: "Football",
    homeTeam: {
      "@type": "SportsTeam",
      name: homeTeam,
    },
    awayTeam: {
      "@type": "SportsTeam",
      name: awayTeam,
    },
    organizer: {
      "@type": "Organization",
      name: competition || "Football League",
    },
    location: {
      "@type": "Place",
      name: `${homeTeam} Stadium`,
      address: {
        "@type": "PostalAddress",
        addressCountry: "EU",
      },
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}

export default async function MatchLayout({ params, children }: Props) {
  const { id: matchId } = await params;
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "https://paris-sportif.vercel.app";

  const data = await fetchPrediction(matchId);
  const homeTeam = data?.home_team || "Equipe Domicile";
  const awayTeam = data?.away_team || "Equipe Exterieure";
  const matchDate = data?.match_date;
  const competition = data?.competition;

  return (
    <>
      <SportsEventJsonLd
        matchId={matchId}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        matchDate={matchDate}
        competition={competition}
        baseUrl={baseUrl}
      />
      {children}
    </>
  );
}
