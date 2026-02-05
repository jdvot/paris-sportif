"use client";

import { useState } from "react";
import {
  Target,
  TrendingUp,
  CheckCircle,
  BarChart3,
  AlertTriangle,
  Info,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useGetCalibration } from "@/lib/hooks/useCalibration";

type PeriodDays = 30 | 90 | 180 | 365;

export default function CalibrationPage() {
  const t = useTranslations("calibration");
  const [days, setDays] = useState<PeriodDays>(90);

  const { data: response, isLoading, error } = useGetCalibration(days);
  const calibration = response?.data;

  const periods: { value: PeriodDays; label: string }[] = [
    { value: 30, label: t("filters.last30Days") },
    { value: 90, label: t("filters.last90Days") },
    { value: 180, label: t("filters.last180Days") },
    { value: 365, label: t("filters.lastYear") },
  ];

  // Calculate color based on calibration error
  const getCalibrationColor = (error: number) => {
    if (error < 0.05) return "text-green-600 dark:text-green-400";
    if (error < 0.10) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 0.55) return "text-green-600 dark:text-green-400";
    if (accuracy >= 0.45) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getOverconfidenceColor = (overconf: number) => {
    if (overconf <= 0.03) return "bg-green-100 dark:bg-green-500/20 text-green-600 dark:text-green-400";
    if (overconf <= 0.08) return "bg-yellow-100 dark:bg-yellow-500/20 text-yellow-600 dark:text-yellow-400";
    return "bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Target className="w-8 h-8 text-primary-500" />
            {t("title")}
          </h1>
          <p className="text-gray-600 dark:text-dark-400 mt-1">{t("subtitle")}</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(parseInt(e.target.value) as PeriodDays)}
          className="px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg text-sm"
        >
          {periods.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-100 dark:bg-dark-700 rounded-xl animate-pulse" />
            ))}
          </div>
          <div className="h-64 bg-gray-100 dark:bg-dark-700 rounded-xl animate-pulse" />
        </div>
      ) : error || !calibration ? (
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {t("empty")}
          </h3>
          <p className="text-gray-600 dark:text-dark-400">{t("emptyHint")}</p>
        </div>
      ) : (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 text-center">
              <CheckCircle className="w-6 h-6 text-primary-500 mx-auto mb-2" />
              <p className={cn("text-2xl font-bold", getAccuracyColor(calibration.overall_accuracy))}>
                {(calibration.overall_accuracy * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-600 dark:text-dark-400">{t("overallAccuracy")}</p>
            </div>
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 text-center">
              <Target className="w-6 h-6 text-primary-500 mx-auto mb-2" />
              <p className={cn("text-2xl font-bold", getCalibrationColor(calibration.overall_calibration_error))}>
                {(calibration.overall_calibration_error * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-600 dark:text-dark-400">
                {t("calibrationError")}
                <span className="ml-1 text-gray-400">({t("calibrationErrorHint")})</span>
              </p>
            </div>
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 text-center">
              <BarChart3 className="w-6 h-6 text-primary-500 mx-auto mb-2" />
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {calibration.total_verified}
              </p>
              <p className="text-xs text-gray-600 dark:text-dark-400">{t("totalVerified")}</p>
            </div>
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 text-center">
              <TrendingUp className="w-6 h-6 text-primary-500 mx-auto mb-2" />
              <p className="text-lg font-bold text-gray-900 dark:text-white">{calibration.period}</p>
              <p className="text-xs text-gray-600 dark:text-dark-400">{t("period")}</p>
            </div>
          </div>

          {/* Calibration by Confidence */}
          <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {t("byConfidence")}
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-dark-700">
                    <th className="text-left py-2 px-2 text-gray-600 dark:text-dark-400">
                      {t("bucket.confidenceRange")}
                    </th>
                    <th className="text-center py-2 px-2 text-gray-600 dark:text-dark-400">
                      {t("bucket.predicted")}
                    </th>
                    <th className="text-center py-2 px-2 text-gray-600 dark:text-dark-400">
                      {t("bucket.actual")}
                    </th>
                    <th className="text-center py-2 px-2 text-gray-600 dark:text-dark-400">
                      {t("bucket.count")}
                    </th>
                    <th className="text-center py-2 px-2 text-gray-600 dark:text-dark-400">
                      {t("bucket.difference")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {calibration.by_confidence.map((bucket) => (
                    <tr key={bucket.confidence_range} className="border-b border-gray-100 dark:border-dark-700/50">
                      <td className="py-2 px-2 font-medium text-gray-900 dark:text-white">
                        {bucket.confidence_range}
                      </td>
                      <td className="py-2 px-2 text-center text-gray-900 dark:text-white">
                        {(bucket.predicted_confidence * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-2 text-center">
                        <span className={getAccuracyColor(bucket.actual_win_rate)}>
                          {(bucket.actual_win_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-2 px-2 text-center text-gray-600 dark:text-dark-400">
                        {bucket.count}
                      </td>
                      <td className="py-2 px-2 text-center">
                        <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", getOverconfidenceColor(Math.abs(bucket.overconfidence)))}>
                          {bucket.overconfidence > 0 ? "+" : ""}
                          {(bucket.overconfidence * 100).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Visual Calibration Chart */}
            <div className="mt-6">
              <div className="flex items-center gap-4 mb-2 text-xs text-gray-500 dark:text-dark-400">
                <div className="flex items-center gap-1">
                  <div className="w-3 h-0.5 bg-gray-400" />
                  {t("chart.perfectCalibration")}
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-primary-500 rounded-full" />
                  {t("chart.actualCalibration")}
                </div>
              </div>
              <div className="relative h-48 border border-gray-200 dark:border-dark-700 rounded-lg overflow-hidden">
                {/* Grid lines */}
                <div className="absolute inset-0">
                  {[0.25, 0.5, 0.75].map((line) => (
                    <div
                      key={line}
                      className="absolute w-full border-t border-gray-100 dark:border-dark-700/50"
                      style={{ top: `${(1 - line) * 100}%` }}
                    />
                  ))}
                </div>
                {/* Perfect calibration line */}
                <div
                  className="absolute w-full h-0.5 bg-gray-300 dark:bg-dark-600 origin-bottom-left"
                  style={{
                    transform: "rotate(-45deg)",
                    transformOrigin: "0% 100%",
                    width: "141%",
                    bottom: 0,
                    left: 0,
                  }}
                />
                {/* Data points */}
                {calibration.by_confidence.map((bucket) => {
                  const x = bucket.predicted_confidence;
                  const y = bucket.actual_win_rate;
                  return (
                    <div
                      key={bucket.confidence_range}
                      className="absolute w-3 h-3 bg-primary-500 rounded-full transform -translate-x-1/2 -translate-y-1/2 hover:scale-150 transition-transform"
                      style={{
                        left: `${x * 100}%`,
                        bottom: `${y * 100}%`,
                      }}
                      title={`${bucket.confidence_range}: ${(y * 100).toFixed(1)}% actual`}
                    />
                  );
                })}
              </div>
              <div className="flex justify-between mt-1 text-xs text-gray-500 dark:text-dark-400">
                <span>50%</span>
                <span>{t("chart.confidence")}</span>
                <span>100%</span>
              </div>
            </div>
          </div>

          {/* By Bet Type */}
          <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {t("byBetType")}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {calibration.by_bet_type.map((bt) => (
                <div
                  key={bt.bet_type}
                  className="border border-gray-200 dark:border-dark-700 rounded-lg p-4"
                >
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    {t(`betTypes.${bt.bet_type}`)}
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-dark-400">{t("overallAccuracy")}</span>
                      <span className={cn("font-medium", getAccuracyColor(bt.accuracy))}>
                        {(bt.accuracy * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-dark-400">{t("totalVerified")}</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {bt.total_predictions}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-dark-400">{t("bucket.predicted")}</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {(bt.avg_confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* By Competition */}
          <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {t("byCompetition")}
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-dark-700">
                    <th className="text-left py-2 px-2 text-gray-600 dark:text-dark-400">Competition</th>
                    <th className="text-center py-2 px-2 text-gray-600 dark:text-dark-400">
                      {t("bucket.count")}
                    </th>
                    <th className="text-center py-2 px-2 text-gray-600 dark:text-dark-400">
                      {t("bucket.actual")}
                    </th>
                    <th className="text-center py-2 px-2 text-gray-600 dark:text-dark-400">
                      {t("bucket.predicted")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(calibration.by_competition)
                    .sort((a, b) => b[1].total - a[1].total)
                    .map(([comp, data]) => (
                      <tr key={comp} className="border-b border-gray-100 dark:border-dark-700/50">
                        <td className="py-2 px-2 font-medium text-gray-900 dark:text-white">{comp}</td>
                        <td className="py-2 px-2 text-center text-gray-600 dark:text-dark-400">
                          {data.total}
                        </td>
                        <td className="py-2 px-2 text-center">
                          <span className={getAccuracyColor(data.accuracy)}>
                            {(data.accuracy * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-2 px-2 text-center text-gray-600 dark:text-dark-400">
                          {(data.avg_confidence * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Info Banner */}
      <div className="bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30 rounded-xl p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-blue-800 dark:text-blue-300">{t("infoBanner")}</p>
      </div>
    </div>
  );
}
