"use client";

import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useTheme } from "next-themes";
import type { DetailedPrediction, ModelContribution } from "@/lib/types";
import type { PredictionResponse } from "@/lib/api/models";
import { cn } from "@/lib/utils";

/**
 * Union type for prediction data - accepts both frontend (camelCase) and API (snake_case) formats.
 * The component handles both formats with fallback logic.
 */
export type PredictionChartsInput = DetailedPrediction | PredictionResponse;

/**
 * Helper to safely extract a numeric value from either camelCase or snake_case property.
 */
function getNumericValue(obj: PredictionChartsInput, camelKey: string, snakeKey: string): number {
  const record = obj as unknown as Record<string, unknown>;
  if (typeof record[camelKey] === "number") return record[camelKey] as number;
  if (typeof record[snakeKey] === "number") return record[snakeKey] as number;
  return 0;
}

/**
 * Helper to safely extract an object value from either camelCase or snake_case property.
 */
function getObjectValue(obj: PredictionChartsInput, camelKey: string, snakeKey: string): unknown {
  const record = obj as unknown as Record<string, unknown>;
  return record[camelKey] ?? record[snakeKey];
}

/**
 * Helper to check if a property exists (with either naming convention).
 */
function hasProperty(obj: PredictionChartsInput, camelKey: string, snakeKey: string): boolean {
  const record = obj as unknown as Record<string, unknown>;
  return record[camelKey] !== undefined || record[snakeKey] !== undefined;
}

// Theme-aware color palette
const getColors = (isDark: boolean) => ({
  primary: "#10B981", // green - home
  yellow: "#F59E0B", // yellow - draw
  accent: "#3B82F6", // blue - away
  background: isDark ? "#1e293b" : "#ffffff", // slate-800 / white
  gridLine: isDark ? "#334155" : "#e2e8f0", // slate-700 / slate-200
  border: isDark ? "#475569" : "#cbd5e1", // slate-600 / slate-300
  text: isDark ? "#f1f5f9" : "#1e293b", // slate-100 / slate-800
  textSecondary: isDark ? "#94a3b8" : "#64748b", // slate-400 / slate-500
});

interface PredictionChartsProps {
  prediction: PredictionChartsInput;
}

/**
 * Probability Pie Chart - Shows home/draw/away probabilities
 */
function ProbabilityPieChart({ prediction }: PredictionChartsProps) {
  const { resolvedTheme } = useTheme();
  const colors = getColors(resolvedTheme === "dark");

  const probs = prediction?.probabilities as Record<string, number> | undefined;

  // Try direct properties first (DetailedPrediction), then nested probabilities (PredictionResponse)
  const homeProb = getNumericValue(prediction, "homeProb", "homeProb") ||
    (typeof probs?.home_win === "number" ? probs.home_win : 0) ||
    (typeof probs?.homeWin === "number" ? probs.homeWin : 0);

  const drawProb = getNumericValue(prediction, "drawProb", "drawProb") ||
    (typeof probs?.draw === "number" ? probs.draw : 0);

  const awayProb = getNumericValue(prediction, "awayProb", "awayProb") ||
    (typeof probs?.away_win === "number" ? probs.away_win : 0) ||
    (typeof probs?.awayWin === "number" ? probs.awayWin : 0);

  const data = [
    { name: "Domicile", value: Math.round(homeProb * 100) },
    { name: "Nul", value: Math.round(drawProb * 100) },
    { name: "Extérieur", value: Math.round(awayProb * 100) },
  ];

  const pieColors = [colors.primary, colors.yellow, colors.accent];

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4 transition-colors">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white">Probabilités de Résultat</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, value }) => `${name}: ${value}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={pieColors[index]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: colors.background,
              border: `1px solid ${colors.border}`,
              borderRadius: "8px",
              color: colors.text,
            }}
            formatter={(value) => `${value}%`}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="grid grid-cols-3 gap-2 text-xs sm:text-sm">
        <div className="text-center p-2 bg-primary-500/10 rounded">
          <div className="font-bold text-primary-400">{Math.round(homeProb * 100)}%</div>
          <div className="text-gray-500 dark:text-slate-400">Domicile</div>
        </div>
        <div className="text-center p-2 bg-yellow-500/10 rounded">
          <div className="font-bold text-yellow-400">{Math.round(drawProb * 100)}%</div>
          <div className="text-gray-500 dark:text-slate-400">Nul</div>
        </div>
        <div className="text-center p-2 bg-accent-500/10 rounded">
          <div className="font-bold text-accent-400">{Math.round(awayProb * 100)}%</div>
          <div className="text-gray-500 dark:text-slate-400">Extérieur</div>
        </div>
      </div>
    </div>
  );
}

/**
 * Model Comparison Bar Chart - Compare predictions from different models
 */
function ModelComparisonChart({ prediction }: PredictionChartsProps) {
  const { resolvedTheme } = useTheme();
  const colors = getColors(resolvedTheme === "dark");

  const modelContributions = getObjectValue(prediction, "modelContributions", "model_contributions");
  if (!modelContributions || typeof modelContributions !== "object") {
    return null;
  }

  const models = Object.entries(modelContributions as Record<string, unknown>)
    .filter(([, value]) => value && typeof value === "object")
    .slice(0, 4); // Limit to 4 models for readability

  if (models.length === 0) {
    return null;
  }

  const modelDisplayNames: Record<string, string> = {
    poisson: "Poisson",
    elo: "ELO",
    dixon_coles: "Dixon-Coles",
    xgModel: "xG",
    xgboost: "XGBoost",
    random_forest: "Random Forest",
    advanced_elo: "ELO Avancé",
  };

  const chartData = models.map(([modelName, contribution]) => {
    const contrib = contribution as ModelContribution;
    const homeProb = contrib?.homeProb || contrib?.homeWin || 0;
    const drawProb = contrib?.drawProb || contrib?.draw || 0;
    const awayProb = contrib?.awayProb || contrib?.awayWin || 0;

    return {
      name: modelDisplayNames[modelName] || modelName,
      Domicile: Math.round(homeProb * 100),
      Nul: Math.round(drawProb * 100),
      Extérieur: Math.round(awayProb * 100),
    };
  });

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4 transition-colors">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white">Comparaison des Modèles</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.gridLine} />
          <XAxis dataKey="name" stroke={colors.textSecondary} />
          <YAxis stroke={colors.textSecondary} />
          <Tooltip
            contentStyle={{
              backgroundColor: colors.background,
              border: `1px solid ${colors.border}`,
              borderRadius: "8px",
              color: colors.text,
            }}
            formatter={(value) => `${value}%`}
          />
          <Legend wrapperStyle={{ color: colors.textSecondary }} />
          <Bar dataKey="Domicile" fill={colors.primary} />
          <Bar dataKey="Nul" fill={colors.yellow} />
          <Bar dataKey="Extérieur" fill={colors.accent} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Confidence Gauge - Visual gauge showing confidence level (0-100%)
 */
function ConfidenceGauge({ prediction }: PredictionChartsProps) {
  const { resolvedTheme } = useTheme();
  const colors = getColors(resolvedTheme === "dark");

  const confidence = typeof prediction?.confidence === "number" ? prediction.confidence : 0;
  const confidencePercent = Math.round(confidence * 100);

  const confidenceColor =
    confidencePercent >= 70
      ? "text-primary-400"
      : confidencePercent >= 60
        ? "text-yellow-400"
        : "text-orange-400";

  const confidenceBg =
    confidencePercent >= 70
      ? "from-primary-500/20 to-primary-500/5"
      : confidencePercent >= 60
        ? "from-yellow-500/20 to-yellow-500/5"
        : "from-orange-500/20 to-orange-500/5";

  const confidenceBorder =
    confidencePercent >= 70
      ? "border-primary-500/30"
      : confidencePercent >= 60
        ? "border-yellow-500/30"
        : "border-orange-500/30";

  return (
    <div
      className={cn(
        "bg-gradient-to-br rounded-xl p-4 sm:p-6 space-y-4 border transition-colors",
        confidenceBg,
        confidenceBorder
      )}
    >
      <h3 className="text-lg font-bold text-gray-900 dark:text-white">Niveau de Confiance</h3>

      {/* Gauge visualization */}
      <div className="flex flex-col items-center space-y-3">
        <div className="relative w-32 h-32">
          {/* Background circle */}
          <svg
            viewBox="0 0 100 100"
            className="absolute inset-0 w-full h-full transform -rotate-90"
          >
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke={colors.gridLine}
              strokeWidth="8"
            />
            {/* Confidence arc */}
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke={
                confidencePercent >= 70
                  ? colors.primary
                  : confidencePercent >= 60
                    ? colors.yellow
                    : "#FF6B35"
              }
              strokeWidth="8"
              strokeDasharray={`${(confidencePercent / 100) * 283} 283`}
              strokeLinecap="round"
            />
          </svg>

          {/* Center text */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className={cn("text-3xl font-bold", confidenceColor)}>
                {confidencePercent}%
              </div>
              <div className="text-xs text-gray-500 dark:text-slate-400">Confiance</div>
            </div>
          </div>
        </div>

        {/* Confidence level label */}
        <div className="text-sm text-center">
          <p className={cn("font-semibold", confidenceColor)}>
            {confidencePercent >= 70
              ? "Très Élevée"
              : confidencePercent >= 60
                ? "Élevée"
                : confidencePercent >= 50
                  ? "Modérée"
                  : "Faible"}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-2 space-y-2 mt-2">
        <p className="text-xs font-medium text-gray-600 dark:text-slate-400 text-center">
          Barre de progression
        </p>
        <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden border border-gray-300 dark:border-slate-600 shadow-inner">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-700 ease-out shadow-md",
              confidencePercent >= 70
                ? "bg-gradient-to-r from-primary-600 via-primary-500 to-primary-400"
                : confidencePercent >= 60
                  ? "bg-gradient-to-r from-yellow-600 via-yellow-500 to-yellow-400"
                  : "bg-gradient-to-r from-orange-600 via-orange-500 to-orange-400"
            )}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
        {/* Confidence scale */}
        <div className="flex justify-between text-xs text-gray-500 dark:text-slate-400 font-medium">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Value Score Indicator - Show the value score with color coding
 */
function ValueScoreIndicator({ prediction }: PredictionChartsProps) {
  const valueScore = getNumericValue(prediction, "valueScore", "value_score");
  const valuePercent = Math.round(valueScore * 100);

  const isPositiveValue = valueScore >= 0;
  const valueColor = isPositiveValue ? "text-primary-400" : "text-red-400";
  const valueBg = isPositiveValue ? "from-primary-500/20 to-primary-500/5" : "from-red-500/20 to-red-500/5";
  const valueBorder = isPositiveValue ? "border-primary-500/30" : "border-red-500/30";

  const valueIntensity = Math.min(Math.abs(valueScore), 0.5); // Cap at 50% for visual intensity
  const barWidth = Math.round((valueIntensity / 0.5) * 100);

  return (
    <div
      className={cn(
        "bg-gradient-to-br rounded-xl p-4 sm:p-6 space-y-4 border transition-colors",
        valueBg,
        valueBorder
      )}
    >
      <h3 className="text-lg font-bold text-gray-900 dark:text-white">Indice de Valeur (Cote)</h3>

      <div className="space-y-4">
        {/* Main Value Display */}
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-slate-400 font-semibold">Valeur Estimée</span>
          <div className={cn("text-3xl font-bold", valueColor)}>
            {isPositiveValue ? "+" : ""}{valuePercent}%
          </div>
        </div>

        {/* Value Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500 dark:text-slate-400">Risque</span>
            <span className={cn("font-semibold", valueColor)}>
              {isPositiveValue ? "Favorable" : "Défavorable"}
            </span>
          </div>
          <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                isPositiveValue
                  ? "bg-gradient-to-r from-primary-500 to-primary-400"
                  : "bg-gradient-to-r from-red-500 to-red-400"
              )}
              style={{ width: `${barWidth}%` }}
            />
          </div>
        </div>

        {/* Value Scale */}
        <div className="grid grid-cols-3 gap-2 text-xs text-gray-500 dark:text-slate-400 text-center py-2 border-t border-gray-200 dark:border-slate-700 pt-3">
          <div>
            <div className="text-red-400 font-semibold">-50%</div>
            <div>Très Mauvaise</div>
          </div>
          <div>
            <div className="text-gray-500 dark:text-slate-400 font-semibold">0%</div>
            <div>Neutre</div>
          </div>
          <div>
            <div className="text-primary-400 font-semibold">+50%</div>
            <div>Excellente</div>
          </div>
        </div>

        {/* Value Interpretation */}
        <div className="p-2 bg-gray-100 dark:bg-slate-700/50 rounded text-xs text-gray-600 dark:text-slate-300">
          {valuePercent > 30
            ? "Excellent ROI attendu sur le long terme"
            : valuePercent > 10
              ? "Valeur intéressante, opportunité favorable"
              : valuePercent > 0
                ? "Léger avantage statistique"
                : valuePercent > -10
                  ? "Prédiction correcte mais sans valeur de cote"
                  : valuePercent > -30
                    ? "Valeur négative, attention au ROI"
                    : "Forte dévaluation, à éviter"}
        </div>
      </div>
    </div>
  );
}

/**
 * Expected Goals Chart - Show home vs away xG comparison
 */
function ExpectedGoalsChart({ prediction }: PredictionChartsProps) {
  const { resolvedTheme } = useTheme();
  const colors = getColors(resolvedTheme === "dark");

  const homeXg = getNumericValue(prediction, "expectedHomeGoals", "expected_home_goals");
  const awayXg = getNumericValue(prediction, "expectedAwayGoals", "expected_away_goals");

  if (homeXg === 0 && awayXg === 0) {
    return null;
  }

  const data = [
    {
      name: "Buts attendus (xG)",
      Domicile: parseFloat(homeXg.toFixed(2)),
      Extérieur: parseFloat(awayXg.toFixed(2)),
    },
  ];

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4 transition-colors">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white">Buts Attendus (xG)</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke={colors.gridLine} />
          <XAxis type="number" stroke={colors.textSecondary} />
          <YAxis dataKey="name" type="category" stroke={colors.textSecondary} width={120} />
          <Tooltip
            contentStyle={{
              backgroundColor: colors.background,
              border: `1px solid ${colors.border}`,
              borderRadius: "8px",
              color: colors.text,
            }}
            formatter={(value) => typeof value === 'number' ? value.toFixed(2) : value}
          />
          <Legend wrapperStyle={{ color: colors.textSecondary }} />
          <Bar dataKey="Domicile" fill={colors.primary} radius={[0, 8, 8, 0]} />
          <Bar dataKey="Extérieur" fill={colors.accent} radius={[0, 8, 8, 0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="p-3 bg-primary-500/10 rounded text-center">
          <div className="text-primary-400 font-bold">{homeXg.toFixed(2)}</div>
          <div className="text-xs text-gray-500 dark:text-slate-400">xG Domicile</div>
        </div>
        <div className="p-3 bg-accent-500/10 rounded text-center">
          <div className="text-accent-400 font-bold">{awayXg.toFixed(2)}</div>
          <div className="text-xs text-gray-500 dark:text-slate-400">xG Extérieur</div>
        </div>
      </div>
    </div>
  );
}

/**
 * Main PredictionCharts Component - Combines all charts
 */
export function PredictionCharts({ prediction }: PredictionChartsProps) {
  if (!prediction) {
    return null;
  }

  const hasModelContributions = hasProperty(prediction, "modelContributions", "model_contributions");
  const hasExpectedGoals = hasProperty(prediction, "expectedHomeGoals", "expected_home_goals") ||
    hasProperty(prediction, "expectedAwayGoals", "expected_away_goals");

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Pie Chart */}
        <ProbabilityPieChart prediction={prediction} />

        {/* Confidence Gauge */}
        <ConfidenceGauge prediction={prediction} />

        {/* Model Comparison */}
        {hasModelContributions && (
          <div className="lg:col-span-2">
            <ModelComparisonChart prediction={prediction} />
          </div>
        )}

        {/* Value Score */}
        <ValueScoreIndicator prediction={prediction} />

        {/* Expected Goals */}
        {hasExpectedGoals && (
          <ExpectedGoalsChart prediction={prediction} />
        )}
      </div>
    </div>
  );
}

export {
  ProbabilityPieChart,
  ModelComparisonChart,
  ConfidenceGauge,
  ValueScoreIndicator,
  ExpectedGoalsChart,
};
