import { ImageResponse } from "next/og";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);

  // Get parameters
  const homeTeam = searchParams.get("home") || "Home Team";
  const awayTeam = searchParams.get("away") || "Away Team";
  const prediction = searchParams.get("prediction") || "home_win";
  const confidence = parseInt(searchParams.get("confidence") || "70", 10);
  const homeProb = parseInt(searchParams.get("homeProb") || "50", 10);
  const drawProb = parseInt(searchParams.get("drawProb") || "25", 10);
  const awayProb = parseInt(searchParams.get("awayProb") || "25", 10);
  const competition = searchParams.get("competition") || "Football";

  // Prediction labels
  const predictionLabels: Record<string, string> = {
    home_win: `Victoire ${homeTeam}`,
    home: `Victoire ${homeTeam}`,
    draw: "Match nul",
    away_win: `Victoire ${awayTeam}`,
    away: `Victoire ${awayTeam}`,
  };

  const predictionLabel = predictionLabels[prediction] || prediction;

  // Confidence tier colors
  const getConfidenceColor = (conf: number) => {
    if (conf >= 75) return { bg: "#059669", text: "#ECFDF5" }; // emerald
    if (conf >= 65) return { bg: "#D97706", text: "#FFFBEB" }; // amber
    return { bg: "#DC2626", text: "#FEF2F2" }; // red
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
          backgroundColor: "#0F172A", // slate-900
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

        {/* Content container */}
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
          {/* Logo/Brand */}
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
            <span
              style={{
                fontSize: "28px",
                fontWeight: "bold",
                color: "#F8FAFC",
              }}
            >
              WinRate AI
            </span>
          </div>

          {/* Competition badge */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              padding: "8px 16px",
              background: "rgba(148, 163, 184, 0.2)",
              borderRadius: "20px",
              marginBottom: "24px",
            }}
          >
            <span
              style={{
                fontSize: "16px",
                color: "#94A3B8",
              }}
            >
              {competition}
            </span>
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
            <span
              style={{
                fontSize: "48px",
                fontWeight: "bold",
                color: "#F8FAFC",
              }}
            >
              {homeTeam}
            </span>
            <span
              style={{
                fontSize: "36px",
                color: "#64748B",
              }}
            >
              vs
            </span>
            <span
              style={{
                fontSize: "48px",
                fontWeight: "bold",
                color: "#F8FAFC",
              }}
            >
              {awayTeam}
            </span>
          </div>

          {/* Probability bars */}
          <div
            style={{
              display: "flex",
              width: "100%",
              gap: "16px",
              marginBottom: "40px",
            }}
          >
            <ProbabilityBar
              label={homeTeam}
              prob={homeProb}
              isSelected={prediction === "home_win" || prediction === "home"}
            />
            <ProbabilityBar
              label="Nul"
              prob={drawProb}
              isSelected={prediction === "draw"}
            />
            <ProbabilityBar
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
              gap: "16px",
              padding: "24px 40px",
              background: `linear-gradient(135deg, ${confColor.bg}22 0%, ${confColor.bg}11 100%)`,
              border: `2px solid ${confColor.bg}`,
              borderRadius: "16px",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontSize: "14px",
                  color: "#94A3B8",
                  marginBottom: "4px",
                }}
              >
                PREDICTION
              </span>
              <span
                style={{
                  fontSize: "28px",
                  fontWeight: "bold",
                  color: confColor.bg,
                }}
              >
                {predictionLabel}
              </span>
            </div>

            <div
              style={{
                width: "2px",
                height: "60px",
                background: "#334155",
              }}
            />

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontSize: "14px",
                  color: "#94A3B8",
                  marginBottom: "4px",
                }}
              >
                CONFIANCE
              </span>
              <span
                style={{
                  fontSize: "36px",
                  fontWeight: "bold",
                  color: confColor.bg,
                }}
              >
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
            gap: "8px",
          }}
        >
          <span
            style={{
              fontSize: "14px",
              color: "#64748B",
            }}
          >
            paris-sportif.vercel.app
          </span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}

function ProbabilityBar({
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
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
        }}
      >
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
