"use client";

import { useState, useEffect } from "react";
import { Newspaper, ExternalLink, Clock, AlertTriangle, TrendingUp, Users, Loader2, RefreshCw } from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { useLocale } from "next-intl";
import { cn } from "@/lib/utils";

interface NewsArticle {
  title: string;
  source: string;
  published_at: string | null;
  url: string | null;
  article_type: string;
  team_name: string | null;
}

interface NewsResponse {
  articles: NewsArticle[];
  total: number;
  fetched_at: string;
}

interface NewsFeedProps {
  team?: string;
  competition?: string;
  limit?: number;
  showTitle?: boolean;
  className?: string;
}

const TYPE_CONFIG: Record<string, { icon: typeof Newspaper; color: string; label: string }> = {
  injury: {
    icon: AlertTriangle,
    color: "text-red-500 bg-red-100 dark:bg-red-500/20",
    label: "Blessure",
  },
  transfer: {
    icon: Users,
    color: "text-blue-500 bg-blue-100 dark:bg-blue-500/20",
    label: "Transfert",
  },
  form: {
    icon: TrendingUp,
    color: "text-green-500 bg-green-100 dark:bg-green-500/20",
    label: "Résultat",
  },
  preview: {
    icon: Newspaper,
    color: "text-purple-500 bg-purple-100 dark:bg-purple-500/20",
    label: "Avant-match",
  },
  general: {
    icon: Newspaper,
    color: "text-gray-500 bg-gray-100 dark:bg-gray-500/20",
    label: "Actualité",
  },
};

function ArticleCard({ article, locale }: { article: NewsArticle; locale: string }) {
  const dateLocale = locale === "fr" ? fr : enUS;
  const config = TYPE_CONFIG[article.article_type] || TYPE_CONFIG.general;
  const Icon = config.icon;

  const timeAgo = article.published_at
    ? formatDistanceToNow(new Date(article.published_at), {
        addSuffix: true,
        locale: dateLocale,
      })
    : null;

  return (
    <a
      href={article.url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-4 bg-white dark:bg-dark-800 border border-gray-200 dark:border-dark-700 rounded-lg hover:border-primary-300 dark:hover:border-primary-500/50 transition-colors group"
    >
      <div className="flex items-start gap-3">
        <span className={cn("p-2 rounded-lg shrink-0", config.color.split(" ").slice(1).join(" "))}>
          <Icon className={cn("w-4 h-4", config.color.split(" ")[0])} />
        </span>

        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 line-clamp-2 transition-colors">
            {article.title}
          </h4>

          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-dark-400">
            {article.team_name && (
              <span className="font-medium text-gray-700 dark:text-dark-300">
                {article.team_name}
              </span>
            )}

            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {timeAgo || "Récent"}
            </span>

            <span>{article.source}</span>

            {article.url && (
              <ExternalLink className="w-3 h-3 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
            )}
          </div>
        </div>
      </div>
    </a>
  );
}

export function NewsFeed({
  team,
  competition,
  limit = 10,
  showTitle = true,
  className,
}: NewsFeedProps) {
  const locale = useLocale();
  const [news, setNews] = useState<NewsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNews = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const params = new URLSearchParams();

      if (team) params.set("team", team);
      if (competition) params.set("competition", competition);
      params.set("limit", limit.toString());

      const response = await fetch(`${apiUrl}/api/v1/rag/news?${params}`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: NewsResponse = await response.json();
      setNews(data);
    } catch (err) {
      console.error("Failed to fetch news:", err);
      setError("Impossible de charger les actualités");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [team, competition, limit]);

  if (isLoading) {
    return (
      <div className={cn("bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5", className)}>
        {showTitle && (
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <Newspaper className="w-5 h-5 text-primary-500" />
            Actualités Football
          </h3>
        )}
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5", className)}>
        {showTitle && (
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <Newspaper className="w-5 h-5 text-primary-500" />
            Actualités Football
          </h3>
        )}
        <div className="text-center py-8">
          <p className="text-sm text-gray-500 dark:text-dark-400 mb-3">{error}</p>
          <button
            onClick={fetchNews}
            className="inline-flex items-center gap-2 text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            <RefreshCw className="w-4 h-4" />
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  if (!news || news.articles.length === 0) {
    return (
      <div className={cn("bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5", className)}>
        {showTitle && (
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
            <Newspaper className="w-5 h-5 text-primary-500" />
            Actualités Football
          </h3>
        )}
        <p className="text-sm text-gray-500 dark:text-dark-400 text-center py-8">
          Aucune actualité disponible
        </p>
      </div>
    );
  }

  return (
    <div className={cn("bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-5", className)}>
      {showTitle && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Newspaper className="w-5 h-5 text-primary-500" />
            Actualités Football
            {team && <span className="text-primary-500">- {team}</span>}
          </h3>
          <button
            onClick={fetchNews}
            className="p-2 text-gray-500 hover:text-primary-500 hover:bg-gray-100 dark:hover:bg-dark-700 rounded-lg transition-colors"
            title="Actualiser"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="space-y-3">
        {news.articles.map((article, index) => (
          <ArticleCard key={`${article.title}-${index}`} article={article} locale={locale} />
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-dark-700 flex items-center justify-between text-xs text-gray-500 dark:text-dark-400">
        <span>{news.total} articles trouvés</span>
        <span>
          Mis à jour{" "}
          {format(new Date(news.fetched_at), "HH:mm", {
            locale: locale === "fr" ? fr : enUS,
          })}
        </span>
      </div>
    </div>
  );
}
