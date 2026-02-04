import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "WinRate AI - Prediction de match";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id: matchId } = await params;

  // Fetch match data from API
  let homeTeam = "Equipe Domicile";
  let awayTeam = "Equipe Extérieure";
  let prediction = "home_win";
  let confidence = 70;
  let homeProb = 50;
  let drawProb = 25;
  let awayProb = 25;
  const competition = "Football";

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // Use matches endpoint (doesn't require auth) for basic match info
    const response = await fetch(`${apiUrl}/api/v1/matches/${matchId}`, {
      next: { revalidate: 300 }, // Cache for 5 minutes
    });

    if (response.ok) {
      const data = await response.json();
      // Get team names from match data
      homeTeam = typeof data.home_team === 'string' ? data.home_team : (data.home_team?.name || homeTeam);
      awayTeam = typeof data.away_team === 'string' ? data.away_team : (data.away_team?.name || awayTeam);
      // Note: prediction data (confidence, probabilities) requires auth
      // OG image will use default values for these
    }
  } catch {
    // Use defaults
  }

  // Prediction labels
  const predictionLabels: Record<string, string> = {
    home_win: `Victoire ${homeTeam}`,
    home: `Victoire ${homeTeam}`,
    draw: "Match nul",
    away_win: `Victoire ${awayTeam}`,
    away: `Victoire ${awayTeam}`,
  };

  const predictionLabel = predictionLabels[prediction] || prediction;

  // Confidence color
  const getConfidenceColor = (conf: number) => {
    if (conf >= 75) return "#059669"; // emerald
    if (conf >= 65) return "#D97706"; // amber
    return "#DC2626"; // red
  };

  const confColor = getConfidenceColor(confidence);

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#0F172A",
          padding: "40px",
        }}
      >
        {/* Background gradient */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%)",
          }}
        />

        {/* Content */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1,
            width: "100%",
            maxWidth: "1000px",
          }}
        >
          {/* Logo */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "32px",
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                background: "linear-gradient(135deg, #10B981 0%, #059669 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "24px",
              }}
            >
              ⚽
            </div>
            <span style={{ fontSize: "28px", fontWeight: "bold", color: "#F8FAFC" }}>
              WinRate AI
            </span>
          </div>

          {/* Competition */}
          <div
            style={{
              display: "flex",
              padding: "8px 16px",
              background: "rgba(148, 163, 184, 0.2)",
              borderRadius: "20px",
              marginBottom: "24px",
            }}
          >
            <span style={{ fontSize: "16px", color: "#94A3B8" }}>{competition}</span>
          </div>

          {/* Match title */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "24px",
              marginBottom: "40px",
            }}
          >
            <span style={{ fontSize: "48px", fontWeight: "bold", color: "#F8FAFC" }}>
              {homeTeam.length > 15 ? homeTeam.slice(0, 14) + "…" : homeTeam}
            </span>
            <span style={{ fontSize: "36px", color: "#64748B" }}>vs</span>
            <span style={{ fontSize: "48px", fontWeight: "bold", color: "#F8FAFC" }}>
              {awayTeam.length > 15 ? awayTeam.slice(0, 14) + "…" : awayTeam}
            </span>
          </div>

          {/* Probability bars */}
          <div style={{ display: "flex", width: "100%", gap: "16px", marginBottom: "40px" }}>
            <ProbBar
              label={homeTeam}
              prob={homeProb}
              isSelected={prediction === "home_win" || prediction === "home"}
            />
            <ProbBar label="Nul" prob={drawProb} isSelected={prediction === "draw"} />
            <ProbBar
              label={awayTeam}
              prob={awayProb}
              isSelected={prediction === "away_win" || prediction === "away"}
            />
          </div>

          {/* Prediction box */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "24px",
              padding: "24px 40px",
              background: `${confColor}15`,
              border: `2px solid ${confColor}`,
              borderRadius: "16px",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span style={{ fontSize: "14px", color: "#94A3B8", marginBottom: "4px" }}>
                PREDICTION
              </span>
              <span style={{ fontSize: "28px", fontWeight: "bold", color: confColor }}>
                {predictionLabel.length > 25 ? predictionLabel.slice(0, 24) + "…" : predictionLabel}
              </span>
            </div>

            <div style={{ width: "2px", height: "60px", background: "#334155" }} />

            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span style={{ fontSize: "14px", color: "#94A3B8", marginBottom: "4px" }}>
                CONFIANCE
              </span>
              <span style={{ fontSize: "36px", fontWeight: "bold", color: confColor }}>
                {confidence}%
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            position: "absolute",
            bottom: "24px",
            display: "flex",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: "14px", color: "#64748B" }}>paris-sportif.vercel.app</span>
        </div>
      </div>
    ),
    { ...size }
  );
}

function ProbBar({
  label,
  prob,
  isSelected,
}: {
  label: string;
  prob: number;
  isSelected: boolean;
}) {
  const truncatedLabel = label.length > 12 ? label.slice(0, 11) + "…" : label;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span
          style={{
            fontSize: "16px",
            fontWeight: isSelected ? "bold" : "normal",
            color: isSelected ? "#10B981" : "#94A3B8",
          }}
        >
          {truncatedLabel}
        </span>
        <span
          style={{
            fontSize: "16px",
            fontWeight: "bold",
            color: isSelected ? "#10B981" : "#94A3B8",
          }}
        >
          {prob}%
        </span>
      </div>
      <div
        style={{
          width: "100%",
          height: "12px",
          background: "#334155",
          borderRadius: "6px",
          overflow: "hidden",
          display: "flex",
        }}
      >
        <div
          style={{
            width: `${prob}%`,
            height: "100%",
            background: isSelected
              ? "linear-gradient(90deg, #10B981 0%, #059669 100%)"
              : "#475569",
            borderRadius: "6px",
          }}
        />
      </div>
    </div>
  );
}
