"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import {
  useGetMatch,
  useGetHeadToHead,
  useGetTeamForm,
} from "@/lib/api/endpoints/matches/matches";
import { useGetPrediction } from "@/lib/api/endpoints/predictions/predictions";
import { useGetFullEnrichmentApiV1EnrichmentFullGet } from "@/lib/api/endpoints/data-enrichment/data-enrichment";
import type {
  MatchResponse,
  HeadToHeadResponse,
  TeamFormResponse,
  PredictionResponse,
  FullEnrichmentResponse,
  OddsData,
  XGEstimate,
  StandingsContext,
  TeamInfo,
} from "@/lib/api/models";
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Users,
  Trophy,
  Clock,
  Target,
  DollarSign,
  Crosshair,
  Medal,
  ArrowUpDown,
  Shield,
  ChevronDown,
  Flame,
  Goal,
} from "lucide-react";
import { cn, isAuthError } from "@/lib/utils";
import { format, parseISO } from "date-fns";
import { fr } from "date-fns/locale";
import { PredictionCharts } from "@/components/PredictionCharts";
import { MultiMarkets } from "@/components/MultiMarkets";
import type { MultiMarketsResponse } from "@/lib/api/models";

// Helper to get team name from TeamInfo | string
const getTeamName = (team: MatchResponse["home_team"] | string): string => {
  if (typeof team === "string") return team;
  return team?.name || "Unknown";
};

// Helper to get team info safely
const getTeamInfo = (team: MatchResponse["home_team"] | string): TeamInfo | null => {
  if (typeof team === "string") return null;
  return team || null;
};

export default function MatchDetailPage() {
  const params = useParams();
  const [matchId, setMatchId] = useState<number | null>(null);

  useEffect(() => {
    if (params?.id) {
      const idValue = Array.isArray(params.id) ? params.id[0] : params.id;
      const id = Number(idValue);
      if (!isNaN(id)) {
        setMatchId(id);
      }
    }
  }, [params]);

  // Using Orval hooks
  const { data: matchResponse, isLoading: matchLoading, error: matchError } = useGetMatch(
    matchId!,
    { query: { enabled: !!matchId && matchId > 0 } }
  );

  const { data: predictionResponse, isLoading: predictionLoading, error: predictionError } = useGetPrediction(
    matchId!,
    { include_model_details: true },
    { query: { enabled: !!matchId && matchId > 0, retry: 1 } }
  );

  const { data: h2hResponse } = useGetHeadToHead(
    matchId!,
    { limit: 10 },
    { query: { enabled: !!matchId && matchId > 0 } }
  );

  // Extract data from responses - API returns { data: {...}, status: number }
  const match = matchResponse?.data as MatchResponse | undefined;
  const prediction = predictionResponse?.data as PredictionResponse | undefined;
  const headToHead = h2hResponse?.data as HeadToHeadResponse | undefined;

  // Fetch form for both teams - extract IDs from home_team/away_team objects
  const homeTeamId = typeof match?.home_team === 'object' ? (match.home_team as { id?: number }).id : undefined;
  const awayTeamId = typeof match?.away_team === 'object' ? (match.away_team as { id?: number }).id : undefined;

  const { data: homeFormResponse } = useGetTeamForm(
    homeTeamId!,
    { matches_count: 5, team_name: getTeamName(match?.home_team || "") || undefined },
    { query: { enabled: !!homeTeamId && homeTeamId > 0 } }
  );

  const { data: awayFormResponse } = useGetTeamForm(
    awayTeamId!,
    { matches_count: 5, team_name: getTeamName(match?.away_team || "") || undefined },
    { query: { enabled: !!awayTeamId && awayTeamId > 0 } }
  );

  // Extract form data from responses - API returns { data: {...}, status: number }
  const homeForm = homeFormResponse?.data as TeamFormResponse | undefined;
  const awayForm = awayFormResponse?.data as TeamFormResponse | undefined;

  // Fetch full enrichment data (odds, xG, standings)
  const homeTeamName = getTeamName(match?.home_team || "");
  const awayTeamName = getTeamName(match?.away_team || "");
  // Use competition_code (e.g., "SA") not competition name (e.g., "Serie A")
  const competitionCode = typeof match?.competition_code === 'string' ? match.competition_code : 'PL';

  const { data: enrichmentResponse } = useGetFullEnrichmentApiV1EnrichmentFullGet(
    {
      home_team: homeTeamName,
      away_team: awayTeamName,
      competition: competitionCode,
    },
    { query: { enabled: !!homeTeamName && !!awayTeamName } }
  );

  const enrichment = enrichmentResponse?.data as FullEnrichmentResponse | undefined;

  if (matchLoading) {
    return <LoadingState />;
  }

  // Auth error - let global handler redirect, show nothing
  if (matchError && isAuthError(matchError)) {
    return null;
  }

  // Other errors or no match data
  if (matchError || !match) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 p-4 bg-red-100 dark:bg-red-500/10 border border-red-300 dark:border-red-500/30 rounded-xl">
          <AlertTriangle className="w-5 h-5 text-red-500 dark:text-red-400" />
          <p className="text-red-700 dark:text-red-300">
            Impossible de charger les details du match.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Match Header */}
      <MatchHeader match={match} />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Left Column - Prediction */}
        <div className="lg:col-span-2 space-y-4 sm:space-y-6">
          {predictionLoading && (
            <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6">
              <div className="animate-pulse space-y-3 sm:space-y-4">
                <div className="h-5 sm:h-6 bg-gray-200 dark:bg-slate-700 rounded w-1/3"></div>
                <div className="h-16 sm:h-20 bg-gray-200 dark:bg-slate-700 rounded"></div>
              </div>
            </div>
          )}

          {!predictionLoading && predictionError && !isAuthError(predictionError) ? (
            <div className="bg-red-100 dark:bg-red-500/10 border border-red-300 dark:border-red-500/30 rounded-xl p-4 sm:p-6">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 sm:w-6 h-5 sm:h-6 text-red-500 dark:text-red-400 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base">Erreur de chargement</h3>
                  <p className="text-xs sm:text-sm text-red-600 dark:text-red-300">
                    {(predictionError as Error)?.message || "Impossible de charger les predictions"}
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          {!predictionLoading && !predictionError && !prediction && (
            <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6">
              <div className="flex items-center gap-3 text-gray-500 dark:text-slate-400">
                <Target className="w-5 sm:w-6 h-5 sm:h-6 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base">Predictions non disponibles</h3>
                  <p className="text-xs sm:text-sm">Les predictions pour ce match seront bientot disponibles.</p>
                </div>
              </div>
            </div>
          )}

          {prediction && <PredictionSection prediction={prediction} />}

          {prediction && prediction.key_factors && prediction.key_factors.length > 0 && (
            <KeyFactorsSection prediction={prediction} />
          )}

          {/* Multi-Markets Section */}
          {prediction && (
            <MultiMarketsSection
              prediction={prediction}
              homeTeam={getTeamName(match.home_team)}
              awayTeam={getTeamName(match.away_team)}
            />
          )}

          {homeForm && awayForm && (
            <TeamFormSection homeForm={homeForm} awayForm={awayForm} />
          )}
        </div>

        {/* Right Column - Head to Head */}
        <div>
          {headToHead && (
            <HeadToHeadSection
              headToHead={headToHead}
              homeTeam={getTeamName(match.home_team)}
              awayTeam={getTeamName(match.away_team)}
            />
          )}
        </div>
      </div>

      {/* Model Contributions */}
      {prediction?.model_contributions && (
        <ModelContributionsSection prediction={prediction} />
      )}

      {/* LLM Adjustments */}
      {prediction?.llm_adjustments && (
        <LLMAdjustmentsSection prediction={prediction} />
      )}

      {/* Enrichment Data: Odds, xG, Standings */}
      {enrichment && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          {/* Odds Section */}
          {enrichment.odds && (
            <OddsSection odds={enrichment.odds} />
          )}

          {/* xG Estimates Section */}
          {(enrichment.home_xg_estimate || enrichment.away_xg_estimate) && (
            <XGEstimatesSection
              homeXg={enrichment.home_xg_estimate}
              awayXg={enrichment.away_xg_estimate}
              homeTeam={homeTeamName}
              awayTeam={awayTeamName}
            />
          )}

          {/* Standings Context */}
          {enrichment.standings && (
            <StandingsSection
              standings={enrichment.standings}
              homeTeam={homeTeamName}
              awayTeam={awayTeamName}
            />
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Team Logo with Fallback
   ============================================ */
function TeamLogo({ team, size = "md" }: { team: TeamInfo | null; size?: "sm" | "md" | "lg" }) {
  const [imgError, setImgError] = useState(false);

  const sizeClasses = {
    sm: "w-10 h-10 sm:w-12 sm:h-12",
    md: "w-14 h-14 sm:w-16 sm:h-16 lg:w-20 lg:h-20",
    lg: "w-20 h-20 sm:w-24 sm:h-24 lg:w-28 lg:h-28",
  };

  if (!team?.logo_url || imgError) {
    return (
      <div className={cn(
        sizeClasses[size],
        "rounded-full bg-gradient-to-br from-gray-200 to-gray-300 dark:from-slate-700 dark:to-slate-600 flex items-center justify-center"
      )}>
        <Shield className="w-1/2 h-1/2 text-gray-400 dark:text-slate-500" />
      </div>
    );
  }

  return (
    <div className={cn(sizeClasses[size], "relative")}>
      <Image
        src={team.logo_url}
        alt={`${team.name} logo`}
        fill
        className="object-contain"
        onError={() => setImgError(true)}
        unoptimized // football-data.org images
      />
    </div>
  );
}

/* ============================================
   COMPONENT: Countdown Timer
   ============================================ */
function CountdownTimer({ targetDate }: { targetDate: Date }) {
  const [timeLeft, setTimeLeft] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0 });
  const [isExpired, setIsExpired] = useState(false);

  const calculateTimeLeft = useCallback(() => {
    const now = new Date();
    const diff = targetDate.getTime() - now.getTime();

    if (diff <= 0) {
      setIsExpired(true);
      return { days: 0, hours: 0, minutes: 0, seconds: 0 };
    }

    return {
      days: Math.floor(diff / (1000 * 60 * 60 * 24)),
      hours: Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
      minutes: Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)),
      seconds: Math.floor((diff % (1000 * 60)) / 1000),
    };
  }, [targetDate]);

  useEffect(() => {
    setTimeLeft(calculateTimeLeft());
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);
    return () => clearInterval(timer);
  }, [calculateTimeLeft]);

  if (isExpired) {
    return (
      <div className="text-center">
        <span className="text-sm font-semibold text-primary-500 dark:text-primary-400">
          Match en cours ou terminé
        </span>
      </div>
    );
  }

  const TimeUnit = ({ value, label }: { value: number; label: string }) => (
    <div className="flex flex-col items-center">
      <div className="bg-gray-100 dark:bg-slate-700 rounded-lg px-2 py-1 sm:px-3 sm:py-2 min-w-[2.5rem] sm:min-w-[3rem]">
        <span className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900 dark:text-white tabular-nums">
          {String(value).padStart(2, "0")}
        </span>
      </div>
      <span className="text-[10px] sm:text-xs text-gray-500 dark:text-slate-400 mt-1">{label}</span>
    </div>
  );

  return (
    <div className="flex items-center gap-1 sm:gap-2">
      {timeLeft.days > 0 && <TimeUnit value={timeLeft.days} label="j" />}
      {timeLeft.days > 0 && <span className="text-gray-400 dark:text-slate-500 text-lg">:</span>}
      <TimeUnit value={timeLeft.hours} label="h" />
      <span className="text-gray-400 dark:text-slate-500 text-lg">:</span>
      <TimeUnit value={timeLeft.minutes} label="m" />
      <span className="text-gray-400 dark:text-slate-500 text-lg">:</span>
      <TimeUnit value={timeLeft.seconds} label="s" />
    </div>
  );
}

/* ============================================
   COMPONENT: Match Header
   ============================================ */
function MatchHeader({ match }: { match: MatchResponse }) {
  let matchDate;
  try {
    matchDate = match?.match_date && typeof match.match_date === 'string'
      ? parseISO(match.match_date)
      : new Date();
  } catch {
    matchDate = new Date();
  }

  const statusLabels: Record<string, string> = {
    scheduled: "A venir",
    live: "EN DIRECT",
    finished: "Termine",
    postponed: "Reporte",
  };

  const statusColors: Record<string, string> = {
    scheduled: "bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-500/30",
    live: "bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300 border-red-300 dark:border-red-500/30 animate-pulse",
    finished: "bg-gray-100 dark:bg-gray-500/20 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-500/30",
    postponed: "bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-300 border-yellow-300 dark:border-yellow-500/30",
  };

  const status = typeof match?.status === 'string' ? match.status : 'scheduled';
  const competition = typeof match?.competition === 'string' ? match.competition : 'Competition';
  const homeTeamName = getTeamName(match.home_team);
  const awayTeamName = getTeamName(match.away_team);
  const homeTeamInfo = getTeamInfo(match.home_team);
  const awayTeamInfo = getTeamInfo(match.away_team);
  const isUpcoming = status === "scheduled";

  return (
    <div className="bg-gradient-to-r from-gray-50 to-white dark:from-slate-800/50 dark:to-slate-900/50 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden">
      <div className="p-4 sm:p-6 lg:p-8">
        {/* Competition & Status Row */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 sm:mb-6 gap-2 sm:gap-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Trophy className="w-4 sm:w-5 h-4 sm:h-5 text-accent-400" />
            <span className="text-accent-400 font-semibold text-sm sm:text-base">
              {competition}
            </span>
            {typeof match?.matchday === 'number' && (
              <span className="text-gray-500 dark:text-slate-400 text-xs sm:text-sm">
                • Journee {match.matchday}
              </span>
            )}
          </div>
          <div
            className={cn(
              "px-2 sm:px-3 py-1 rounded-lg border font-semibold text-xs sm:text-sm",
              statusColors[status] || statusColors.scheduled
            )}
          >
            {statusLabels[status] || "Status"}
          </div>
        </div>

        {/* Teams Row with Logos */}
        <div className="flex items-center justify-between gap-2 sm:gap-4">
          {/* Home Team */}
          <div className="flex-1 flex flex-col items-center gap-2 sm:gap-3">
            <TeamLogo team={homeTeamInfo} size="md" />
            <h2 className="text-sm sm:text-lg lg:text-2xl font-bold text-gray-900 dark:text-white text-center break-words max-w-full">
              {homeTeamName}
            </h2>
            {status === "finished" && typeof match?.home_score === 'number' && (
              <p className="text-2xl sm:text-3xl lg:text-4xl font-bold text-primary-400">
                {match.home_score}
              </p>
            )}
          </div>

          {/* Center - VS / Countdown / Score */}
          <div className="flex flex-col items-center gap-2 sm:gap-3 px-2 sm:px-4 lg:px-6 min-w-[100px] sm:min-w-[180px]">
            {status === "finished" ? (
              <p className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-500 dark:text-slate-400">
                vs
              </p>
            ) : status === "live" ? (
              <div className="flex flex-col items-center gap-1">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                  <span className="text-red-500 font-bold text-sm sm:text-base">LIVE</span>
                </div>
              </div>
            ) : isUpcoming ? (
              <div className="flex flex-col items-center gap-2">
                <CountdownTimer targetDate={matchDate} />
              </div>
            ) : (
              <p className="text-xl sm:text-2xl font-bold text-gray-500 dark:text-slate-400">
                vs
              </p>
            )}

            {/* Date/Time (always shown) */}
            <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2 text-gray-500 dark:text-slate-400 text-xs sm:text-sm">
              <Clock className="w-3 sm:w-4 h-3 sm:h-4" />
              <span className="text-center">
                {format(matchDate, "dd MMM yyyy", { locale: fr })}
              </span>
              <span className="hidden sm:inline">à</span>
              <span>{format(matchDate, "HH:mm", { locale: fr })}</span>
            </div>
          </div>

          {/* Away Team */}
          <div className="flex-1 flex flex-col items-center gap-2 sm:gap-3">
            <TeamLogo team={awayTeamInfo} size="md" />
            <h2 className="text-sm sm:text-lg lg:text-2xl font-bold text-gray-900 dark:text-white text-center break-words max-w-full">
              {awayTeamName}
            </h2>
            {status === "finished" && typeof match?.away_score === 'number' && (
              <p className="text-2xl sm:text-3xl lg:text-4xl font-bold text-accent-400">
                {match.away_score}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================
   COMPONENT: Prediction Section
   ============================================ */
function PredictionSection({
  prediction,
}: {
  prediction: PredictionResponse;
}) {
  const betLabels: Record<string, string> = {
    home: "Victoire domicile",
    home_win: "Victoire domicile",
    draw: "Match nul",
    away: "Victoire exterieur",
    away_win: "Victoire exterieur",
  };

  const confidence = typeof prediction?.confidence === 'number' && !isNaN(prediction.confidence)
    ? prediction.confidence
    : 0;

  const confidenceColor =
    confidence >= 0.7
      ? "text-primary-400"
      : confidence >= 0.6
        ? "text-yellow-400"
        : "text-orange-400";

  const homeProb = prediction?.probabilities?.home_win ?? 0;
  const drawProb = prediction?.probabilities?.draw ?? 0;
  const awayProb = prediction?.probabilities?.away_win ?? 0;

  const recommendedBet = prediction?.recommended_bet;
  const recommendedBetStr = typeof recommendedBet === 'string' ? recommendedBet : '';
  const isHomeRecommended = recommendedBetStr === "home_win";
  const isAwayRecommended = recommendedBetStr === "away_win";

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
          <h2 className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Target className="w-5 sm:w-6 h-5 sm:h-6 text-primary-400 flex-shrink-0" />
            Prediction
          </h2>
          <div className={cn("text-right", confidenceColor)}>
            <p className="font-bold text-base sm:text-lg">
              {Math.round(confidence * 100)}%
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Confiance</p>
          </div>
        </div>

        <div className="space-y-3 sm:space-y-4">
          <ProbabilityBar
            label="Victoire Domicile"
            probability={homeProb}
            isRecommended={isHomeRecommended}
            color="primary"
          />
          <ProbabilityBar
            label="Match Nul"
            probability={drawProb}
            isRecommended={recommendedBet === "draw"}
            color="yellow"
          />
          <ProbabilityBar
            label="Victoire Exterieur"
            probability={awayProb}
            isRecommended={isAwayRecommended}
            color="accent"
          />
        </div>

        <div className="flex items-start sm:items-center gap-3 p-3 sm:p-4 bg-primary-100 dark:bg-primary-500/10 border border-primary-300 dark:border-primary-500/30 rounded-lg">
          <CheckCircle className="w-5 sm:w-6 h-5 sm:h-6 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5 sm:mt-0" />
          <div className="min-w-0">
            <p className="text-primary-700 dark:text-primary-400 font-bold text-sm sm:text-base">
              {betLabels[recommendedBet] || "Prediction indisponible"}
            </p>
            <p className="text-xs sm:text-sm text-primary-600 dark:text-primary-300">
              Cote Value: +{typeof prediction?.value_score === 'number' && !isNaN(prediction.value_score)
                ? Math.round(prediction.value_score * 100)
                : 0}%
            </p>
          </div>
        </div>


        {prediction.explanation && (
          <div className="p-3 sm:p-4 bg-gray-200 dark:bg-slate-700/50 rounded-lg border border-gray-300 dark:border-slate-600">
            <p className="text-gray-600 dark:text-slate-300 text-sm leading-relaxed">
              {prediction.explanation}
            </p>
          </div>
        )}
      </div>

      <PredictionCharts prediction={prediction as any} />
    </div>
  );
}

/* ============================================
   COMPONENT: Key Factors Section
   ============================================ */
function KeyFactorsSection({
  prediction,
}: {
  prediction: PredictionResponse;
}) {
  const keyFactors = prediction?.key_factors || [];
  const riskFactors = prediction?.risk_factors || [];

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-3 sm:space-y-4">
      <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-accent-400 flex-shrink-0" />
        Facteurs Cles
      </h3>

      {keyFactors.length > 0 && (
        <div className="space-y-2">
          {keyFactors.map((factor, index) => (
            <div key={index} className="flex items-start gap-3 p-3 bg-gray-100 dark:bg-slate-700/50 rounded-lg">
              <CheckCircle className="w-4 sm:w-5 h-4 sm:h-5 text-primary-400 flex-shrink-0 mt-0.5" />
              <p className="text-gray-800 dark:text-slate-200 text-sm">{factor}</p>
            </div>
          ))}
        </div>
      )}

      {riskFactors.length > 0 && (
        <div className="space-y-2 pt-3 sm:pt-4 border-t border-gray-200 dark:border-slate-700">
          <h4 className="text-xs sm:text-sm font-semibold text-yellow-600 dark:text-yellow-400">Facteurs de Risque</h4>
          {riskFactors.map((factor, index) => (
            <div key={index} className="flex items-start gap-3 p-3 bg-yellow-100 dark:bg-yellow-500/10 rounded-lg border border-yellow-300 dark:border-yellow-500/20">
              <AlertTriangle className="w-4 sm:w-5 h-4 sm:h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-yellow-800 dark:text-yellow-200 text-xs sm:text-sm">{factor}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Team Form Section
   ============================================ */
function TeamFormSection({
  homeForm,
  awayForm,
}: {
  homeForm: TeamFormResponse;
  awayForm: TeamFormResponse;
}) {
  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-primary-400 flex-shrink-0" />
        Forme Recente
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        <TeamFormCard form={homeForm} isHome={true} />
        <TeamFormCard form={awayForm} isHome={false} />
      </div>
    </div>
  );
}

function TeamFormCard({ form, isHome }: { form: TeamFormResponse; isHome: boolean }) {
  if (!form) {
    return (
      <div className="bg-gray-200 dark:bg-slate-700/50 rounded-lg p-3 sm:p-4">
        <p className="text-gray-500 dark:text-slate-400 text-sm">Donnees non disponibles</p>
      </div>
    );
  }

  const formString = form.form_string || "";
  const formResults = formString.split("").filter(Boolean).slice(0, 5);
  const color = isHome ? "primary" : "accent";

  return (
    <div className="bg-gray-200 dark:bg-slate-700/50 rounded-lg p-3 sm:p-4 space-y-3 sm:space-y-4">
      <div>
        <h4 className="font-bold text-gray-900 dark:text-white text-sm sm:text-base mb-1">{form.team_name}</h4>
        {formString && (
          <p className={cn("text-xs sm:text-sm font-mono", color === "primary" ? "text-primary-400" : "text-accent-400")}>
            {formString}
          </p>
        )}
      </div>

      {formResults.length > 0 && (
        <div className="flex gap-2">
          {formResults.map((result, i) => {
            const resultStr = result.toUpperCase();
            const bgColor = resultStr === "W" ? "bg-primary-500" : resultStr === "D" ? "bg-gray-500" : "bg-red-500";
            const displayLabel = resultStr === "W" ? "V" : resultStr === "D" ? "N" : "D";
            return (
              <div key={i} className={cn("flex-1 h-7 sm:h-8 rounded flex items-center justify-center text-gray-900 dark:text-white font-semibold text-xs sm:text-sm", bgColor)}>
                {displayLabel}
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs sm:text-sm">
        <div>
          <p className="text-gray-500 dark:text-slate-400">Points (5 derniers)</p>
          <p className="text-base sm:text-lg font-bold text-gray-900 dark:text-white">{form.points_last_5 ?? "-"}</p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-slate-400">Buts marques/match</p>
          <p className="text-base sm:text-lg font-bold text-primary-400">
            {typeof form.goals_scored_avg === 'number' ? form.goals_scored_avg.toFixed(1) : "-"}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-slate-400">Buts encaisses/match</p>
          <p className="text-base sm:text-lg font-bold text-orange-400">
            {typeof form.goals_conceded_avg === 'number' ? form.goals_conceded_avg.toFixed(1) : "-"}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-slate-400">Matchs sans encaisser</p>
          <p className="text-base sm:text-lg font-bold text-accent-400">{form.clean_sheets ?? "-"}</p>
        </div>
      </div>

      {(form.xg_for_avg !== null || form.xg_against_avg !== null) && (
        <div className="grid grid-cols-2 gap-2 text-xs sm:text-sm border-t border-gray-300 dark:border-slate-600 pt-2 sm:pt-3">
          <div>
            <p className="text-gray-500 dark:text-slate-400">xG pour/match</p>
            <p className="text-base sm:text-lg font-bold text-primary-300">
              {typeof form.xg_for_avg === 'number' ? form.xg_for_avg.toFixed(2) : "-"}
            </p>
          </div>
          <div>
            <p className="text-gray-500 dark:text-slate-400">xG contre/match</p>
            <p className="text-base sm:text-lg font-bold text-orange-300">
              {typeof form.xg_against_avg === 'number' ? form.xg_against_avg.toFixed(2) : "-"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Head to Head Section (Enhanced)
   ============================================ */
function HeadToHeadSection({
  headToHead,
  homeTeam,
  awayTeam,
}: {
  headToHead: HeadToHeadResponse;
  homeTeam: string;
  awayTeam: string;
}) {
  const [showDetails, setShowDetails] = useState(false);

  // Calculate additional stats from matches
  const matches = headToHead.matches || [];
  const totalGoalsHome = matches.reduce((sum, m) => {
    // Count goals when homeTeam was playing (either as home or away)
    if (m.home_team === homeTeam) return sum + m.home_score;
    if (m.away_team === homeTeam) return sum + m.away_score;
    return sum;
  }, 0);
  const totalGoalsAway = matches.reduce((sum, m) => {
    if (m.home_team === awayTeam) return sum + m.home_score;
    if (m.away_team === awayTeam) return sum + m.away_score;
    return sum;
  }, 0);

  // Calculate winning streak
  const calculateStreak = () => {
    if (matches.length === 0) return null;
    let streakTeam: string | null = null;
    let streakCount = 0;

    for (const match of matches) {
      let winner: string | null = null;
      if (match.home_score > match.away_score) {
        winner = match.home_team;
      } else if (match.away_score > match.home_score) {
        winner = match.away_team;
      }

      if (streakTeam === null && winner) {
        streakTeam = winner;
        streakCount = 1;
      } else if (winner === streakTeam) {
        streakCount++;
      } else {
        break;
      }
    }

    if (streakCount >= 2 && streakTeam) {
      return { team: streakTeam, count: streakCount };
    }
    return null;
  };

  const streak = calculateStreak();
  const lastMatch = matches[0];
  const avgGoals = headToHead.avg_goals ?? 0;

  // Format last match result
  const formatLastMatchResult = () => {
    if (!lastMatch) return null;
    try {
      const date = format(parseISO(lastMatch.date), "dd MMM yyyy", { locale: fr });
      return { date, score: `${lastMatch.home_score} - ${lastMatch.away_score}`, teams: `${lastMatch.home_team} vs ${lastMatch.away_team}` };
    } catch {
      return null;
    }
  };
  const lastMatchInfo = formatLastMatchResult();

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6 sticky top-8">
      <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <Users className="w-5 h-5 text-accent-400 flex-shrink-0" />
        Head-to-Head
        {headToHead.total_matches > 0 && (
          <span className="text-xs text-gray-500 dark:text-slate-400 font-normal ml-auto">
            {headToHead.total_matches} matchs
          </span>
        )}
      </h3>

      {/* Win/Draw/Lose Stats */}
      <div className="space-y-2">
        <div className="flex items-center justify-between p-2.5 sm:p-3 bg-primary-100 dark:bg-primary-500/10 border border-primary-200 dark:border-primary-500/20 rounded-lg">
          <span className="text-primary-700 dark:text-primary-300 font-semibold text-sm">Victoires {homeTeam}</span>
          <span className="text-xl sm:text-2xl font-bold text-primary-600 dark:text-primary-400">{headToHead.home_wins ?? 0}</span>
        </div>
        <div className="flex items-center justify-between p-2.5 sm:p-3 bg-gray-100 dark:bg-gray-500/10 border border-gray-200 dark:border-gray-500/20 rounded-lg">
          <span className="text-gray-700 dark:text-gray-300 font-semibold text-sm">Matchs nuls</span>
          <span className="text-xl sm:text-2xl font-bold text-gray-600 dark:text-gray-400">{headToHead.draws ?? 0}</span>
        </div>
        <div className="flex items-center justify-between p-2.5 sm:p-3 bg-accent-100 dark:bg-accent-500/10 border border-accent-200 dark:border-accent-500/20 rounded-lg">
          <span className="text-accent-700 dark:text-accent-300 font-semibold text-sm">Victoires {awayTeam}</span>
          <span className="text-xl sm:text-2xl font-bold text-accent-600 dark:text-accent-400">{headToHead.away_wins ?? 0}</span>
        </div>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-200 dark:border-slate-700">
        <div className="text-center p-2 bg-gray-50 dark:bg-slate-700/30 rounded-lg">
          <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-slate-400">
            <Goal className="w-3.5 h-3.5" />
            <span className="text-xs">Moy. buts/match</span>
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-white">{avgGoals.toFixed(1)}</p>
        </div>
        <div className="text-center p-2 bg-gray-50 dark:bg-slate-700/30 rounded-lg">
          <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-slate-400">
            <Goal className="w-3.5 h-3.5" />
            <span className="text-xs">Buts totaux</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <span className="text-sm font-bold text-primary-500">{totalGoalsHome}</span>
            <span className="text-gray-400">-</span>
            <span className="text-sm font-bold text-accent-500">{totalGoalsAway}</span>
          </div>
        </div>
      </div>

      {/* Winning Streak */}
      {streak && (
        <div className="flex items-center gap-2 p-2.5 bg-gradient-to-r from-orange-100 to-yellow-100 dark:from-orange-500/20 dark:to-yellow-500/20 rounded-lg border border-orange-200 dark:border-orange-500/30">
          <Flame className="w-4 h-4 text-orange-500" />
          <span className="text-sm text-orange-700 dark:text-orange-300">
            <span className="font-bold">{streak.team}</span>: {streak.count} victoires consecutives
          </span>
        </div>
      )}

      {/* Last Confrontation */}
      {lastMatchInfo && (
        <div className="p-3 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-slate-700/50 dark:to-slate-800/50 rounded-lg border border-gray-200 dark:border-slate-600">
          <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Derniere confrontation</p>
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-900 dark:text-white">{lastMatchInfo.teams}</p>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{lastMatchInfo.score}</p>
          </div>
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{lastMatchInfo.date}</p>
        </div>
      )}

      {/* Collapsible Match History */}
      {matches.length > 0 && (
        <div className="border-t border-gray-200 dark:border-slate-700 pt-3">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center justify-between w-full text-sm font-semibold text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <span>Historique ({matches.length} matchs)</span>
            <ChevronDown
              className={cn(
                "w-4 h-4 transition-transform",
                showDetails && "rotate-180"
              )}
            />
          </button>

          {showDetails && (
            <div className="space-y-2 mt-3 max-h-64 overflow-y-auto">
              {matches.map((match, index) => {
                const matchHomeTeam = match.home_team;
                const matchAwayTeam = match.away_team;
                const homeWon = match.home_score > match.away_score;
                const awayWon = match.away_score > match.home_score;

                let dateDisplay = "";
                try {
                  dateDisplay = format(parseISO(match.date), "dd MMM yyyy", { locale: fr });
                } catch {
                  dateDisplay = "Date invalide";
                }

                // Determine which team in this H2H context won
                const winnerIsHome = (homeWon && matchHomeTeam === homeTeam) || (awayWon && matchAwayTeam === homeTeam);
                const winnerIsAway = (homeWon && matchHomeTeam === awayTeam) || (awayWon && matchAwayTeam === awayTeam);
                const isDraw = match.home_score === match.away_score;

                const borderColor = winnerIsHome
                  ? "border-l-primary-500"
                  : winnerIsAway
                    ? "border-l-accent-500"
                    : "border-l-gray-400";

                return (
                  <div
                    key={`h2h-${index}-${match.date}`}
                    className={cn(
                      "p-2.5 bg-gray-100 dark:bg-slate-700/50 rounded-lg text-xs border-l-2",
                      borderColor
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-semibold text-gray-800 dark:text-slate-100">
                        {matchHomeTeam} vs {matchAwayTeam}
                      </p>
                      <p className={cn(
                        "font-bold",
                        isDraw ? "text-gray-500" : winnerIsHome ? "text-primary-500" : "text-accent-500"
                      )}>
                        {match.home_score} - {match.away_score}
                      </p>
                    </div>
                    <div className="flex items-center justify-between text-gray-500 dark:text-slate-400">
                      <span>{dateDisplay}</span>
                      <span className="text-[10px] truncate max-w-[100px]">{match.competition}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Model Contributions Section
   ============================================ */
function ModelContributionsSection({ prediction }: { prediction: PredictionResponse }) {
  if (!prediction?.model_contributions) return null;

  const models = Object.entries(prediction.model_contributions).filter(([, v]) => v);
  if (models.length === 0) return null;

  const modelDescriptions: Record<string, { desc: string; weight: string; icon: string }> = {
    poisson: { desc: "Distribution statistique des buts", weight: "15%", icon: "📊" },
    elo: { desc: "Classement dynamique des equipes", weight: "10%", icon: "📈" },
    xg_model: { desc: "Analyse des Expected Goals (xG)", weight: "15%", icon: "⚽" },
    xgboost: { desc: "Machine Learning gradient boosting", weight: "35%", icon: "🤖" },
  };

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-accent-400 flex-shrink-0" />
          Modeles de Prediction
        </h3>
        <span className="text-xs sm:text-sm text-gray-500 dark:text-slate-400">{models.length} modeles combines</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {models.map(([modelName, contribution]) => {
          const modelInfo = modelDescriptions[modelName] || { desc: "Modele statistique", weight: "N/A", icon: "📐" };
          return (
            <ModelContributionCard
              key={modelName}
              modelName={modelName}
              contribution={contribution!}
              description={modelInfo.desc}
              weight={modelInfo.weight}
              icon={modelInfo.icon}
            />
          );
        })}
      </div>
    </div>
  );
}

function ModelContributionCard({
  modelName,
  contribution,
  description,
  weight,
  icon,
}: {
  modelName: string;
  contribution: { home_win?: number; draw?: number; away_win?: number };
  description: string;
  weight: string;
  icon: string;
}) {
  const displayName: Record<string, string> = {
    poisson: "Poisson",
    elo: "ELO",
    xg_model: "Expected Goals",
    xgboost: "XGBoost ML",
  };

  const homeProb = contribution?.home_win ?? 0;
  const drawProb = contribution?.draw ?? 0;
  const awayProb = contribution?.away_win ?? 0;

  const maxProb = Math.max(homeProb, drawProb, awayProb);
  const predictedOutcome = maxProb === homeProb ? "home" : maxProb === drawProb ? "draw" : "away";
  const outcomeColors = { home: "border-primary-500/50", draw: "border-yellow-500/50", away: "border-accent-500/50" };

  return (
    <div className={cn("bg-gray-200 dark:bg-slate-700/50 rounded-lg p-3 sm:p-4 space-y-3 border-l-2", outcomeColors[predictedOutcome])}>
      <div className="flex items-start gap-2">
        <span className="text-lg">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-gray-900 dark:text-white text-sm sm:text-base font-semibold truncate">{displayName[modelName] || modelName}</p>
          <p className="text-xs text-gray-500 dark:text-slate-400">Poids: {weight}</p>
        </div>
      </div>
      <p className="text-xs text-gray-500 dark:text-slate-400 line-clamp-2">{description}</p>
      <div className="space-y-1.5 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-slate-400">Domicile:</span>
          <span className="text-primary-400 font-semibold">{Math.round(homeProb * 100)}%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-slate-400">Nul:</span>
          <span className="text-yellow-400 font-semibold">{Math.round(drawProb * 100)}%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-slate-400">Exterieur:</span>
          <span className="text-accent-400 font-semibold">{Math.round(awayProb * 100)}%</span>
        </div>
      </div>
    </div>
  );
}

/* ============================================
   COMPONENT: LLM Adjustments Section
   ============================================ */
function LLMAdjustmentsSection({ prediction }: { prediction: PredictionResponse }) {
  if (!prediction?.llm_adjustments) return null;

  const adjustments = prediction.llm_adjustments;

  const formatAdjustment = (value: number | undefined): string => {
    if (typeof value !== 'number' || isNaN(value)) return "-";
    return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
  };

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary-400 flex-shrink-0" />
          Analyse IA Avancee
        </h3>
        <div className={cn(
          "px-3 py-1 rounded-full text-xs sm:text-sm font-semibold",
          (adjustments.total_adjustment ?? 0) >= 0 ? "bg-primary-500/20 text-primary-400" : "bg-red-500/20 text-red-400"
        )}>
          Ajustement Total: {formatAdjustment(adjustments.total_adjustment)}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-gray-200 dark:bg-slate-700/30 rounded-lg p-3 sm:p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white text-sm mb-2">🏥 Impact Blessures</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-gray-500 dark:text-slate-400">Domicile</p>
              <p className="text-orange-400 font-bold">{formatAdjustment(adjustments.injury_impact_home)}</p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-slate-400">Exterieur</p>
              <p className="text-orange-400 font-bold">{formatAdjustment(adjustments.injury_impact_away)}</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-200 dark:bg-slate-700/30 rounded-lg p-3 sm:p-4">
          <h4 className="font-semibold text-gray-900 dark:text-white text-sm mb-2">💭 Sentiment & Moral</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-gray-500 dark:text-slate-400">Domicile</p>
              <p className="text-blue-400 font-bold">{formatAdjustment(adjustments.sentiment_home)}</p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-slate-400">Exterieur</p>
              <p className="text-blue-400 font-bold">{formatAdjustment(adjustments.sentiment_away)}</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-200 dark:bg-slate-700/30 rounded-lg p-3 sm:p-4 sm:col-span-2">
          <h4 className="font-semibold text-gray-900 dark:text-white text-sm mb-2">⚔️ Avantage Tactique</h4>
          <p className="text-primary-400 font-bold text-lg">{formatAdjustment(adjustments.tactical_edge)}</p>
        </div>
      </div>

      {adjustments.reasoning && (
        <div className="p-3 sm:p-4 bg-gradient-to-r from-primary-100 to-accent-100 dark:from-primary-500/10 dark:to-accent-500/10 rounded-lg border border-primary-200 dark:border-primary-500/20">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🤖</span>
            <h4 className="font-semibold text-gray-900 dark:text-white text-sm sm:text-base">Raisonnement IA</h4>
          </div>
          <p className="text-xs sm:text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{adjustments.reasoning}</p>
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Odds Section
   ============================================ */
function OddsSection({ odds }: { odds: OddsData }) {
  if (!odds.home_win && !odds.draw && !odds.away_win) return null;

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4">
      <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <DollarSign className="w-5 h-5 text-green-500" />
        Cotes Bookmakers
      </h3>

      <div className="grid grid-cols-3 gap-3">
        <div className="text-center p-3 bg-primary-100 dark:bg-primary-500/20 rounded-lg border border-primary-300 dark:border-primary-500/40">
          <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Domicile</p>
          <p className="text-xl font-bold text-primary-600 dark:text-primary-400">
            {odds.home_win?.toFixed(2) || "-"}
          </p>
        </div>
        <div className="text-center p-3 bg-gray-100 dark:bg-gray-500/20 rounded-lg border border-gray-300 dark:border-gray-500/40">
          <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Nul</p>
          <p className="text-xl font-bold text-gray-600 dark:text-gray-400">
            {odds.draw?.toFixed(2) || "-"}
          </p>
        </div>
        <div className="text-center p-3 bg-accent-100 dark:bg-accent-500/20 rounded-lg border border-accent-300 dark:border-accent-500/40">
          <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Exterieur</p>
          <p className="text-xl font-bold text-accent-600 dark:text-accent-400">
            {odds.away_win?.toFixed(2) || "-"}
          </p>
        </div>
      </div>

      {odds.value_detected && (
        <div className="flex items-center gap-2 p-2 bg-green-100 dark:bg-green-500/20 rounded-lg border border-green-300 dark:border-green-500/40">
          <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
          <span className="text-xs text-green-700 dark:text-green-300 font-semibold">
            Value Bet detecte
          </span>
        </div>
      )}

      {odds.bookmakers && odds.bookmakers.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-gray-200 dark:border-slate-700">
          <span className="text-xs text-gray-500 dark:text-slate-400">Sources:</span>
          {odds.bookmakers.map((bookie, i) => (
            <span key={i} className="px-1.5 py-0.5 bg-gray-100 dark:bg-slate-700 rounded text-[10px] text-gray-600 dark:text-slate-400">
              {bookie}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: xG Estimates Section
   ============================================ */
function XGEstimatesSection({
  homeXg,
  awayXg,
  homeTeam,
  awayTeam,
}: {
  homeXg?: XGEstimate | null;
  awayXg?: XGEstimate | null;
  homeTeam: string;
  awayTeam: string;
}) {
  if (!homeXg && !awayXg) return null;

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4">
      <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <Crosshair className="w-5 h-5 text-orange-500" />
        Expected Goals (xG)
      </h3>

      <div className="space-y-4">
        {/* Home Team xG */}
        {homeXg && (
          <div className="p-3 bg-primary-50 dark:bg-primary-500/10 rounded-lg border border-primary-200 dark:border-primary-500/30">
            <p className="text-xs font-semibold text-primary-700 dark:text-primary-300 mb-2">{homeTeam}</p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <p className="text-gray-700 dark:text-slate-400">xG estime</p>
                <p className="text-lg font-bold text-primary-600 dark:text-primary-400">
                  {homeXg.estimated_xg?.toFixed(2) || "-"}
                </p>
              </div>
              <div>
                <p className="text-gray-700 dark:text-slate-400">xGA estime</p>
                <p className="text-lg font-bold text-orange-500">
                  {homeXg.estimated_xga?.toFixed(2) || "-"}
                </p>
              </div>
              <div>
                <p className="text-gray-700 dark:text-slate-400">Rating offensif</p>
                <p className="font-semibold text-green-600 dark:text-green-400">
                  {homeXg.offensive_rating?.toFixed(1) || "-"}
                </p>
              </div>
              <div>
                <p className="text-gray-700 dark:text-slate-400">Rating defensif</p>
                <p className="font-semibold text-red-500">
                  {homeXg.defensive_rating?.toFixed(1) || "-"}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Away Team xG */}
        {awayXg && (
          <div className="p-3 bg-accent-50 dark:bg-accent-500/10 rounded-lg border border-accent-200 dark:border-accent-500/30">
            <p className="text-xs font-semibold text-accent-700 dark:text-accent-300 mb-2">{awayTeam}</p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <p className="text-gray-700 dark:text-slate-400">xG estime</p>
                <p className="text-lg font-bold text-accent-600 dark:text-accent-400">
                  {awayXg.estimated_xg?.toFixed(2) || "-"}
                </p>
              </div>
              <div>
                <p className="text-gray-700 dark:text-slate-400">xGA estime</p>
                <p className="text-lg font-bold text-orange-500">
                  {awayXg.estimated_xga?.toFixed(2) || "-"}
                </p>
              </div>
              <div>
                <p className="text-gray-700 dark:text-slate-400">Rating offensif</p>
                <p className="font-semibold text-green-600 dark:text-green-400">
                  {awayXg.offensive_rating?.toFixed(1) || "-"}
                </p>
              </div>
              <div>
                <p className="text-gray-700 dark:text-slate-400">Rating defensif</p>
                <p className="font-semibold text-red-500">
                  {awayXg.defensive_rating?.toFixed(1) || "-"}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ============================================
   COMPONENT: Standings Section
   ============================================ */
function StandingsSection({
  standings,
  homeTeam,
  awayTeam,
}: {
  standings: StandingsContext;
  homeTeam: string;
  awayTeam: string;
}) {
  const hasData = standings.home_position || standings.away_position;
  if (!hasData) return null;

  const positionDiff = standings.position_diff ?? 0;
  const diffColor = positionDiff > 0 ? "text-primary-500" : positionDiff < 0 ? "text-accent-500" : "text-gray-500";

  return (
    <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 sm:p-6 space-y-4">
      <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <Medal className="w-5 h-5 text-yellow-500" />
        Classement
      </h3>

      <div className="grid grid-cols-2 gap-4">
        {/* Home Team */}
        <div className="p-3 bg-primary-50 dark:bg-primary-500/10 rounded-lg border border-primary-200 dark:border-primary-500/30 text-center">
          <p className="text-xs text-gray-700 dark:text-slate-400 mb-1 truncate">{homeTeam}</p>
          <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">
            {standings.home_position ? `${standings.home_position}e` : "-"}
          </p>
          {standings.home_points != null && (
            <p className="text-xs text-gray-700 dark:text-slate-400">{standings.home_points} pts</p>
          )}
        </div>

        {/* Away Team */}
        <div className="p-3 bg-accent-50 dark:bg-accent-500/10 rounded-lg border border-accent-200 dark:border-accent-500/30 text-center">
          <p className="text-xs text-gray-700 dark:text-slate-400 mb-1 truncate">{awayTeam}</p>
          <p className="text-2xl font-bold text-accent-600 dark:text-accent-400">
            {standings.away_position ? `${standings.away_position}e` : "-"}
          </p>
          {standings.away_points != null && (
            <p className="text-xs text-gray-700 dark:text-slate-400">{standings.away_points} pts</p>
          )}
        </div>
      </div>

      {/* Position Difference */}
      {positionDiff !== 0 && (
        <div className="flex items-center justify-center gap-2 p-2 bg-gray-100 dark:bg-slate-700/50 rounded-lg">
          <ArrowUpDown className={cn("w-4 h-4", diffColor)} />
          <span className={cn("text-sm font-semibold", diffColor)}>
            {Math.abs(positionDiff)} place{Math.abs(positionDiff) > 1 ? "s" : ""} d'ecart
          </span>
        </div>
      )}

      {/* Context Note */}
      {standings.context_note && (
        <div className="p-2 bg-yellow-50 dark:bg-yellow-500/10 rounded-lg border border-yellow-200 dark:border-yellow-500/30">
          <p className="text-xs text-yellow-700 dark:text-yellow-300">{standings.context_note}</p>
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Probability Bar
   ============================================ */
function ProbabilityBar({
  label,
  probability,
  isRecommended,
  color,
}: {
  label: string;
  probability: number;
  isRecommended: boolean;
  color: "primary" | "accent" | "yellow";
}) {
  const colorClasses: Record<string, string> = {
    primary: "bg-primary-500",
    accent: "bg-accent-500",
    yellow: "bg-yellow-500",
  };

  const textColorClasses: Record<string, string> = {
    primary: "text-primary-400",
    accent: "text-accent-400",
    yellow: "text-yellow-400",
  };

  const prob = probability ?? 0;

  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <span className={cn("text-sm font-semibold", isRecommended ? textColorClasses[color] : "text-gray-800 dark:text-slate-300")}>
          {label}
        </span>
        <span className={cn("text-sm font-bold", isRecommended ? textColorClasses[color] : "text-gray-700 dark:text-slate-400")}>
          {Math.round(prob * 100)}%
        </span>
      </div>
      <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", colorClasses[color], !isRecommended && "opacity-60")}
          style={{ width: `${prob * 100}%` }}
        />
      </div>
    </div>
  );
}

/* ============================================
   COMPONENT: Loading State
   ============================================ */
function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-8 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-1/3 mb-4" />
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-2/3 mx-auto" />
          </div>
          <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/4" />
          <div className="flex-1 space-y-2">
            <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-2/3 mx-auto" />
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {[1, 2].map((i) => (
            <div key={i} className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-6 animate-pulse">
              <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-1/3 mb-4" />
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-full" />
                <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-5/6" />
              </div>
            </div>
          ))}
        </div>
        <div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-6 animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-1/2 mb-4" />
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded" />
            <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================
   COMPONENT: Multi-Markets Section
   ============================================ */
function MultiMarketsSection({
  prediction,
  homeTeam,
  awayTeam,
}: {
  prediction: PredictionResponse;
  homeTeam: string;
  awayTeam: string;
}) {
  // Use real multi-markets data from API if available
  const mm = prediction?.multi_markets;

  if (!mm) {
    return null; // No multi-markets data available
  }

  // Transform API data to component format
  const overUnder25 = {
    prob: mm.over_under_25.over_prob,
    odds: {
      over: mm.over_under_25.over_odds ?? undefined,
      under: mm.over_under_25.under_odds ?? undefined,
    },
  };

  const overUnder15 = {
    prob: mm.over_under_15.over_prob,
    odds: {
      over: mm.over_under_15.over_odds ?? undefined,
      under: mm.over_under_15.under_odds ?? undefined,
    },
  };

  const btts = {
    prob: mm.btts.yes_prob,
    odds: {
      yes: mm.btts.yes_odds ?? undefined,
      no: mm.btts.no_odds ?? undefined,
    },
  };

  const doubleChance = {
    homeOrDraw: {
      prob: mm.double_chance["1X"],
      odds: mm.double_chance.home_or_draw_odds ?? undefined,
    },
    awayOrDraw: {
      prob: mm.double_chance.X2,
      odds: mm.double_chance.away_or_draw_odds ?? undefined,
    },
    homeOrAway: {
      prob: mm.double_chance["12"],
      odds: mm.double_chance.home_or_away_odds ?? undefined,
    },
  };

  return (
    <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-6">
      <MultiMarkets
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        overUnder25={overUnder25}
        overUnder15={overUnder15}
        btts={btts}
        doubleChance={doubleChance}
      />
    </div>
  );
}
