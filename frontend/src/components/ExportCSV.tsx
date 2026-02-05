"use client";

import { Download } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DailyPickResponse } from "@/lib/api/models";
import { getConfidenceTier, getValueTier } from "@/lib/constants";

interface ExportCSVProps {
  picks: DailyPickResponse[];
  filename?: string;
  className?: string;
  variant?: "button" | "icon";
}

export function ExportCSV({
  picks,
  filename = "paris-sportif-picks",
  className,
  variant = "button",
}: ExportCSVProps) {
  const exportToCSV = () => {
    if (!picks || picks.length === 0) return;

    const headers = [
      "Rang",
      "Match",
      "Date",
      "Pari Recommandé",
      "Confiance (%)",
      "Niveau Confiance",
      "Value Score (%)",
      "Niveau Value",
      "Prob Domicile (%)",
      "Prob Nul (%)",
      "Prob Extérieur (%)",
      "Pick Score",
      "Explication",
      "Facteurs Clés",
      "Risques",
    ];

    const rows = picks.map((pick) => {
      const p = pick.prediction;
      const confidenceTier = getConfidenceTier(p.confidence || 0);
      const valueTier = getValueTier(p.value_score || 0);

      const betLabel = {
        home: `Victoire ${p.home_team}`,
        home_win: `Victoire ${p.home_team}`,
        draw: "Match nul",
        away: `Victoire ${p.away_team}`,
        away_win: `Victoire ${p.away_team}`,
      }[p.recommended_bet] || p.recommended_bet;

      return [
        pick.rank,
        `${p.home_team} vs ${p.away_team}`,
        p.match_date || "",
        betLabel,
        Math.round((p.confidence || 0) * 100),
        confidenceTier.label,
        Math.round((p.value_score || 0) * 100),
        valueTier.label,
        Math.round((p.probabilities?.home_win || 0) * 100),
        Math.round((p.probabilities?.draw || 0) * 100),
        Math.round((p.probabilities?.away_win || 0) * 100),
        pick.pick_score?.toFixed(2) || "",
        p.explanation?.replace(/"/g, '""') || "",
        (p.key_factors || []).join("; "),
        (p.risk_factors || []).join("; "),
      ];
    });

    // Build CSV content
    const csvContent = [
      headers.join(","),
      ...rows.map((row) =>
        row
          .map((cell) => {
            const str = String(cell);
            // Escape cells containing commas, quotes, or newlines
            if (str.includes(",") || str.includes('"') || str.includes("\n")) {
              return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
          })
          .join(",")
      ),
    ].join("\n");

    // Create and download file
    const blob = new Blob(["\ufeff" + csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (variant === "icon") {
    return (
      <button
        onClick={exportToCSV}
        disabled={!picks || picks.length === 0}
        className={cn(
          "p-2 rounded-lg transition-colors",
          "bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600",
          "text-gray-600 dark:text-dark-300 hover:text-gray-900 dark:hover:text-white",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          className
        )}
        title="Exporter en CSV"
      >
        <Download className="w-5 h-5" />
      </button>
    );
  }

  return (
    <button
      onClick={exportToCSV}
      disabled={!picks || picks.length === 0}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors",
        "bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600",
        "text-gray-700 dark:text-dark-300 hover:text-gray-900 dark:hover:text-white",
        "text-sm font-medium",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className
      )}
    >
      <Download className="w-4 h-4" />
      <span>Exporter CSV</span>
    </button>
  );
}
