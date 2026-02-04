"use client";

import { useState, useEffect } from "react";
import {
  Search,
  Sparkles,
  Clock,
  Tag,
  Users,
  Loader2,
  AlertTriangle,
  Crown,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import { useTranslations, useLocale } from "next-intl";
import { useAuth } from "@/hooks/useAuth";
import { useSearchNewsApiV1VectorSearchGet } from "@/lib/api/endpoints/vector-store/vector-store";
import { cn } from "@/lib/utils";
import type { SearchResult } from "@/lib/api/models";

const ARTICLE_TYPE_COLORS: Record<string, string> = {
  injury: "bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300",
  transfer: "bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300",
  form: "bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-300",
  preview: "bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300",
  default: "bg-gray-100 dark:bg-dark-700 text-gray-700 dark:text-dark-300",
};

function SearchResultCard({ result, locale }: { result: SearchResult; locale: string }) {
  const dateLocale = locale === "fr" ? fr : enUS;
  const typeColor = ARTICLE_TYPE_COLORS[result.article_type || ""] || ARTICLE_TYPE_COLORS.default;

  return (
    <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 hover:border-primary-400 dark:hover:border-primary-500/50 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-2">
            {result.title}
          </h3>
          {result.content && (
            <p className="text-sm text-gray-600 dark:text-dark-400 mt-1 line-clamp-2">
              {result.content}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2 mt-3">
            {result.team_name && (
              <span className="inline-flex items-center gap-1 text-xs text-gray-600 dark:text-dark-400">
                <Users className="w-3 h-3" />
                {result.team_name}
              </span>
            )}
            {result.article_type && (
              <span className={cn("px-2 py-0.5 rounded text-xs font-medium", typeColor)}>
                {result.article_type}
              </span>
            )}
            {result.published_at && (
              <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-dark-500">
                <Clock className="w-3 h-3" />
                {format(new Date(result.published_at), "d MMM yyyy", { locale: dateLocale })}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div
            className={cn(
              "px-2 py-1 rounded text-xs font-medium",
              result.score >= 0.8
                ? "bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-300"
                : result.score >= 0.6
                  ? "bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300"
                  : "bg-gray-100 dark:bg-dark-700 text-gray-600 dark:text-dark-400"
            )}
          >
            {Math.round(result.score * 100)}%
          </div>
          {result.source && (
            <span className="text-xs text-gray-400 dark:text-dark-500">{result.source}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function UpgradeCTA({ t }: { t: (key: string) => string }) {
  return (
    <div className="bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-300 dark:border-primary-500/30 rounded-xl p-6 sm:p-8 text-center">
      <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary-100 dark:bg-primary-500/20 flex items-center justify-center">
        <Crown className="w-8 h-8 text-primary-500" />
      </div>
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
        {t("premiumRequired")}
      </h2>
      <p className="text-gray-600 dark:text-dark-400 mb-6 max-w-md mx-auto">
        {t("premiumDescription")}
      </p>
      <Link
        href="/plans"
        className="inline-flex items-center gap-2 px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium"
      >
        {t("upgradeToPremium")}
        <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

export default function SearchPage() {
  const t = useTranslations("search");
  const locale = useLocale();
  const { isPremium, loading: authLoading } = useAuth();

  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [articleType, setArticleType] = useState<string | undefined>();

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query.length >= 3) {
        setDebouncedQuery(query);
      } else {
        setDebouncedQuery("");
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [query]);

  const { data: response, isLoading, error } = useSearchNewsApiV1VectorSearchGet(
    { query: debouncedQuery, article_type: articleType, limit: 20 },
    {
      query: {
        enabled: isPremium && debouncedQuery.length >= 3,
      },
    }
  );

  const results = response?.status === 200 ? response.data.results : [];
  const searchTime = response?.status === 200 ? response.data.search_time_ms : 0;
  const total = response?.status === 200 ? response.data.total : 0;

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!isPremium) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-primary-500" />
            {t("title")}
          </h1>
          <p className="text-gray-600 dark:text-dark-400 mt-1">{t("subtitle")}</p>
        </div>
        <UpgradeCTA t={t} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-primary-500" />
          {t("title")}
        </h1>
        <p className="text-gray-600 dark:text-dark-400 mt-1">{t("subtitle")}</p>
      </div>

      {/* Search Bar */}
      <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("placeholder")}
              className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2">
            <select
              value={articleType || ""}
              onChange={(e) => setArticleType(e.target.value || undefined)}
              className="px-3 py-2.5 bg-gray-50 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">{t("filters.allTypes")}</option>
              <option value="injury">{t("filters.injury")}</option>
              <option value="transfer">{t("filters.transfer")}</option>
              <option value="form">{t("filters.form")}</option>
              <option value="preview">{t("filters.preview")}</option>
            </select>
          </div>
        </div>
        {query.length > 0 && query.length < 3 && (
          <p className="text-sm text-gray-500 dark:text-dark-400 mt-2">
            {t("minChars")}
          </p>
        )}
      </div>

      {/* Results */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500" />
          <p className="text-red-700 dark:text-red-300">{t("error")}</p>
        </div>
      )}

      {!isLoading && !error && debouncedQuery && results.length === 0 && (
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-8 text-center">
          <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-dark-700 flex items-center justify-center">
            <Search className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-gray-600 dark:text-dark-400">{t("noResults")}</p>
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="flex items-center justify-between text-sm text-gray-500 dark:text-dark-400">
            <span>
              {t("resultsCount", { count: total })}
            </span>
            <span>{t("searchTime", { time: searchTime })}</span>
          </div>
          <div className="space-y-3">
            {results.map((result) => (
              <SearchResultCard key={result.id} result={result} locale={locale} />
            ))}
          </div>
        </>
      )}

      {/* Tips */}
      {!debouncedQuery && (
        <div className="bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30 rounded-xl p-4">
          <h3 className="font-medium text-blue-800 dark:text-blue-300 mb-2 flex items-center gap-2">
            <Tag className="w-4 h-4" />
            {t("tips.title")}
          </h3>
          <ul className="text-sm text-blue-700 dark:text-blue-300/80 space-y-1">
            <li>• {t("tips.tip1")}</li>
            <li>• {t("tips.tip2")}</li>
            <li>• {t("tips.tip3")}</li>
          </ul>
        </div>
      )}
    </div>
  );
}
