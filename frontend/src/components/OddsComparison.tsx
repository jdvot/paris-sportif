"use client";

import { useState } from "react";
import { TrendingUp, AlertTriangle, CheckCircle, BarChart3, DollarSign, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

interface OddsComparisonProps {
  homeProb: number;
  drawProb: number;
  awayProb: number;
  homeTeam: string;
  awayTeam: string;
}

interface OddsData {
  outcome: "home" | "draw" | "away";
  label: string;
  probability: number;
  fairOdds: number;
  bookmakerOdds?: number;
  valuePercentage?: number;
  hasValue?: boolean;
}

/**
 * Calculate fair odds from probability
 * Fair odds = 1 / probability
 */
function calculateFairOdds(probability: number): number {
  if (probability <= 0) return Infinity;
  return 1 / probability;
}

/**
 * Calculate value percentage
 * Value = (odds * probability - 1) * 100
 */
function calculateValue(odds: number, probability: number): number {
  if (odds <= 0 || probability <= 0) return 0;
  return (odds * probability - 1) * 100;
}

/**
 * Calculate Kelly Criterion bet size
 * Kelly = (odds * probability - 1) / (odds - 1)
 */
function calculateKelly(odds: number, probability: number): number {
  if (odds <= 1 || probability <= 0) return 0;
  const kelly = (odds * probability - 1) / (odds - 1);
  return Math.max(0, Math.min(kelly, 0.25)); // Cap at 25% for safety
}

/**
 * Main OddsComparison Component
 * Displays odds analysis with value indicators and ROI/Kelly calculations
 */
export function OddsComparison({
  homeProb,
  drawProb,
  awayProb,
  homeTeam,
  awayTeam,
}: OddsComparisonProps) {
  const t = useTranslations("odds");
  const [selectedBookmakerOdds, setSelectedBookmakerOdds] = useState<Record<string, number>>({
    home: 0,
    draw: 0,
    away: 0,
  });
  const [stakeAmount, setStakeAmount] = useState<number>(10);
  const [bankroll, setBankroll] = useState<number>(1000);
  const [activeTab, setActiveTab] = useState<"comparison" | "roi" | "kelly">("comparison");

  // Build odds data
  const oddsData: OddsData[] = [
    {
      outcome: "home",
      label: t("outcomes.homeWin", { team: homeTeam }),
      probability: homeProb,
      fairOdds: calculateFairOdds(homeProb),
      bookmakerOdds: selectedBookmakerOdds.home || undefined,
    },
    {
      outcome: "draw",
      label: t("outcomes.draw"),
      probability: drawProb,
      fairOdds: calculateFairOdds(drawProb),
      bookmakerOdds: selectedBookmakerOdds.draw || undefined,
    },
    {
      outcome: "away",
      label: t("outcomes.awayWin", { team: awayTeam }),
      probability: awayProb,
      fairOdds: calculateFairOdds(awayProb),
      bookmakerOdds: selectedBookmakerOdds.away || undefined,
    },
  ];

  // Calculate values for each outcome
  const oddsDataWithValues = oddsData.map((data) => ({
    ...data,
    valuePercentage: data.bookmakerOdds ? calculateValue(data.bookmakerOdds, data.probability) : undefined,
    hasValue: data.bookmakerOdds ? data.bookmakerOdds * data.probability > 1 : undefined,
  }));

  // Calculate ROI
  const selectedOuts = oddsDataWithValues.filter((o) => o.bookmakerOdds && o.bookmakerOdds > 0);
  let totalProfit = 0;
  if (selectedOuts.length > 0) {
    selectedOuts.forEach((out) => {
      if (out.bookmakerOdds) {
        const profit = stakeAmount * (out.bookmakerOdds - 1) * out.probability;
        totalProfit += profit;
      }
    });
  }
  const roi = selectedOuts.length > 0 ? (totalProfit / stakeAmount) * 100 : 0;

  // Calculate Kelly sizes for each outcome
  const kellyData = oddsDataWithValues.map((data) => ({
    ...data,
    kellySize: data.bookmakerOdds ? calculateKelly(data.bookmakerOdds, data.probability) : 0,
  }));

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 sm:p-6 border-b border-dark-700">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-5 h-5 text-primary-400" />
          <h2 className="text-lg sm:text-2xl font-bold text-white">{t("title")}</h2>
        </div>
        <p className="text-sm text-dark-400">
          {t("description")}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-dark-700 bg-dark-900/30">
        <button
          onClick={() => setActiveTab("comparison")}
          className={cn(
            "flex-1 px-4 py-3 font-semibold text-sm transition-colors",
            activeTab === "comparison"
              ? "text-primary-400 border-b-2 border-primary-400 bg-primary-500/5"
              : "text-dark-400 hover:text-dark-300"
          )}
        >
          {t("tabs.comparison")}
        </button>
        <button
          onClick={() => setActiveTab("roi")}
          className={cn(
            "flex-1 px-4 py-3 font-semibold text-sm transition-colors",
            activeTab === "roi"
              ? "text-primary-400 border-b-2 border-primary-400 bg-primary-500/5"
              : "text-dark-400 hover:text-dark-300"
          )}
        >
          {t("tabs.roi")}
        </button>
        <button
          onClick={() => setActiveTab("kelly")}
          className={cn(
            "flex-1 px-4 py-3 font-semibold text-sm transition-colors",
            activeTab === "kelly"
              ? "text-primary-400 border-b-2 border-primary-400 bg-primary-500/5"
              : "text-dark-400 hover:text-dark-300"
          )}
        >
          {t("tabs.kelly")}
        </button>
      </div>

      {/* Content */}
      <div className="p-4 sm:p-6">
        {activeTab === "comparison" && (
          <OddsComparisonTab
            oddsData={oddsDataWithValues}
            onOddsChange={(outcome, value) => setSelectedBookmakerOdds(prev => ({ ...prev, [outcome]: value }))}
            translations={{
              ourProbability: t("labels.ourProbability"),
              fairOdds: t("labels.fairOdds"),
              bookmakerOdds: t("labels.bookmakerOdds"),
              value: t("labels.value"),
              hasValue: t("labels.hasValue"),
              noValue: t("labels.noValue"),
              fairOddsTitle: t("formulas.fairOddsTitle"),
              fairOddsDesc: t("formulas.fairOddsDesc"),
              valueTitle: t("formulas.valueTitle"),
              valueDesc: t("formulas.valueDesc"),
            }}
          />
        )}
        {activeTab === "roi" && (
          <ROITab
            oddsData={oddsDataWithValues}
            stakeAmount={stakeAmount}
            setStakeAmount={setStakeAmount}
            totalProfit={totalProfit}
            roi={roi}
            translations={{
              stakeAmount: t("roi.stakeAmount"),
              potentialProfit: t("roi.potentialProfit"),
              breakdown: t("roi.breakdown"),
              noOddsEntered: t("roi.noOddsEntered"),
              noOddsHint: t("roi.noOddsHint"),
            }}
          />
        )}
        {activeTab === "kelly" && (
          <KellyTab
            kellyData={kellyData}
            bankroll={bankroll}
            setBankroll={setBankroll}
            translations={{
              bankrollTotal: t("kelly.bankrollTotal"),
              bankrollHint: t("kelly.bankrollHint"),
              formula: t("kelly.formula"),
              formulaDesc: t("kelly.formulaDesc"),
              formulaExplanation: t("kelly.formulaExplanation"),
              recommendedBets: t("kelly.recommendedBets"),
              optimalBet: t("kelly.optimalBet"),
              ofBankroll: t("kelly.ofBankroll"),
              probability: t("kelly.probability"),
              odds: t("kelly.odds"),
              value: t("labels.value"),
              noOddsEntered: t("kelly.noOddsEntered"),
              noOddsHint: t("kelly.noOddsHint"),
              safetyNotes: t("kelly.safetyNotes"),
              safetyNote1: t("kelly.safetyNote1"),
              safetyNote2: t("kelly.safetyNote2"),
              safetyNote3: t("kelly.safetyNote3"),
            }}
          />
        )}
      </div>
    </div>
  );
}

interface ComparisonTranslations {
  ourProbability: string;
  fairOdds: string;
  bookmakerOdds: string;
  value: string;
  hasValue: string;
  noValue: string;
  fairOddsTitle: string;
  fairOddsDesc: string;
  valueTitle: string;
  valueDesc: string;
}

/**
 * Odds Comparison Tab Component
 */
function OddsComparisonTab({
  oddsData,
  onOddsChange,
  translations,
}: {
  oddsData: OddsData[];
  onOddsChange: (outcome: string, value: number) => void;
  translations: ComparisonTranslations;
}) {
  return (
    <div className="space-y-4">
      {oddsData.map((data) => (
        <OddsComparisonCard
          key={data.outcome}
          data={data}
          onOddsChange={(value) => onOddsChange(data.outcome, value)}
          translations={translations}
        />
      ))}

      {/* Legend */}
      <div className="mt-6 p-4 bg-dark-700/30 rounded-lg space-y-2 text-sm">
        <div className="flex items-start gap-2">
          <CheckCircle className="w-4 h-4 text-primary-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-primary-300 font-semibold">{translations.fairOddsTitle}</p>
            <p className="text-dark-400 text-xs">{translations.fairOddsDesc}</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <CheckCircle className="w-4 h-4 text-accent-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-accent-300 font-semibold">{translations.valueTitle}</p>
            <p className="text-dark-400 text-xs">{translations.valueDesc}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Individual Odds Comparison Card
 */
function OddsComparisonCard({
  data,
  onOddsChange,
  translations,
}: {
  data: OddsData;
  onOddsChange: (value: number) => void;
  translations: ComparisonTranslations;
}) {
  const colorMap: Record<string, "primary" | "yellow" | "accent"> = {
    home: "primary",
    draw: "yellow",
    away: "accent",
  };

  const color = colorMap[data.outcome] || "primary";
  const colorClasses: Record<"primary" | "yellow" | "accent", { bg: string; border: string; text: string; barBg: string }> = {
    primary: {
      bg: "bg-primary-500/10",
      border: "border-primary-500/30",
      text: "text-primary-400",
      barBg: "bg-primary-500",
    },
    yellow: {
      bg: "bg-yellow-500/10",
      border: "border-yellow-500/30",
      text: "text-yellow-400",
      barBg: "bg-yellow-500",
    },
    accent: {
      bg: "bg-accent-500/10",
      border: "border-accent-500/30",
      text: "text-accent-400",
      barBg: "bg-accent-500",
    },
  };

  const classes = colorClasses[color];

  return (
    <div className={cn("rounded-lg border p-4 space-y-3", classes.bg, classes.border)}>
      {/* Title */}
      <div className="flex items-center justify-between">
        <h3 className={cn("font-semibold", classes.text)}>{data.label}</h3>
        <div className="text-right">
          <p className={cn("text-lg font-bold", classes.text)}>
            {Math.round(data.probability * 100)}%
          </p>
          <p className="text-xs text-dark-400">{translations.ourProbability}</p>
        </div>
      </div>

      {/* Probability Bar */}
      <div className="space-y-1">
        <div className={cn("h-2.5 rounded-full overflow-hidden bg-dark-700")}>
          <div
            className={cn("h-full rounded-full", classes.barBg)}
            style={{ width: `${Math.min(data.probability * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Odds Grid */}
      <div className="grid grid-cols-3 gap-3">
        {/* Fair Odds */}
        <div className="bg-dark-800 rounded p-3 text-center">
          <p className="text-xs text-dark-400 mb-1">{translations.fairOdds}</p>
          <p className={cn("font-bold text-lg", classes.text)}>
            {data.fairOdds === Infinity ? "∞" : data.fairOdds.toFixed(2)}
          </p>
        </div>

        {/* Bookmaker Odds Input */}
        <div className="bg-dark-800 rounded p-3">
          <p className="text-xs text-dark-400 mb-1">{translations.bookmakerOdds}</p>
          <input
            type="number"
            step="0.01"
            min="1"
            placeholder="Ex: 2.50"
            value={data.bookmakerOdds ? data.bookmakerOdds : ""}
            onChange={(e) => onOddsChange(e.target.value ? parseFloat(e.target.value) : 0)}
            className={cn(
              "w-full bg-dark-700 text-white rounded px-2 py-1 text-sm text-center border",
              "focus:outline-none focus:border-primary-500/50",
              data.bookmakerOdds ? "border-primary-500/30" : "border-dark-600"
            )}
          />
        </div>

        {/* Value Indicator */}
        {data.bookmakerOdds && data.bookmakerOdds > 0 ? (
          <div
            className={cn(
              "rounded p-3 text-center",
              data.hasValue ? "bg-primary-500/20" : "bg-red-500/20"
            )}
          >
            <p className="text-xs text-dark-400 mb-1">{translations.value}</p>
            <p
              className={cn(
                "font-bold text-lg",
                data.hasValue ? "text-primary-400" : "text-red-400"
              )}
            >
              {data.valuePercentage !== undefined ? `${data.valuePercentage > 0 ? "+" : ""}${data.valuePercentage.toFixed(1)}%` : "-"}
            </p>
            <p className={cn("text-xs font-semibold", data.hasValue ? "text-primary-300" : "text-red-300")}>
              {data.hasValue ? `✓ ${translations.hasValue}` : `✗ ${translations.noValue}`}
            </p>
          </div>
        ) : (
          <div className="bg-dark-700/30 rounded p-3 text-center">
            <p className="text-xs text-dark-400">{translations.value}</p>
            <p className="text-dark-500 text-sm mt-2">-</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface ROITranslations {
  stakeAmount: string;
  potentialProfit: string;
  breakdown: string;
  noOddsEntered: string;
  noOddsHint: string;
}

/**
 * ROI Calculator Tab
 */
function ROITab({
  oddsData,
  stakeAmount,
  setStakeAmount,
  totalProfit,
  roi,
  translations,
}: {
  oddsData: OddsData[];
  stakeAmount: number;
  setStakeAmount: (value: number) => void;
  totalProfit: number;
  roi: number;
  translations: ROITranslations;
}) {
  const selectedOdds = oddsData.filter((o) => o.bookmakerOdds && o.bookmakerOdds > 0);

  return (
    <div className="space-y-4">
      {/* Stake Input */}
      <div className="bg-dark-700/50 rounded-lg p-4">
        <label className="block text-sm font-semibold text-dark-300 mb-2">
          {translations.stakeAmount}
        </label>
        <div className="relative">
          <DollarSign className="absolute left-3 top-3 w-5 h-5 text-dark-400" />
          <input
            type="number"
            step="1"
            min="0"
            value={stakeAmount}
            onChange={(e) => setStakeAmount(parseFloat(e.target.value) || 0)}
            className="w-full bg-dark-800 text-white rounded-lg px-10 py-3 border border-dark-600 focus:outline-none focus:border-primary-500/50"
          />
        </div>
      </div>

      {/* ROI Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-primary-500/10 border border-primary-500/30 rounded-lg p-4 text-center">
          <p className="text-sm text-dark-300 mb-1">{translations.potentialProfit}</p>
          <p className={cn("text-2xl font-bold", totalProfit >= 0 ? "text-primary-400" : "text-red-400")}>
            {totalProfit >= 0 ? "+" : ""}{totalProfit.toFixed(2)} €
          </p>
        </div>

        <div className="bg-accent-500/10 border border-accent-500/30 rounded-lg p-4 text-center">
          <p className="text-sm text-dark-300 mb-1">ROI</p>
          <p className={cn("text-2xl font-bold", roi >= 0 ? "text-accent-400" : "text-red-400")}>
            {roi >= 0 ? "+" : ""}{roi.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Breakdown */}
      {selectedOdds.length > 0 && (
        <div className="bg-dark-700/30 rounded-lg p-4 space-y-3">
          <h4 className="font-semibold text-white text-sm">{translations.breakdown}</h4>
          {selectedOdds.map((odd) => {
            const profit = stakeAmount * (odd.bookmakerOdds! - 1) * odd.probability;
            const oddsRoi = (profit / stakeAmount) * 100;
            return (
              <div key={odd.outcome} className="flex items-center justify-between text-sm p-2 bg-dark-800/50 rounded">
                <span className="text-dark-300">{odd.label}</span>
                <div className="text-right">
                  <p className={cn("font-semibold", profit >= 0 ? "text-primary-400" : "text-red-400")}>
                    {profit >= 0 ? "+" : ""}{profit.toFixed(2)} €
                  </p>
                  <p className="text-xs text-dark-400">
                    {oddsRoi >= 0 ? "+" : ""}{oddsRoi.toFixed(1)}%
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedOdds.length === 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-yellow-300">{translations.noOddsEntered}</p>
              <p className="text-xs text-yellow-200 mt-1">
                {translations.noOddsHint}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface KellyTranslations {
  bankrollTotal: string;
  bankrollHint: string;
  formula: string;
  formulaDesc: string;
  formulaExplanation: string;
  recommendedBets: string;
  optimalBet: string;
  ofBankroll: string;
  probability: string;
  odds: string;
  value: string;
  noOddsEntered: string;
  noOddsHint: string;
  safetyNotes: string;
  safetyNote1: string;
  safetyNote2: string;
  safetyNote3: string;
}

/**
 * Kelly Criterion Calculator Tab
 */
function KellyTab({
  kellyData,
  bankroll,
  setBankroll,
  translations,
}: {
  kellyData: (OddsData & { kellySize: number })[];
  bankroll: number;
  setBankroll: (value: number) => void;
  translations: KellyTranslations;
}) {
  const selectedKelly = kellyData.filter((k) => k.bookmakerOdds && k.bookmakerOdds > 0);

  return (
    <div className="space-y-4">
      {/* Bankroll Input */}
      <div className="bg-dark-700/50 rounded-lg p-4">
        <label className="block text-sm font-semibold text-dark-300 mb-2">
          {translations.bankrollTotal}
        </label>
        <div className="relative">
          <DollarSign className="absolute left-3 top-3 w-5 h-5 text-dark-400" />
          <input
            type="number"
            step="10"
            min="0"
            value={bankroll}
            onChange={(e) => setBankroll(parseFloat(e.target.value) || 0)}
            className="w-full bg-dark-800 text-white rounded-lg px-10 py-3 border border-dark-600 focus:outline-none focus:border-primary-500/50"
          />
        </div>
        <p className="text-xs text-dark-400 mt-2">
          {translations.bankrollHint}
        </p>
      </div>

      {/* Kelly Formula Info */}
      <div className="bg-primary-500/10 border border-primary-500/30 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <Zap className="w-5 h-5 text-primary-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-primary-300 mb-1">{translations.formula}</p>
            <p className="text-sm text-primary-200">
              {translations.formulaDesc}
            </p>
            <p className="text-xs text-primary-300 mt-2">
              {translations.formulaExplanation}
            </p>
          </div>
        </div>
      </div>

      {/* Kelly Bets */}
      {selectedKelly.length > 0 ? (
        <div className="space-y-3">
          <h4 className="font-semibold text-white">{translations.recommendedBets}</h4>
          {selectedKelly.map((kelly) => {
            const betSize = kelly.kellySize * bankroll;
            const colorMap = {
              home: "primary",
              draw: "yellow",
              away: "accent",
            };
            const color = colorMap[kelly.outcome as keyof typeof colorMap];
            const bgColor = color === "primary" ? "bg-primary-500/10" : color === "yellow" ? "bg-yellow-500/10" : "bg-accent-500/10";
            const borderColor = color === "primary" ? "border-primary-500/30" : color === "yellow" ? "border-yellow-500/30" : "border-accent-500/30";
            const textColor = color === "primary" ? "text-primary-400" : color === "yellow" ? "text-yellow-400" : "text-accent-400";

            return (
              <div key={kelly.outcome} className={cn("rounded-lg border p-4", bgColor, borderColor)}>
                <div className="flex items-center justify-between mb-2">
                  <p className="font-semibold text-white">{kelly.label}</p>
                  <p className={cn("text-sm font-bold", textColor)}>
                    {(kelly.kellySize * 100).toFixed(1)}% {translations.ofBankroll}
                  </p>
                </div>

                {/* Bet Size and Visualization */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-dark-300">{translations.optimalBet}</p>
                    <p className={cn("font-bold text-lg", textColor)}>
                      {betSize.toFixed(2)} €
                    </p>
                  </div>

                  {/* Progress Bar */}
                  <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                    <div
                      className={cn("h-full rounded-full", {
                        "bg-primary-500": color === "primary",
                        "bg-yellow-500": color === "yellow",
                        "bg-accent-500": color === "accent",
                      })}
                      style={{ width: `${Math.min(kelly.kellySize * 100, 100)}%` }}
                    />
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-2 text-xs mt-2">
                    <div>
                      <p className="text-dark-400">{translations.probability}</p>
                      <p className="font-semibold text-white">{Math.round(kelly.probability * 100)}%</p>
                    </div>
                    <div>
                      <p className="text-dark-400">{translations.odds}</p>
                      <p className="font-semibold text-white">{kelly.bookmakerOdds?.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-dark-400">{translations.value}</p>
                      <p className="font-semibold text-white">
                        {kelly.valuePercentage ? `+${kelly.valuePercentage.toFixed(1)}%` : "-"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-yellow-300">{translations.noOddsEntered}</p>
              <p className="text-xs text-yellow-200 mt-1">
                {translations.noOddsHint}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Kelly Safety Notes */}
      <div className="bg-dark-700/30 rounded-lg p-4 space-y-2 text-xs text-dark-400">
        <p className="font-semibold text-dark-300">{translations.safetyNotes}</p>
        <ul className="space-y-1 list-disc list-inside">
          <li>{translations.safetyNote1}</li>
          <li>{translations.safetyNote2}</li>
          <li>{translations.safetyNote3}</li>
        </ul>
      </div>
    </div>
  );
}
