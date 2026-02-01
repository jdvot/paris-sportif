"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  fetchMatch,
  fetchPrediction,
  fetchHeadToHead,
  fetchTeamForm,
} from "@/lib/api";
import type {
  Match,
  DetailedPrediction,
  TeamForm,
} from "@/lib/types";
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Users,
  Trophy,
  Clock,
  Target,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format, parseISO } from "date-fns";
import { fr } from "date-fns/locale";

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

  const { data: match, isLoading: matchLoading, error: matchError } = useQuery({
    queryKey: ["match", matchId],
    queryFn: () => fetchMatch(matchId!),
    enabled: !!matchId && matchId > 0,
  });

  const { data: prediction, isLoading: predictionLoading, error: predictionError } = useQuery({
    queryKey: ["prediction", matchId],
    queryFn: () => fetchPrediction(matchId!, true),
    enabled: !!matchId && matchId > 0,
    retry: false, // Don't retry on 500 errors
  });

  const { data: headToHead } = useQuery({
    queryKey: ["headToHead", matchId],
    queryFn: () => fetchHeadToHead(matchId!, 10),
    enabled: !!matchId && matchId > 0,
  });

  // Fetch form for both teams - use real team IDs from API
  const homeTeamId = (match as { homeTeamId?: number } | undefined)?.homeTeamId;
  const awayTeamId = (match as { awayTeamId?: number } | undefined)?.awayTeamId;

  const { data: homeForm } = useQuery({
    queryKey: ["teamForm", homeTeamId],
    queryFn: () => fetchTeamForm(homeTeamId!, 5),
    enabled: !!homeTeamId && homeTeamId > 0,
  });

  const { data: awayForm } = useQuery({
    queryKey: ["teamForm", awayTeamId],
    queryFn: () => fetchTeamForm(awayTeamId!, 5),
    enabled: !!awayTeamId && awayTeamId > 0,
  });

  if (matchLoading) {
    return <LoadingState />;
  }

  if (matchError || !match) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <p className="text-red-300">
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
            <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6">
              <div className="animate-pulse space-y-3 sm:space-y-4">
                <div className="h-5 sm:h-6 bg-dark-700 rounded w-1/3"></div>
                <div className="h-16 sm:h-20 bg-dark-700 rounded"></div>
              </div>
            </div>
          )}

          {!predictionLoading && !prediction && (
            <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6">
              <div className="flex items-center gap-3 text-dark-400">
                <Target className="w-5 sm:w-6 h-5 sm:h-6 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-white text-sm sm:text-base">Predictions non disponibles</h3>
                  <p className="text-xs sm:text-sm">Les predictions pour ce match seront bientot disponibles.</p>
                </div>
              </div>
            </div>
          )}

          {prediction && <PredictionSection prediction={prediction} />}

          {prediction && prediction.keyFactors && prediction.keyFactors.length > 0 && (
            <KeyFactorsSection prediction={prediction} />
          )}

          {homeForm && awayForm && typeof homeForm === 'object' && typeof awayForm === 'object' && (
            <TeamFormSection homeForm={homeForm} awayForm={awayForm} />
          )}
        </div>

        {/* Right Column - Head to Head */}
        <div>
          {headToHead && (
            <HeadToHeadSection
              headToHead={headToHead}
              homeTeam={match.homeTeam}
              awayTeam={match.awayTeam}
            />
          )}
        </div>
      </div>

      {/* Model Contributions */}
      {prediction?.modelContributions && (
        <ModelContributionsSection prediction={prediction} />
      )}

      {/* LLM Adjustments */}
      {prediction?.llmAdjustments && (
        <LLMAdjustmentsSection prediction={prediction} />
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Match Header
   ============================================ */
function MatchHeader({ match }: { match: Match }) {
  // Guard: safely parse match date
  let matchDate;
  try {
    matchDate = match?.matchDate && typeof match.matchDate === 'string'
      ? parseISO(match.matchDate)
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
    scheduled: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    live: "bg-red-500/20 text-red-300 border-red-500/30 animate-pulse",
    finished: "bg-gray-500/20 text-gray-300 border-gray-500/30",
    postponed: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  };

  const status = typeof match?.status === 'string' ? match.status : 'scheduled';
  const competition = typeof match?.competition === 'string' ? match.competition : 'Compétition';

  return (
    <div className="bg-gradient-to-r from-dark-800/50 to-dark-900/50 border border-dark-700 rounded-xl overflow-hidden">
      <div className="p-4 sm:p-6 lg:p-8">
        {/* Competition and Status */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 sm:mb-6 gap-2 sm:gap-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Trophy className="w-4 sm:w-5 h-4 sm:h-5 text-accent-400" />
            <span className="text-accent-400 font-semibold text-sm sm:text-base">
              {competition}
            </span>
            {typeof match?.matchday === 'number' && (
              <span className="text-dark-400 text-xs sm:text-sm">
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

        {/* Teams and Score */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 sm:gap-4">
          {/* Home Team */}
          <div className="flex-1 text-center order-1 sm:order-1">
            <h2 className="text-lg sm:text-xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 break-words">
              {typeof match?.homeTeam === 'string' ? match.homeTeam : "Équipe"}
            </h2>
            {status === "finished" && typeof match?.homeScore === 'number' && (
              <p className="text-2xl sm:text-3xl lg:text-4xl font-bold text-primary-400">
                {match.homeScore}
              </p>
            )}
          </div>

          {/* VS and Date */}
          <div className="flex flex-col items-center gap-1 sm:gap-2 px-2 sm:px-4 lg:px-6 order-2 sm:order-2">
            <p className="text-lg sm:text-xl lg:text-2xl font-bold text-dark-400">vs</p>
            <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2 text-dark-400 text-xs sm:text-sm">
              <Clock className="w-3 sm:w-4 h-3 sm:h-4" />
              <span className="text-center">
                {format(matchDate, "dd MMM yyyy", { locale: fr })}
              </span>
              <span className="hidden sm:inline">à</span>
              <span>{format(matchDate, "HH:mm", { locale: fr })}</span>
            </div>
          </div>

          {/* Away Team */}
          <div className="flex-1 text-center order-3 sm:order-3">
            <h2 className="text-lg sm:text-xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 break-words">
              {typeof match?.awayTeam === 'string' ? match.awayTeam : "Équipe"}
            </h2>
            {status === "finished" && typeof match?.awayScore === 'number' && (
              <p className="text-2xl sm:text-3xl lg:text-4xl font-bold text-accent-400">
                {match.awayScore}
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
  prediction: DetailedPrediction;
}) {
  const betLabels: Record<string, string> = {
    home: "Victoire domicile",
    home_win: "Victoire domicile",
    draw: "Match nul",
    away: "Victoire exterieur",
    away_win: "Victoire exterieur",
  };

  const betColors: Record<string, string> = {
    home: "text-primary-400",
    home_win: "text-primary-400",
    draw: "text-yellow-400",
    away: "text-accent-400",
    away_win: "text-accent-400",
  };

  // Guard: safely extract numeric values
  const confidence = typeof prediction?.confidence === 'number' && !isNaN(prediction.confidence)
    ? prediction.confidence
    : 0;

  const confidenceColor =
    confidence >= 0.7
      ? "text-primary-400"
      : confidence >= 0.6
        ? "text-yellow-400"
        : "text-orange-400";

  // Support both API formats (snake_case from API, camelCase from types)
  // API returns: home_win, draw, away_win (snake_case)
  // Types expect: homeWin, draw, awayWin (camelCase)
  const probs = prediction?.probabilities as Record<string, number> | undefined;

  const homeProb = typeof prediction?.homeProb === 'number'
    ? prediction.homeProb
    : typeof probs?.home_win === 'number'
      ? probs.home_win
      : typeof probs?.homeWin === 'number'
        ? probs.homeWin
        : 0;

  const drawProb = typeof prediction?.drawProb === 'number'
    ? prediction.drawProb
    : typeof probs?.draw === 'number'
      ? probs.draw
      : 0;

  const awayProb = typeof prediction?.awayProb === 'number'
    ? prediction.awayProb
    : typeof probs?.away_win === 'number'
      ? probs.away_win
      : typeof probs?.awayWin === 'number'
        ? probs.awayWin
        : 0;

  const recommendedBet = typeof prediction?.recommendedBet === 'string' ? prediction.recommendedBet : '';
  const isHomeRecommended = recommendedBet === "home" || recommendedBet === "home_win";
  const isAwayRecommended = recommendedBet === "away" || recommendedBet === "away_win";

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
        <h2 className="text-lg sm:text-2xl font-bold text-white flex items-center gap-2">
          <Target className="w-5 sm:w-6 h-5 sm:h-6 text-primary-400 flex-shrink-0" />
          Prediction
        </h2>
        <div className={cn("text-right", confidenceColor)}>
          <p className="font-bold text-base sm:text-lg">
            {Math.round(confidence * 100)}%
          </p>
          <p className="text-xs text-dark-300">Confiance</p>
        </div>
      </div>

      {/* Probabilities */}
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
          isRecommended={prediction.recommendedBet === "draw"}
          color="yellow"
        />
        <ProbabilityBar
          label="Victoire Exterieur"
          probability={awayProb}
          isRecommended={isAwayRecommended}
          color="accent"
        />
      </div>

      {/* Recommended Bet */}
      <div className="flex items-start sm:items-center gap-3 p-3 sm:p-4 bg-primary-500/10 border border-primary-500/30 rounded-lg">
        <CheckCircle className="w-5 sm:w-6 h-5 sm:h-6 text-primary-400 flex-shrink-0 mt-0.5 sm:mt-0" />
        <div className="min-w-0">
          <p className="text-primary-400 font-bold text-sm sm:text-base">
            {typeof prediction?.recommendedBet === 'string' && betLabels[prediction.recommendedBet]
              ? betLabels[prediction.recommendedBet]
              : "Prédiction indisponible"}
          </p>
          <p className="text-xs sm:text-sm text-primary-300">
            Cote Value: +{typeof prediction?.valueScore === 'number' && !isNaN(prediction.valueScore)
              ? Math.round(prediction.valueScore * 100)
              : 0}%
          </p>
        </div>
      </div>

      {/* Expected Goals */}
      {(typeof prediction?.expectedHomeGoals === 'number' || typeof prediction?.expectedAwayGoals === 'number') && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4">
            <p className="text-dark-400 text-xs sm:text-sm mb-1">Buts attendus (Domicile)</p>
            <p className="text-2xl sm:text-3xl font-bold text-primary-400">
              {typeof prediction?.expectedHomeGoals === 'number' && !isNaN(prediction.expectedHomeGoals)
                ? prediction.expectedHomeGoals.toFixed(2)
                : "-"}
            </p>
          </div>
          <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4">
            <p className="text-dark-400 text-xs sm:text-sm mb-1">Buts attendus (Exterieur)</p>
            <p className="text-2xl sm:text-3xl font-bold text-accent-400">
              {typeof prediction?.expectedAwayGoals === 'number' && !isNaN(prediction.expectedAwayGoals)
                ? prediction.expectedAwayGoals.toFixed(2)
                : "-"}
            </p>
          </div>
        </div>
      )}

      {/* Explanation */}
      {prediction.explanation && (
        <div className="p-3 sm:p-4 bg-dark-700/50 rounded-lg border border-dark-600">
          <p className="text-dark-300 text-sm leading-relaxed">
            {prediction.explanation}
          </p>
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Key Factors Section
   ============================================ */
function KeyFactorsSection({
  prediction,
}: {
  prediction: DetailedPrediction;
}) {
  // Guard: safely extract arrays
  const keyFactors = Array.isArray(prediction?.keyFactors)
    ? prediction.keyFactors.filter(factor => typeof factor === 'string' && factor.length > 0)
    : [];

  const riskFactors = Array.isArray(prediction?.riskFactors)
    ? prediction.riskFactors.filter(factor => typeof factor === 'string' && factor.length > 0)
    : [];

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 space-y-3 sm:space-y-4">
      <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-accent-400 flex-shrink-0" />
        Facteurs Cles
      </h3>

      {keyFactors.length > 0 && (
        <div className="space-y-2">
          {keyFactors.map((factor, index) => (
            <div
              key={index}
              className="flex items-start gap-3 p-3 bg-dark-700/50 rounded-lg"
            >
              <CheckCircle className="w-4 sm:w-5 h-4 sm:h-5 text-primary-400 flex-shrink-0 mt-0.5" />
              <p className="text-dark-200 text-sm">{factor}</p>
            </div>
          ))}
        </div>
      )}

      {riskFactors.length > 0 && (
        <div className="space-y-2 pt-3 sm:pt-4 border-t border-dark-700">
          <h4 className="text-xs sm:text-sm font-semibold text-yellow-400">
            Facteurs de Risque
          </h4>
          {riskFactors.map((factor, index) => (
            <div
              key={index}
              className="flex items-start gap-3 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20"
            >
              <AlertTriangle className="w-4 sm:w-5 h-4 sm:h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-yellow-200 text-xs sm:text-sm">{factor}</p>
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
  homeForm: TeamForm;
  awayForm: TeamForm;
}) {
  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
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

function TeamFormCard({ form, isHome }: { form: TeamForm; isHome: boolean }) {
  // Guard clause: safely handle undefined form
  if (!form || typeof form !== 'object') {
    return (
      <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4">
        <p className="text-dark-400 text-sm">Données non disponibles</p>
      </div>
    );
  }

  // Safely extract and validate formString
  const formString = typeof form.formString === 'string' && form.formString.length > 0 ? form.formString : "";

  // Safely split the form string - guard against null/undefined
  const formResults = formString && typeof formString === 'string'
    ? formString.split("").filter(Boolean).slice(0, 5)
    : [];

  const color = isHome ? "primary" : "accent";
  const teamName = typeof form.teamName === 'string' ? form.teamName : "Équipe";

  return (
    <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4 space-y-3 sm:space-y-4">
      <div>
        <h4 className="font-bold text-white text-sm sm:text-base mb-1">{teamName}</h4>
        {formString && typeof formString === 'string' && (
          <p className={cn("text-xs sm:text-sm font-mono", color === "primary" ? "text-primary-400" : "text-accent-400")}>
            {formString}
          </p>
        )}
      </div>

      {/* Last 5 matches */}
      {Array.isArray(formResults) && formResults.length > 0 && (
        <div className="flex gap-2">
          {formResults.map((result, i) => {
            const resultStr = typeof result === 'string' ? result.toUpperCase() : "";
            // API returns W (Win), D (Draw), L (Loss)
            const bgColor =
              resultStr === "W"
                ? "bg-primary-500"
                : resultStr === "D"
                  ? "bg-gray-500"
                  : "bg-red-500";
            // Display in French: V (Victoire), N (Nul), D (Défaite)
            const displayLabel = resultStr === "W" ? "V" : resultStr === "D" ? "N" : "D";
            return (
              <div
                key={i}
                className={cn(
                  "flex-1 h-7 sm:h-8 rounded flex items-center justify-center text-white font-semibold text-xs sm:text-sm",
                  bgColor
                )}
              >
                {displayLabel}
              </div>
            );
          })}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-xs sm:text-sm">
        <div>
          <p className="text-dark-400">Points (5 derniers)</p>
          <p className="text-base sm:text-lg font-bold text-white">
            {typeof form.pointsLast5 === 'number' ? form.pointsLast5 : "-"}
          </p>
        </div>
        <div>
          <p className="text-dark-400">Buts marques/match</p>
          <p className="text-base sm:text-lg font-bold text-primary-400">
            {typeof form.goalsScoredAvg === 'number' ? form.goalsScoredAvg.toFixed(1) : "-"}
          </p>
        </div>
        <div>
          <p className="text-dark-400">Buts encaisses/match</p>
          <p className="text-base sm:text-lg font-bold text-orange-400">
            {typeof form.goalsConcededAvg === 'number' ? form.goalsConcededAvg.toFixed(1) : "-"}
          </p>
        </div>
        <div>
          <p className="text-dark-400">Matchs sans encaisser</p>
          <p className="text-base sm:text-lg font-bold text-accent-400">
            {typeof form.cleanSheets === 'number' ? form.cleanSheets : "-"}
          </p>
        </div>
      </div>

      {/* xG Stats if available */}
      {(typeof form.xgForAvg === 'number' || typeof form.xgAgainstAvg === 'number') && (
        <div className="grid grid-cols-2 gap-2 text-xs sm:text-sm border-t border-dark-600 pt-2 sm:pt-3">
          <div>
            <p className="text-dark-400">xG pour/match</p>
            <p className="text-base sm:text-lg font-bold text-primary-300">
              {typeof form.xgForAvg === 'number' ? form.xgForAvg.toFixed(2) : "-"}
            </p>
          </div>
          <div>
            <p className="text-dark-400">xG contre/match</p>
            <p className="text-base sm:text-lg font-bold text-orange-300">
              {typeof form.xgAgainstAvg === 'number' ? form.xgAgainstAvg.toFixed(2) : "-"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Head to Head Section
   ============================================ */
function HeadToHeadSection({
  headToHead,
  homeTeam,
  awayTeam,
}: {
  headToHead: {
    matches: Match[];
    homeWins: number;
    draws: number;
    awayWins: number;
  };
  homeTeam: string;
  awayTeam: string;
}) {
  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 space-y-6 sticky top-8">
      <h3 className="text-xl font-bold text-white flex items-center gap-2">
        <Users className="w-5 h-5 text-accent-400" />
        Head-to-Head
      </h3>

      {/* Historical Stats */}
      <div className="space-y-3">
        <div className="flex items-center justify-between p-3 bg-primary-500/10 border border-primary-500/20 rounded-lg">
          <span className="text-primary-300 font-semibold">
            Victoires {typeof homeTeam === 'string' ? homeTeam : "Équipe"}
          </span>
          <span className="text-2xl font-bold text-primary-400">
            {typeof headToHead?.homeWins === 'number' ? headToHead.homeWins : 0}
          </span>
        </div>
        <div className="flex items-center justify-between p-3 bg-gray-500/10 border border-gray-500/20 rounded-lg">
          <span className="text-gray-300 font-semibold">Matchs nuls</span>
          <span className="text-2xl font-bold text-gray-400">
            {typeof headToHead?.draws === 'number' ? headToHead.draws : 0}
          </span>
        </div>
        <div className="flex items-center justify-between p-3 bg-accent-500/10 border border-accent-500/20 rounded-lg">
          <span className="text-accent-300 font-semibold">
            Victoires {typeof awayTeam === 'string' ? awayTeam : "Équipe"}
          </span>
          <span className="text-2xl font-bold text-accent-400">
            {typeof headToHead?.awayWins === 'number' ? headToHead.awayWins : 0}
          </span>
        </div>
      </div>

      {/* Recent Matches */}
      {Array.isArray(headToHead.matches) && headToHead.matches.length > 0 && (
        <div className="space-y-2 border-t border-dark-700 pt-4">
          <h4 className="text-sm font-semibold text-dark-300">Derniers Matchs</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {(headToHead.matches || []).map((match) => {
              // Guard clauses for match properties
              if (!match || typeof match !== 'object') return null;

              const homeTeam = typeof match.homeTeam === 'string' ? match.homeTeam : "Équipe";
              const awayTeam = typeof match.awayTeam === 'string' ? match.awayTeam : "Équipe";
              const homeScore = typeof match.homeScore === 'number' ? match.homeScore : null;
              const awayScore = typeof match.awayScore === 'number' ? match.awayScore : null;
              const status = typeof match.status === 'string' ? match.status : "scheduled";

              let scoreDisplay = "";
              if (status === "finished" && homeScore !== null && awayScore !== null) {
                scoreDisplay = `${homeScore} - ${awayScore}`;
              } else if (match.matchDate && typeof match.matchDate === 'string') {
                try {
                  scoreDisplay = format(parseISO(match.matchDate), "dd MMM yyyy", {
                    locale: fr,
                  });
                } catch {
                  scoreDisplay = "Date invalide";
                }
              } else {
                scoreDisplay = "Date indisponible";
              }

              return (
                <div
                  key={match.id || Math.random()}
                  className="p-2 bg-dark-700/50 rounded text-xs space-y-1"
                >
                  <p className="font-semibold text-dark-100">
                    {homeTeam} vs {awayTeam}
                  </p>
                  <p className="text-dark-400">
                    {scoreDisplay}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================
   COMPONENT: Model Contributions Section
   ============================================ */
function ModelContributionsSection({
  prediction,
}: {
  prediction: DetailedPrediction;
}) {
  // Guard: check if modelContributions exists and is an object
  if (!prediction || !prediction.modelContributions || typeof prediction.modelContributions !== 'object') {
    return null;
  }

  const models = Array.isArray(prediction.modelContributions)
    ? []
    : Object.entries(prediction.modelContributions).filter(
        ([key, value]) => typeof key === 'string' && value && typeof value === 'object'
      );

  // Guard: check if models array is not empty
  if (!Array.isArray(models) || models.length === 0) {
    return null;
  }

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 space-y-3 sm:space-y-4">
      <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-accent-400 flex-shrink-0" />
        Contributions des Modeles
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {models.map(([modelName, contribution]) => {
          if (!modelName || typeof modelName !== 'string' || !contribution || typeof contribution !== 'object') {
            return null;
          }
          return (
            <ModelContributionCard
              key={modelName}
              modelName={modelName}
              contribution={contribution as any}
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
}: {
  modelName: string;
  contribution: {
    homeProb?: number;
    drawProb?: number;
    awayProb?: number;
    homeWin?: number;
    draw?: number;
    awayWin?: number;
    weight?: number;
  };
}) {
  const displayName: Record<string, string> = {
    poisson: "Poisson",
    elo: "ELO",
    xg: "xG",
    xgModel: "xG Model",
    xgboost: "XGBoost",
  };

  // Guard: safely extract numeric values with proper type checking
  const homeProb = typeof contribution?.homeProb === 'number'
    ? contribution.homeProb
    : typeof contribution?.homeWin === 'number'
      ? contribution.homeWin
      : 0;

  const drawProb = typeof contribution?.drawProb === 'number'
    ? contribution.drawProb
    : typeof contribution?.draw === 'number'
      ? contribution.draw
      : 0;

  const awayProb = typeof contribution?.awayProb === 'number'
    ? contribution.awayProb
    : typeof contribution?.awayWin === 'number'
      ? contribution.awayWin
      : 0;

  const weight = typeof contribution?.weight === 'number' ? contribution.weight : 0.25;

  // Guard: ensure values are valid numbers before calculations
  const safeHomeProb = typeof homeProb === 'number' && !isNaN(homeProb) ? homeProb : 0;
  const safeDrawProb = typeof drawProb === 'number' && !isNaN(drawProb) ? drawProb : 0;
  const safeAwayProb = typeof awayProb === 'number' && !isNaN(awayProb) ? awayProb : 0;
  const safeWeight = typeof weight === 'number' && !isNaN(weight) ? weight : 0.25;

  const displayModelName = typeof modelName === 'string' ? displayName[modelName] || modelName : "Modèle";

  return (
    <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4 space-y-2">
      <div>
        <p className="text-dark-300 text-xs sm:text-sm font-semibold">
          {displayModelName}
        </p>
        <p className="text-xs text-dark-400">
          Poids: {Math.round(safeWeight * 100)}%
        </p>
      </div>

      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-dark-400">Domicile:</span>
          <span className="text-primary-400 font-semibold">
            {Math.round(safeHomeProb * 100)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-dark-400">Nul:</span>
          <span className="text-yellow-400 font-semibold">
            {Math.round(safeDrawProb * 100)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-dark-400">Exterieur:</span>
          <span className="text-accent-400 font-semibold">
            {Math.round(safeAwayProb * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
}

/* ============================================
   COMPONENT: LLM Adjustments Section
   ============================================ */
function LLMAdjustmentsSection({
  prediction,
}: {
  prediction: DetailedPrediction;
}) {
  // Guard: check if llmAdjustments exists and is an object
  if (!prediction || !prediction.llmAdjustments || typeof prediction.llmAdjustments !== 'object') {
    return null;
  }

  const adjustments = prediction.llmAdjustments;

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 space-y-3 sm:space-y-4">
      <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-primary-400 flex-shrink-0" />
        Ajustements IA
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
        <AdjustmentCard
          label="Impact Blessures (Domicile)"
          value={adjustments.injuryImpactHome}
          color="orange"
        />
        <AdjustmentCard
          label="Impact Blessures (Exterieur)"
          value={adjustments.injuryImpactAway}
          color="orange"
        />
        <AdjustmentCard
          label="Sentiment (Domicile)"
          value={adjustments.sentimentHome}
          color="blue"
        />
        <AdjustmentCard
          label="Sentiment (Exterieur)"
          value={adjustments.sentimentAway}
          color="blue"
        />
        <AdjustmentCard
          label="Avantage Tactique"
          value={adjustments.tacticalEdge}
          color="primary"
        />
        <AdjustmentCard
          label="Ajustement Total"
          value={adjustments.totalAdjustment}
          color="primary"
          isBold
        />
      </div>

      {adjustments.reasoning && (
        <div className="p-3 sm:p-4 bg-dark-700/50 rounded-lg border border-dark-600">
          <p className="text-xs sm:text-sm text-dark-300 leading-relaxed">
            {adjustments.reasoning}
          </p>
        </div>
      )}
    </div>
  );
}

function AdjustmentCard({
  label,
  value,
  color,
  isBold = false,
}: {
  label: string;
  value: number | undefined;
  color: "primary" | "orange" | "blue";
  isBold?: boolean;
}) {
  const colorClasses: Record<string, string> = {
    primary: "text-primary-400",
    orange: "text-orange-400",
    blue: "text-blue-400",
  };

  const bgColorClasses: Record<string, string> = {
    primary: "bg-primary-500/10 border-primary-500/20",
    orange: "bg-orange-500/10 border-orange-500/20",
    blue: "bg-blue-500/10 border-blue-500/20",
  };

  // Guard: safely check if value is a valid number
  const displayValue = typeof value === 'number' && !isNaN(value)
    ? `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`
    : "-";

  // Ensure color is valid
  const safeColor = color && ['primary', 'orange', 'blue'].includes(color) ? color : 'primary';

  return (
    <div className={cn("p-3 sm:p-4 rounded-lg border", bgColorClasses[safeColor])}>
      <p className="text-dark-400 text-xs sm:text-sm mb-2">{label || "N/A"}</p>
      <p className={cn("text-xl sm:text-2xl font-bold", colorClasses[safeColor], isBold && "font-black")}>
        {displayValue}
      </p>
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
        <span
          className={cn(
            "text-sm font-semibold",
            isRecommended ? textColorClasses[color] : "text-dark-300"
          )}
        >
          {label}
        </span>
        <span
          className={cn(
            "text-sm font-bold",
            isRecommended ? textColorClasses[color] : "text-dark-400"
          )}
        >
          {Math.round(prob * 100)}%
        </span>
      </div>
      <div className="h-3 bg-dark-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            colorClasses[color],
            !isRecommended && "opacity-60"
          )}
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
      {/* Header Skeleton */}
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8 animate-pulse">
        <div className="h-6 bg-dark-700 rounded w-1/3 mb-4" />
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="h-8 bg-dark-700 rounded w-2/3 mx-auto" />
            <div className="h-4 bg-dark-700 rounded w-1/3 mx-auto" />
          </div>
          <div className="h-4 bg-dark-700 rounded w-1/4" />
          <div className="flex-1 space-y-2">
            <div className="h-8 bg-dark-700 rounded w-2/3 mx-auto" />
            <div className="h-4 bg-dark-700 rounded w-1/3 mx-auto" />
          </div>
        </div>
      </div>

      {/* Content Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 animate-pulse"
            >
              <div className="h-6 bg-dark-700 rounded w-1/3 mb-4" />
              <div className="space-y-2">
                <div className="h-4 bg-dark-700 rounded w-full" />
                <div className="h-4 bg-dark-700 rounded w-5/6" />
                <div className="h-4 bg-dark-700 rounded w-4/6" />
              </div>
            </div>
          ))}
        </div>
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 animate-pulse">
          <div className="h-6 bg-dark-700 rounded w-1/2 mb-4" />
          <div className="space-y-2">
            <div className="h-4 bg-dark-700 rounded" />
            <div className="h-4 bg-dark-700 rounded" />
            <div className="h-4 bg-dark-700 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================
   UTILITY FUNCTIONS
   ============================================ */

