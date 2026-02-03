"use client";

import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useTranslations } from "next-intl";

interface TeamStrengthIndexProps {
  homeTeam: string;
  awayTeam: string;
  homeElo?: number;
  awayElo?: number;
  homeForm?: string;
  awayForm?: string;
  className?: string;
}

const ELO_MIN = 1200;
const ELO_MAX = 2000;

function getStrengthPercentage(elo: number): number {
  return Math.min(100, Math.max(0, ((elo - ELO_MIN) / (ELO_MAX - ELO_MIN)) * 100));
}

type StrengthLabelKey = "elite" | "strong" | "aboveAverage" | "average" | "weak";

function getStrengthLabelKey(elo: number): StrengthLabelKey {
  if (elo >= 1800) return "elite";
  if (elo >= 1650) return "strong";
  if (elo >= 1500) return "aboveAverage";
  if (elo >= 1350) return "average";
  return "weak";
}

function getStrengthColor(elo: number): string {
  if (elo >= 1800) return "from-emerald-500 to-emerald-400";
  if (elo >= 1650) return "from-green-500 to-green-400";
  if (elo >= 1500) return "from-blue-500 to-blue-400";
  if (elo >= 1350) return "from-yellow-500 to-yellow-400";
  return "from-red-500 to-red-400";
}

function FormBadges({ form }: { form: string }) {
  if (!form) return null;
  return (
    <div className="flex gap-0.5">
      {form.split("").slice(-5).map((result, idx) => (
        <span
          key={idx}
          className={cn(
            "w-5 h-5 rounded text-xs font-bold flex items-center justify-center",
            result === "W" && "bg-green-500/20 text-green-500",
            result === "D" && "bg-yellow-500/20 text-yellow-500",
            result === "L" && "bg-red-500/20 text-red-500"
          )}
        >
          {result}
        </span>
      ))}
    </div>
  );
}

function TeamStrengthBar({ team, elo, form, isHome, t }: { team: string; elo: number; form?: string; isHome: boolean; t: (key: string) => string }) {
  const percentage = getStrengthPercentage(elo);
  const labelKey = getStrengthLabelKey(elo);
  const label = t(labelKey);
  const colorClass = getStrengthColor(elo);

  return (
    <div className={cn("space-y-2", isHome ? "text-left" : "text-right")}>
      <div className="flex items-center justify-between">
        <div className={cn("flex items-center gap-2", !isHome && "flex-row-reverse")}>
          <span className="text-sm font-semibold text-gray-900 dark:text-white truncate max-w-[120px]">{team}</span>
          <span className={cn(
            "text-xs px-2 py-0.5 rounded-full font-medium",
            elo >= 1650 ? "bg-green-500/20 text-green-600 dark:text-green-400" :
            elo >= 1400 ? "bg-blue-500/20 text-blue-600 dark:text-blue-400" :
            "bg-yellow-500/20 text-yellow-600 dark:text-yellow-400"
          )}>{label}</span>
        </div>
        <span className="text-xs font-mono text-gray-500 dark:text-slate-400">{elo}</span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full bg-gradient-to-r transition-all duration-500", colorClass, !isHome && "ml-auto")} style={{ width: `${percentage}%` }} />
      </div>
      {form && <div className={cn("flex", isHome ? "justify-start" : "justify-end")}><FormBadges form={form} /></div>}
    </div>
  );
}

export function TeamStrengthIndex({ homeTeam, awayTeam, homeElo = 1500, awayElo = 1500, homeForm, awayForm, className }: TeamStrengthIndexProps) {
  const t = useTranslations("components.teamStrength");
  const eloDiff = homeElo - awayElo;
  const advantage = Math.abs(eloDiff) > 50 ? (eloDiff > 0 ? "home" : "away") : "neutral";

  return (
    <div className={cn("bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4", className)}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary-500" />
          {t("title")}
        </h3>
        <div className="flex items-center gap-1.5">
          {advantage === "home" && <><TrendingUp className="w-4 h-4 text-green-500" /><span className="text-xs text-green-600 dark:text-green-400 font-medium">+{eloDiff} {t("home")}</span></>}
          {advantage === "away" && <><TrendingDown className="w-4 h-4 text-red-500" /><span className="text-xs text-red-600 dark:text-red-400 font-medium">{eloDiff} {t("away")}</span></>}
          {advantage === "neutral" && <><Minus className="w-4 h-4 text-gray-400" /><span className="text-xs text-gray-500 dark:text-slate-400 font-medium">{t("balanced")}</span></>}
        </div>
      </div>
      <div className="space-y-4">
        <TeamStrengthBar team={homeTeam} elo={homeElo} form={homeForm} isHome t={t} />
        <div className="relative py-2">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200 dark:border-slate-700" /></div>
          <div className="relative flex justify-center"><span className="bg-white dark:bg-slate-800 px-2 text-xs text-gray-500 dark:text-slate-400">VS</span></div>
        </div>
        <TeamStrengthBar team={awayTeam} elo={awayElo} form={awayForm} isHome={false} t={t} />
      </div>
      <div className="mt-4 pt-3 border-t border-gray-100 dark:border-slate-700/50">
        <div className="flex justify-between text-xs text-gray-400 dark:text-slate-500"><span>{t("weak")}</span><span>{t("average")}</span><span>{t("elite")}</span></div>
        <div className="h-1.5 mt-1 rounded-full bg-gradient-to-r from-red-500 via-yellow-500 via-blue-500 to-emerald-500" />
      </div>
    </div>
  );
}
