"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Search, X, Trophy, Calendar } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { customInstance } from "@/lib/api/custom-instance";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TeamResult {
  id: number;
  name: string;
  short_name: string | null;
  tla: string | null;
  country: string | null;
  logo_url: string | null;
}

interface MatchResult {
  id: number;
  home_team_name: string;
  away_team_name: string;
  home_team_logo: string | null;
  away_team_logo: string | null;
  competition_code: string;
  match_date: string;
  status: string;
}

interface SearchApiResponse {
  data: {
    query: string;
    teams: TeamResult[];
    matches: MatchResult[];
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SearchBarProps {
  variant?: "desktop" | "mobile";
}

export function SearchBar({ variant = "desktop" }: SearchBarProps) {
  const router = useRouter();
  const t = useTranslations("searchBar");
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [teams, setTeams] = useState<TeamResult[]>([]);
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);

  // Total interactive items for keyboard navigation
  const totalItems = teams.length + matches.length;

  // -----------------------------------------------------------------------
  // Debounced fetch
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (query.length < 2) {
      setTeams([]);
      setMatches([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await customInstance<SearchApiResponse>(
          `/api/v1/search?q=${encodeURIComponent(query)}&limit=5`,
        );
        setTeams(res.data.teams);
        setMatches(res.data.matches);
        setIsOpen(true);
      } catch {
        setTeams([]);
        setMatches([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // -----------------------------------------------------------------------
  // Click outside to close
  // -----------------------------------------------------------------------
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // -----------------------------------------------------------------------
  // Navigation helpers
  // -----------------------------------------------------------------------
  const navigateToTeam = useCallback(
    (teamId: number) => {
      setIsOpen(false);
      setQuery("");
      router.push(`/matches?team=${teamId}`);
    },
    [router],
  );

  const navigateToMatch = useCallback(
    (matchId: number) => {
      setIsOpen(false);
      setQuery("");
      router.push(`/match/${matchId}`);
    },
    [router],
  );

  const handleSelect = useCallback(
    (index: number) => {
      if (index < teams.length) {
        const team = teams[index];
        if (team) navigateToTeam(team.id);
      } else {
        const match = matches[index - teams.length];
        if (match) navigateToMatch(match.id);
      }
    },
    [teams, matches, navigateToTeam, navigateToMatch],
  );

  // -----------------------------------------------------------------------
  // Keyboard handler
  // -----------------------------------------------------------------------
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false);
        inputRef.current?.blur();
        return;
      }
      if (!isOpen || totalItems === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % totalItems);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + totalItems) % totalItems);
      } else if (e.key === "Enter" && activeIndex >= 0) {
        e.preventDefault();
        handleSelect(activeIndex);
      }
    },
    [isOpen, totalItems, activeIndex, handleSelect],
  );

  // Reset active index when results change
  useEffect(() => {
    setActiveIndex(-1);
  }, [teams, matches]);

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------
  const formatDate = (dateStr: string) => {
    try {
      return new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(dateStr));
    } catch {
      return dateStr;
    }
  };

  const clear = () => {
    setQuery("");
    setTeams([]);
    setMatches([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div ref={containerRef} className={cn("relative", variant === "desktop" && "hidden md:block")}>
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-dark-400 pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (query.length >= 2 && (teams.length > 0 || matches.length > 0)) {
              setIsOpen(true);
            }
          }}
          placeholder={t("placeholder")}
          aria-label={t("placeholder")}
          aria-expanded={isOpen}
          aria-controls="search-results"
          aria-autocomplete="list"
          role="combobox"
          className={cn(
            "pl-8 pr-8 py-1.5 text-sm rounded-lg",
            variant === "desktop" ? "w-44 lg:w-56" : "w-full",
            "bg-gray-100 dark:bg-dark-800 border border-transparent",
            "text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-dark-400",
            "focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500",
            "transition-all duration-200",
          )}
        />
        {query && (
          <button
            onClick={clear}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 dark:text-dark-400 hover:text-gray-600 dark:hover:text-dark-200"
            aria-label={t("clear")}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Results dropdown */}
      {isOpen && (
        <div
          id="search-results"
          role="listbox"
          className={cn(
            "absolute top-full mt-2 right-0 w-80 lg:w-96 z-50",
            "bg-white dark:bg-dark-800 rounded-xl shadow-lg",
            "border border-gray-200 dark:border-dark-700",
            "max-h-96 overflow-y-auto",
            "animate-in fade-in slide-in-from-top-2 duration-200",
          )}
        >
          {isLoading && (
            <div className="px-4 py-3 text-sm text-gray-500 dark:text-dark-400">
              {t("searching")}
            </div>
          )}

          {!isLoading && teams.length === 0 && matches.length === 0 && query.length >= 2 && (
            <div className="px-4 py-6 text-center text-sm text-gray-500 dark:text-dark-400">
              {t("noResults")}
            </div>
          )}

          {/* Teams */}
          {teams.length > 0 && (
            <div>
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-dark-400 uppercase tracking-wider flex items-center gap-1.5">
                <Trophy className="w-3 h-3" />
                {t("teams")}
              </div>
              {teams.map((team, i) => (
                <button
                  key={`team-${team.id}`}
                  role="option"
                  aria-selected={activeIndex === i}
                  onClick={() => navigateToTeam(team.id)}
                  onMouseEnter={() => setActiveIndex(i)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors",
                    activeIndex === i
                      ? "bg-primary-50 dark:bg-primary-500/10"
                      : "hover:bg-gray-50 dark:hover:bg-dark-700",
                  )}
                >
                  {team.logo_url ? (
                    <Image
                      src={team.logo_url}
                      alt={team.name}
                      width={24}
                      height={24}
                      className="w-6 h-6 object-contain flex-shrink-0"
                    />
                  ) : (
                    <div className="w-6 h-6 rounded bg-gray-200 dark:bg-dark-600 flex items-center justify-center flex-shrink-0">
                      <Trophy className="w-3 h-3 text-gray-400" />
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {team.name}
                    </p>
                    {team.country && (
                      <p className="text-xs text-gray-500 dark:text-dark-400">
                        {team.country}
                        {team.tla ? ` (${team.tla})` : ""}
                      </p>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Matches */}
          {matches.length > 0 && (
            <div>
              {teams.length > 0 && (
                <div className="border-t border-gray-100 dark:border-dark-700" />
              )}
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-dark-400 uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-3 h-3" />
                {t("matches")}
              </div>
              {matches.map((match, i) => {
                const itemIndex = teams.length + i;
                return (
                  <button
                    key={`match-${match.id}`}
                    role="option"
                    aria-selected={activeIndex === itemIndex}
                    onClick={() => navigateToMatch(match.id)}
                    onMouseEnter={() => setActiveIndex(itemIndex)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors",
                      activeIndex === itemIndex
                        ? "bg-primary-50 dark:bg-primary-500/10"
                        : "hover:bg-gray-50 dark:hover:bg-dark-700",
                    )}
                  >
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {match.home_team_logo ? (
                        <Image
                          src={match.home_team_logo}
                          alt={match.home_team_name}
                          width={20}
                          height={20}
                          className="w-5 h-5 object-contain"
                        />
                      ) : (
                        <div className="w-5 h-5 rounded bg-gray-200 dark:bg-dark-600" />
                      )}
                      <span className="text-xs text-gray-400">vs</span>
                      {match.away_team_logo ? (
                        <Image
                          src={match.away_team_logo}
                          alt={match.away_team_name}
                          width={20}
                          height={20}
                          className="w-5 h-5 object-contain"
                        />
                      ) : (
                        <div className="w-5 h-5 rounded bg-gray-200 dark:bg-dark-600" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {match.home_team_name} vs {match.away_team_name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-dark-400">
                        {match.competition_code} &middot; {formatDate(match.match_date)}
                      </p>
                    </div>
                    {match.status === "live" && (
                      <span className="text-xs font-bold text-red-500 animate-pulse flex-shrink-0">
                        LIVE
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
