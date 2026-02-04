"use client";

import { Newspaper, AlertTriangle, TrendingUp, Users, Clock, Loader2, Crown } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { useTranslations, useLocale } from "next-intl";
import { useAuth } from "@/hooks/useAuth";
import { useGetMatchContextApiV1VectorMatchContextGet } from "@/lib/api/endpoints/vector-store/vector-store";
import { cn } from "@/lib/utils";

interface MatchNewsContextProps {
  homeTeam: string;
  awayTeam: string;
}

const CATEGORY_CONFIG = {
  injuries: {
    icon: AlertTriangle,
    color: "text-red-500",
    bgColor: "bg-red-100 dark:bg-red-500/20",
  },
  transfers: {
    icon: Users,
    color: "text-blue-500",
    bgColor: "bg-blue-100 dark:bg-blue-500/20",
  },
  form: {
    icon: TrendingUp,
    color: "text-green-500",
    bgColor: "bg-green-100 dark:bg-green-500/20",
  },
  previews: {
    icon: Newspaper,
    color: "text-purple-500",
    bgColor: "bg-purple-100 dark:bg-purple-500/20",
  },
};

interface NewsItem {
  id: string;
  title: string;
  content?: string | null;
  published_at?: string | null;
  score: number;
}

interface TeamContext {
  team_name: string;
  injuries: NewsItem[];
  transfers: NewsItem[];
  form: NewsItem[];
  previews: NewsItem[];
}

function NewsCard({ item, locale }: { item: NewsItem; locale: string }) {
  const dateLocale = locale === "fr" ? fr : enUS;

  return (
    <div className="p-3 bg-gray-50 dark:bg-dark-700/50 rounded-lg">
      <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2">
        {item.title}
      </p>
      {item.published_at && (
        <p className="text-xs text-gray-500 dark:text-dark-500 mt-1 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {format(new Date(item.published_at), "d MMM", { locale: dateLocale })}
        </p>
      )}
    </div>
  );
}

function TeamNewsSection({
  context,
  locale,
  t,
}: {
  context: TeamContext;
  locale: string;
  t: (key: string) => string;
}) {
  const categories = [
    { key: "injuries", items: context.injuries },
    { key: "transfers", items: context.transfers },
    { key: "form", items: context.form },
    { key: "previews", items: context.previews },
  ] as const;

  const hasNews = categories.some((cat) => cat.items.length > 0);

  if (!hasNews) {
    return (
      <p className="text-sm text-gray-500 dark:text-dark-400 italic">
        {t("noNews")}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {categories.map(({ key, items }) => {
        if (items.length === 0) return null;
        const config = CATEGORY_CONFIG[key];
        const Icon = config.icon;

        return (
          <div key={key}>
            <h4 className="text-sm font-medium text-gray-700 dark:text-dark-300 flex items-center gap-2 mb-2">
              <span className={cn("p-1 rounded", config.bgColor)}>
                <Icon className={cn("w-3 h-3", config.color)} />
              </span>
              {t(`categories.${key}`)} ({items.length})
            </h4>
            <div className="space-y-2">
              {items.slice(0, 3).map((item) => (
                <NewsCard key={item.id} item={item} locale={locale} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function MatchNewsContext({ homeTeam, awayTeam }: MatchNewsContextProps) {
  const t = useTranslations("matchNews");
  const locale = useLocale();
  const { isPremium, loading: authLoading } = useAuth();

  const { data: response, isLoading, error } = useGetMatchContextApiV1VectorMatchContextGet(
    { home_team: homeTeam, away_team: awayTeam },
    {
      query: {
        enabled: isPremium && !authLoading,
      },
    }
  );

  if (authLoading) {
    return null;
  }

  if (!isPremium) {
    return (
      <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Newspaper className="w-5 h-5 text-primary-500" />
          {t("title")}
        </h3>
        <div className="bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-200 dark:border-primary-500/30 rounded-lg p-4 text-center">
          <Crown className="w-8 h-8 text-primary-500 mx-auto mb-2" />
          <p className="text-sm text-gray-700 dark:text-dark-300 mb-3">
            {t("premiumOnly")}
          </p>
          <Link
            href="/plans"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary-600 dark:text-primary-400 hover:underline"
          >
            {t("upgrade")}
          </Link>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Newspaper className="w-5 h-5 text-primary-500" />
          {t("title")}
        </h3>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
        </div>
      </div>
    );
  }

  if (error || response?.status !== 200) {
    return null;
  }

  const data = response.data;
  const homeContext = data.home_team as TeamContext | undefined;
  const awayContext = data.away_team as TeamContext | undefined;

  return (
    <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
        <Newspaper className="w-5 h-5 text-primary-500" />
        {t("title")}
        <span className="ml-auto px-2 py-0.5 bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300 text-xs font-medium rounded">
          Premium
        </span>
      </h3>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Home Team */}
        <div>
          <h4 className="font-medium text-gray-900 dark:text-white mb-3 pb-2 border-b border-gray-200 dark:border-dark-700">
            {homeTeam}
          </h4>
          {homeContext ? (
            <TeamNewsSection context={homeContext} locale={locale} t={t} />
          ) : (
            <p className="text-sm text-gray-500 dark:text-dark-400 italic">
              {t("noNews")}
            </p>
          )}
        </div>

        {/* Away Team */}
        <div>
          <h4 className="font-medium text-gray-900 dark:text-white mb-3 pb-2 border-b border-gray-200 dark:border-dark-700">
            {awayTeam}
          </h4>
          {awayContext ? (
            <TeamNewsSection context={awayContext} locale={locale} t={t} />
          ) : (
            <p className="text-sm text-gray-500 dark:text-dark-400 italic">
              {t("noNews")}
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-dark-700">
        <Link
          href="/search"
          className="text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
        >
          {t("searchMore")}
        </Link>
      </div>
    </div>
  );
}
