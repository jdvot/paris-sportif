"use client";

import { Newspaper, UserX, TrendingUp, TrendingDown, Minus, Loader2, AlertTriangle, Info, Cloud, CloudRain, Sun, Wind, Thermometer, MessageSquare, Database, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEnrichMatch } from "@/lib/api/endpoints/rag/rag";
import type { TeamContext, WeatherInfo } from "@/lib/api/models";
import { format } from "date-fns";
import { useTranslations, useLocale } from "next-intl";
import { useAuth } from "@/hooks/useAuth";

interface RAGContextProps {
  homeTeam: string;
  awayTeam: string;
  competition: string;
  matchDate: Date;
  className?: string;
}

function SentimentBadge({ label, score, neutralLabel }: { label?: string; score?: number; neutralLabel: string }) {
  const normalizedLabel = label?.toLowerCase() || "neutral";

  const config = {
    positive: {
      icon: TrendingUp,
      bg: "bg-green-100 dark:bg-green-500/20",
      text: "text-green-700 dark:text-green-300",
      border: "border-green-300 dark:border-green-500/40",
    },
    negative: {
      icon: TrendingDown,
      bg: "bg-red-100 dark:bg-red-500/20",
      text: "text-red-700 dark:text-red-300",
      border: "border-red-300 dark:border-red-500/40",
    },
    neutral: {
      icon: Minus,
      bg: "bg-gray-100 dark:bg-gray-500/20",
      text: "text-gray-700 dark:text-gray-300",
      border: "border-gray-300 dark:border-gray-500/40",
    },
  };

  const style = config[normalizedLabel as keyof typeof config] || config.neutral;
  const Icon = style.icon;

  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-medium border",
      style.bg,
      style.text,
      style.border
    )}>
      <Icon className="w-3 h-3" />
      {label || neutralLabel}
    </span>
  );
}

interface WeatherTranslations {
  favorable: string;
  cold: string;
  hot: string;
  strongWind: string;
  likelyRain: string;
  normalConditions: string;
}

function WeatherSection({ weather, translations }: { weather: WeatherInfo; translations: WeatherTranslations }) {
  if (!weather.available) return null;

  const getWeatherIcon = () => {
    const desc = weather.description?.toLowerCase() || "";
    if (desc.includes("rain") || desc.includes("drizzle") || desc.includes("shower")) {
      return <CloudRain className="w-4 h-4 text-blue-500" />;
    }
    if (desc.includes("clear") || desc.includes("sun")) {
      return <Sun className="w-4 h-4 text-yellow-500" />;
    }
    return <Cloud className="w-4 h-4 text-gray-500" />;
  };

  const getImpactBadge = () => {
    if (!weather.impact || weather.impact === "favorable") {
      return (
        <span className="px-1.5 py-0.5 bg-green-100 dark:bg-green-500/20 border border-green-300 dark:border-green-500/40 rounded text-[10px] text-green-700 dark:text-green-300">
          {translations.favorable}
        </span>
      );
    }
    const impacts = weather.impact.split(",");
    return impacts.map((impact, i) => (
      <span
        key={i}
        className="px-1.5 py-0.5 bg-orange-100 dark:bg-orange-500/20 border border-orange-300 dark:border-orange-500/40 rounded text-[10px] text-orange-700 dark:text-orange-300"
      >
        {impact === "cold_conditions" ? translations.cold :
         impact === "hot_conditions" ? translations.hot :
         impact === "strong_wind" ? translations.strongWind :
         impact === "likely_rain" ? translations.likelyRain :
         impact}
      </span>
    ));
  };

  return (
    <div className="flex items-center gap-3 p-2 bg-gray-50 dark:bg-slate-700/40 rounded-lg">
      {getWeatherIcon()}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 text-xs text-gray-700 dark:text-slate-300">
          <span className="flex items-center gap-1">
            <Thermometer className="w-3 h-3" />
            {weather.temperature != null ? `${Math.round(weather.temperature)}°C` : "--"}
          </span>
          {weather.wind_speed != null && (
            <span className="flex items-center gap-1">
              <Wind className="w-3 h-3" />
              {Math.round(weather.wind_speed)} m/s
            </span>
          )}
          {weather.rain_probability != null && weather.rain_probability > 0 && (
            <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
              <CloudRain className="w-3 h-3" />
              {weather.rain_probability}%
            </span>
          )}
        </div>
        <div className="text-[10px] text-gray-500 dark:text-slate-400 mt-0.5">
          {weather.description || translations.normalConditions}
        </div>
      </div>
      <div className="flex flex-wrap gap-1">
        {getImpactBadge()}
      </div>
    </div>
  );
}

function TeamContextSection({ context, teamName, neutralLabel }: { context: TeamContext; teamName: string; neutralLabel: string }) {
  const hasNews = context.recent_news && context.recent_news.length > 0;
  const hasInjuries = context.injuries && context.injuries.length > 0;

  if (!hasNews && !hasInjuries) {
    return null;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-700 dark:text-slate-200 truncate max-w-[150px]">
          {teamName}
        </span>
        <SentimentBadge label={context.sentiment_label} score={context.sentiment_score} neutralLabel={neutralLabel} />
      </div>

      {/* Recent News */}
      {hasNews && (
        <div className="space-y-1">
          {context.recent_news!.slice(0, 2).map((news, i) => (
            <div
              key={i}
              className="flex items-start gap-1.5 text-[10px] sm:text-xs text-gray-600 dark:text-slate-400"
            >
              <Newspaper className="w-3 h-3 mt-0.5 flex-shrink-0 text-blue-500" />
              <span className="line-clamp-1">{news}</span>
            </div>
          ))}
        </div>
      )}

      {/* Injuries */}
      {hasInjuries && (
        <div className="flex flex-wrap gap-1">
          {context.injuries!.slice(0, 3).map((injury, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-100 dark:bg-red-500/20 border border-red-300 dark:border-red-500/40 rounded text-[10px] text-red-700 dark:text-red-300"
            >
              <UserX className="w-2.5 h-2.5" />
              {injury}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function RAGContext({
  homeTeam,
  awayTeam,
  competition,
  matchDate,
  className,
}: RAGContextProps) {
  const t = useTranslations("rag");
  const locale = useLocale();
  const { isPremium, loading: authLoading } = useAuth();

  const { data, isLoading, error } = useEnrichMatch(
    {
      home_team: homeTeam,
      away_team: awayTeam,
      competition: competition,
      match_date: format(matchDate, "yyyy-MM-dd"),
    },
    {
      query: {
        enabled: isPremium && !authLoading, // Only fetch for premium users
        staleTime: 5 * 60 * 1000, // 5 minutes
        retry: 1,
      },
    }
  );

  // Don't render anything for non-premium users
  if (!authLoading && !isPremium) {
    return null;
  }

  // Extract the actual data from the response
  const ragContext = data?.data;

  if (isLoading) {
    return (
      <div className={cn("flex items-center justify-center py-3", className)}>
        <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
        <span className="ml-2 text-xs text-gray-500 dark:text-slate-400">
          {t("loadingContext")}
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("flex items-center gap-2 py-2 text-xs text-orange-600 dark:text-orange-400", className)}>
        <AlertTriangle className="w-3.5 h-3.5" />
        <span>{t("notAvailable")}</span>
      </div>
    );
  }

  if (!ragContext) {
    return null;
  }

  const homeContext = ragContext.home_context;
  const awayContext = ragContext.away_context;
  const weather = ragContext.weather;

  // Check if there's any meaningful context to display
  const hasHomeContext = homeContext && (
    (homeContext.recent_news && homeContext.recent_news.length > 0) ||
    (homeContext.injuries && homeContext.injuries.length > 0)
  );
  const hasAwayContext = awayContext && (
    (awayContext.recent_news && awayContext.recent_news.length > 0) ||
    (awayContext.injuries && awayContext.injuries.length > 0)
  );
  const hasWeather = weather && weather.available;

  // Weather translations
  const weatherTranslations: WeatherTranslations = {
    favorable: t("weather.favorable"),
    cold: t("weather.cold"),
    hot: t("weather.hot"),
    strongWind: t("weather.strongWind"),
    likelyRain: t("weather.likelyRain"),
    normalConditions: t("weather.normalConditions"),
  };

  if (!hasHomeContext && !hasAwayContext && !hasWeather) {
    return (
      <div className={cn("flex items-center gap-2 py-2 text-xs text-gray-500 dark:text-slate-400", className)}>
        <Info className="w-3.5 h-3.5" />
        <span>{t("noRecentNews")}</span>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 dark:text-slate-300">
        <Newspaper className="w-3.5 h-3.5" />
        <span>{t("matchContext")}</span>
        {ragContext.is_derby && (
          <span className="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-500/20 border border-purple-300 dark:border-purple-500/40 rounded text-[10px] text-purple-700 dark:text-purple-300">
            {t("derby")}
          </span>
        )}
        {ragContext.match_importance && ragContext.match_importance !== "normal" && (
          <span className={cn(
            "px-1.5 py-0.5 rounded text-[10px] border",
            ragContext.match_importance === "high" || ragContext.match_importance === "critical"
              ? "bg-amber-100 dark:bg-amber-500/20 border-amber-300 dark:border-amber-500/40 text-amber-700 dark:text-amber-300"
              : "bg-gray-100 dark:bg-gray-500/20 border-gray-300 dark:border-gray-500/40 text-gray-700 dark:text-gray-300"
          )}>
            {ragContext.match_importance === "high" ? t("importance.high") :
             ragContext.match_importance === "critical" ? t("importance.critical") :
             ragContext.match_importance}
          </span>
        )}
      </div>

      {/* Weather Section */}
      {hasWeather && weather && (
        <WeatherSection weather={weather} translations={weatherTranslations} />
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {hasHomeContext && (
          <TeamContextSection context={homeContext} teamName={homeTeam} neutralLabel={t("neutral")} />
        )}
        {hasAwayContext && (
          <TeamContextSection context={awayContext} teamName={awayTeam} neutralLabel={t("neutral")} />
        )}
      </div>

      {/* Combined Analysis */}
      {ragContext.combined_analysis && (
        <div className="p-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-500/10 dark:to-indigo-500/10 rounded-lg border border-blue-200 dark:border-blue-500/30">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">{t("aiAnalysis")}</span>
          </div>
          <p className="text-xs text-gray-700 dark:text-slate-300 leading-relaxed">
            {ragContext.combined_analysis}
          </p>
        </div>
      )}

      {/* Sources & Metadata */}
      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-200 dark:border-slate-700/50">
        {/* Sources Used */}
        {ragContext.sources_used && ragContext.sources_used.length > 0 && (
          <div className="flex items-center gap-1.5">
            <Database className="w-3 h-3 text-gray-400 dark:text-slate-500" />
            <div className="flex flex-wrap gap-1">
              {ragContext.sources_used.map((source, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 bg-gray-100 dark:bg-slate-700/50 rounded text-[9px] text-gray-500 dark:text-slate-400"
                >
                  {source}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Enriched At */}
        {ragContext.enriched_at && (
          <div className="flex items-center gap-1 ml-auto">
            <Clock className="w-3 h-3 text-gray-400 dark:text-slate-500" />
            <span className="text-[9px] text-gray-400 dark:text-slate-500">
              {new Date(ragContext.enriched_at).toLocaleTimeString(locale === "fr" ? "fr-FR" : "en-US", { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
