"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  useGetMatch,
  useGetHeadToHead,
  useGetTeamForm,
} from "@/lib/api/endpoints/matches/matches";
import { useGetPrediction } from "@/lib/api/endpoints/predictions/predictions";
import type {
  Match,
  HeadToHeadResponse,
  TeamFormResponse,
  PredictionResponse,
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format, parseISO } from "date-fns";
import { fr } from "date-fns/locale";
import { PredictionCharts } from "@/components/PredictionCharts";

// Helper to get team name from Team | string
const getTeamName = (team: Match["home_team"]): string => {
  if (typeof team === "string") return team;
  return team.name || "Unknown";
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

  // Extract data from responses
  const match = (matchResponse as unknown as { data?: Match })?.data;
  const prediction = (predictionResponse as unknown as { data?: PredictionResponse })?.data;
  const headToHead = (h2hResponse as unknown as { data?: HeadToHeadResponse })?.data;

  // Fetch form for both teams - use real team IDs from API
  const homeTeamId = (match as unknown as { home_team_id?: number })?.home_team_id;
  const awayTeamId = (match as unknown as { away_team_id?: number })?.away_team_id;

  const { data: homeFormResponse } = useGetTeamForm(
    homeTeamId!,
    { matches_count: 5 },
    { query: { enabled: !!homeTeamId && homeTeamId > 0 } }
  );

  const { data: awayFormResponse } = useGetTeamForm(
    awayTeamId!,
    { matches_count: 5 },
    { query: { enabled: !!awayTeamId && awayTeamId > 0 } }
  );

  const homeForm = (homeFormResponse as unknown as { data?: TeamFormResponse })?.data;
  const awayForm = (awayFormResponse as unknown as { data?: TeamFormResponse })?.data;

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

          {!predictionLoading && predictionError ? (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 sm:p-6">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 sm:w-6 h-5 sm:h-6 text-red-400 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-white text-sm sm:text-base">Erreur de chargement</h3>
                  <p className="text-xs sm:text-sm text-red-300">
                    {predictionError instanceof Error ? predictionError.message : "Impossible de charger les predictions"}
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          {!predictionLoading && !predictionError && !prediction && (
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

          {prediction && prediction.key_factors && prediction.key_factors.length > 0 && (
            <KeyFactorsSection prediction={prediction} />
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
    </div>
  );
}

/* ============================================
   COMPONENT: Match Header
   ============================================ */
function MatchHeader({ match }: { match: Match }) {
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
    scheduled: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    live: "bg-red-500/20 text-red-300 border-red-500/30 animate-pulse",
    finished: "bg-gray-500/20 text-gray-300 border-gray-500/30",
    postponed: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  };

  const status = typeof match?.status === 'string' ? match.status : 'scheduled';
  const competition = typeof match?.competition === 'string' ? match.competition : 'Competition';
  const homeTeamName = getTeamName(match.home_team);
  const awayTeamName = getTeamName(match.away_team);

  return (
    <div className="bg-gradient-to-r from-dark-800/50 to-dark-900/50 border border-dark-700 rounded-xl overflow-hidden">
      <div className="p-4 sm:p-6 lg:p-8">
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

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 sm:gap-4">
          <div className="flex-1 text-center order-1 sm:order-1">
            <h2 className="text-lg sm:text-xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 break-words">
              {homeTeamName}
            </h2>
            {status === "finished" && typeof match?.home_score === 'number' && (
              <p className="text-2xl sm:text-3xl lg:text-4xl font-bold text-primary-400">
                {match.home_score}
              </p>
            )}
          </div>

          <div className="flex flex-col items-center gap-1 sm:gap-2 px-2 sm:px-4 lg:px-6 order-2 sm:order-2">
            <p className="text-lg sm:text-xl lg:text-2xl font-bold text-dark-400">vs</p>
            <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2 text-dark-400 text-xs sm:text-sm">
              <Clock className="w-3 sm:w-4 h-3 sm:h-4" />
              <span className="text-center">
                {format(matchDate, "dd MMM yyyy", { locale: fr })}
              </span>
              <span className="hidden sm:inline">a</span>
              <span>{format(matchDate, "HH:mm", { locale: fr })}</span>
            </div>
          </div>

          <div className="flex-1 text-center order-3 sm:order-3">
            <h2 className="text-lg sm:text-xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 break-words">
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

  const recommendedBet = prediction?.recommended_bet ?? '';
  const isHomeRecommended = recommendedBet === "home" || recommendedBet === "home_win";
  const isAwayRecommended = recommendedBet === "away" || recommendedBet === "away_win";

  return (
    <div className="space-y-4 sm:space-y-6">
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

        <div className="flex items-start sm:items-center gap-3 p-3 sm:p-4 bg-primary-500/10 border border-primary-500/30 rounded-lg">
          <CheckCircle className="w-5 sm:w-6 h-5 sm:h-6 text-primary-400 flex-shrink-0 mt-0.5 sm:mt-0" />
          <div className="min-w-0">
            <p className="text-primary-400 font-bold text-sm sm:text-base">
              {betLabels[recommendedBet] || "Prediction indisponible"}
            </p>
            <p className="text-xs sm:text-sm text-primary-300">
              Cote Value: +{typeof prediction?.value_score === 'number' && !isNaN(prediction.value_score)
                ? Math.round(prediction.value_score * 100)
                : 0}%
            </p>
          </div>
        </div>

        {(typeof prediction?.expected_home_goals === 'number' || typeof prediction?.expected_away_goals === 'number') && (
          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4">
              <p className="text-dark-400 text-xs sm:text-sm mb-1">Buts attendus (Domicile)</p>
              <p className="text-2xl sm:text-3xl font-bold text-primary-400">
                {typeof prediction?.expected_home_goals === 'number' && !isNaN(prediction.expected_home_goals)
                  ? prediction.expected_home_goals.toFixed(2)
                  : "-"}
              </p>
            </div>
            <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4">
              <p className="text-dark-400 text-xs sm:text-sm mb-1">Buts attendus (Exterieur)</p>
              <p className="text-2xl sm:text-3xl font-bold text-accent-400">
                {typeof prediction?.expected_away_goals === 'number' && !isNaN(prediction.expected_away_goals)
                  ? prediction.expected_away_goals.toFixed(2)
                  : "-"}
              </p>
            </div>
          </div>
        )}

        {prediction.explanation && (
          <div className="p-3 sm:p-4 bg-dark-700/50 rounded-lg border border-dark-600">
            <p className="text-dark-300 text-sm leading-relaxed">
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
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 space-y-3 sm:space-y-4">
      <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-accent-400 flex-shrink-0" />
        Facteurs Cles
      </h3>

      {keyFactors.length > 0 && (
        <div className="space-y-2">
          {keyFactors.map((factor, index) => (
            <div key={index} className="flex items-start gap-3 p-3 bg-dark-700/50 rounded-lg">
              <CheckCircle className="w-4 sm:w-5 h-4 sm:h-5 text-primary-400 flex-shrink-0 mt-0.5" />
              <p className="text-dark-200 text-sm">{factor}</p>
            </div>
          ))}
        </div>
      )}

      {riskFactors.length > 0 && (
        <div className="space-y-2 pt-3 sm:pt-4 border-t border-dark-700">
          <h4 className="text-xs sm:text-sm font-semibold text-yellow-400">Facteurs de Risque</h4>
          {riskFactors.map((factor, index) => (
            <div key={index} className="flex items-start gap-3 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
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
  homeForm: TeamFormResponse;
  awayForm: TeamFormResponse;
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

function TeamFormCard({ form, isHome }: { form: TeamFormResponse; isHome: boolean }) {
  if (!form) {
    return (
      <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4">
        <p className="text-dark-400 text-sm">Donnees non disponibles</p>
      </div>
    );
  }

  const formString = form.form_string || "";
  const formResults = formString.split("").filter(Boolean).slice(0, 5);
  const color = isHome ? "primary" : "accent";

  return (
    <div className="bg-dark-700/50 rounded-lg p-3 sm:p-4 space-y-3 sm:space-y-4">
      <div>
        <h4 className="font-bold text-white text-sm sm:text-base mb-1">{form.team_name}</h4>
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
              <div key={i} className={cn("flex-1 h-7 sm:h-8 rounded flex items-center justify-center text-white font-semibold text-xs sm:text-sm", bgColor)}>
                {displayLabel}
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs sm:text-sm">
        <div>
          <p className="text-dark-400">Points (5 derniers)</p>
          <p className="text-base sm:text-lg font-bold text-white">{form.points_last_5 ?? "-"}</p>
        </div>
        <div>
          <p className="text-dark-400">Buts marques/match</p>
          <p className="text-base sm:text-lg font-bold text-primary-400">
            {typeof form.goals_scored_avg === 'number' ? form.goals_scored_avg.toFixed(1) : "-"}
          </p>
        </div>
        <div>
          <p className="text-dark-400">Buts encaisses/match</p>
          <p className="text-base sm:text-lg font-bold text-orange-400">
            {typeof form.goals_conceded_avg === 'number' ? form.goals_conceded_avg.toFixed(1) : "-"}
          </p>
        </div>
        <div>
          <p className="text-dark-400">Matchs sans encaisser</p>
          <p className="text-base sm:text-lg font-bold text-accent-400">{form.clean_sheets ?? "-"}</p>
        </div>
      </div>

      {(form.xg_for_avg !== null || form.xg_against_avg !== null) && (
        <div className="grid grid-cols-2 gap-2 text-xs sm:text-sm border-t border-dark-600 pt-2 sm:pt-3">
          <div>
            <p className="text-dark-400">xG pour/match</p>
            <p className="text-base sm:text-lg font-bold text-primary-300">
              {typeof form.xg_for_avg === 'number' ? form.xg_for_avg.toFixed(2) : "-"}
            </p>
          </div>
          <div>
            <p className="text-dark-400">xG contre/match</p>
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
   COMPONENT: Head to Head Section
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
  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 space-y-6 sticky top-8">
      <h3 className="text-xl font-bold text-white flex items-center gap-2">
        <Users className="w-5 h-5 text-accent-400" />
        Head-to-Head
      </h3>

      <div className="space-y-3">
        <div className="flex items-center justify-between p-3 bg-primary-500/10 border border-primary-500/20 rounded-lg">
          <span className="text-primary-300 font-semibold">Victoires {homeTeam}</span>
          <span className="text-2xl font-bold text-primary-400">{headToHead.home_wins ?? 0}</span>
        </div>
        <div className="flex items-center justify-between p-3 bg-gray-500/10 border border-gray-500/20 rounded-lg">
          <span className="text-gray-300 font-semibold">Matchs nuls</span>
          <span className="text-2xl font-bold text-gray-400">{headToHead.draws ?? 0}</span>
        </div>
        <div className="flex items-center justify-between p-3 bg-accent-500/10 border border-accent-500/20 rounded-lg">
          <span className="text-accent-300 font-semibold">Victoires {awayTeam}</span>
          <span className="text-2xl font-bold text-accent-400">{headToHead.away_wins ?? 0}</span>
        </div>
      </div>

      {headToHead.matches && headToHead.matches.length > 0 && (
        <div className="space-y-2 border-t border-dark-700 pt-4">
          <h4 className="text-sm font-semibold text-dark-300">Derniers Matchs</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {headToHead.matches.map((match) => {
              const matchHomeTeam = getTeamName(match.home_team);
              const matchAwayTeam = getTeamName(match.away_team);

              let scoreDisplay = "";
              if (match.status === "finished" && match.home_score !== null && match.away_score !== null) {
                scoreDisplay = `${match.home_score} - ${match.away_score}`;
              } else if (match.match_date) {
                try {
                  scoreDisplay = format(parseISO(match.match_date), "dd MMM yyyy", { locale: fr });
                } catch {
                  scoreDisplay = "Date invalide";
                }
              }

              return (
                <div key={match.id} className="p-2 bg-dark-700/50 rounded text-xs space-y-1">
                  <p className="font-semibold text-dark-100">{matchHomeTeam} vs {matchAwayTeam}</p>
                  <p className="text-dark-400">{scoreDisplay}</p>
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
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-accent-400 flex-shrink-0" />
          Modeles de Prediction
        </h3>
        <span className="text-xs sm:text-sm text-dark-400">{models.length} modeles combines</span>
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
    <div className={cn("bg-dark-700/50 rounded-lg p-3 sm:p-4 space-y-3 border-l-2", outcomeColors[predictedOutcome])}>
      <div className="flex items-start gap-2">
        <span className="text-lg">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm sm:text-base font-semibold truncate">{displayName[modelName] || modelName}</p>
          <p className="text-xs text-dark-400">Poids: {weight}</p>
        </div>
      </div>
      <p className="text-xs text-dark-400 line-clamp-2">{description}</p>
      <div className="space-y-1.5 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-dark-400">Domicile:</span>
          <span className="text-primary-400 font-semibold">{Math.round(homeProb * 100)}%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-dark-400">Nul:</span>
          <span className="text-yellow-400 font-semibold">{Math.round(drawProb * 100)}%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-dark-400">Exterieur:</span>
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
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
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
        <div className="bg-dark-700/30 rounded-lg p-3 sm:p-4">
          <h4 className="font-semibold text-white text-sm mb-2">🏥 Impact Blessures</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-dark-400">Domicile</p>
              <p className="text-orange-400 font-bold">{formatAdjustment(adjustments.injury_impact_home)}</p>
            </div>
            <div>
              <p className="text-dark-400">Exterieur</p>
              <p className="text-orange-400 font-bold">{formatAdjustment(adjustments.injury_impact_away)}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-700/30 rounded-lg p-3 sm:p-4">
          <h4 className="font-semibold text-white text-sm mb-2">💭 Sentiment & Moral</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-dark-400">Domicile</p>
              <p className="text-blue-400 font-bold">{formatAdjustment(adjustments.sentiment_home)}</p>
            </div>
            <div>
              <p className="text-dark-400">Exterieur</p>
              <p className="text-blue-400 font-bold">{formatAdjustment(adjustments.sentiment_away)}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-700/30 rounded-lg p-3 sm:p-4 sm:col-span-2">
          <h4 className="font-semibold text-white text-sm mb-2">⚔️ Avantage Tactique</h4>
          <p className="text-primary-400 font-bold text-lg">{formatAdjustment(adjustments.tactical_edge)}</p>
        </div>
      </div>

      {adjustments.reasoning && (
        <div className="p-3 sm:p-4 bg-gradient-to-r from-primary-500/10 to-accent-500/10 rounded-lg border border-primary-500/20">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🤖</span>
            <h4 className="font-semibold text-white text-sm sm:text-base">Raisonnement IA</h4>
          </div>
          <p className="text-xs sm:text-sm text-dark-300 leading-relaxed">{adjustments.reasoning}</p>
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
        <span className={cn("text-sm font-semibold", isRecommended ? textColorClasses[color] : "text-dark-300")}>
          {label}
        </span>
        <span className={cn("text-sm font-bold", isRecommended ? textColorClasses[color] : "text-dark-400")}>
          {Math.round(prob * 100)}%
        </span>
      </div>
      <div className="h-3 bg-dark-700 rounded-full overflow-hidden">
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
      <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-8 animate-pulse">
        <div className="h-6 bg-dark-700 rounded w-1/3 mb-4" />
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="h-8 bg-dark-700 rounded w-2/3 mx-auto" />
          </div>
          <div className="h-4 bg-dark-700 rounded w-1/4" />
          <div className="flex-1 space-y-2">
            <div className="h-8 bg-dark-700 rounded w-2/3 mx-auto" />
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {[1, 2].map((i) => (
            <div key={i} className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 animate-pulse">
              <div className="h-6 bg-dark-700 rounded w-1/3 mb-4" />
              <div className="space-y-2">
                <div className="h-4 bg-dark-700 rounded w-full" />
                <div className="h-4 bg-dark-700 rounded w-5/6" />
              </div>
            </div>
          ))}
        </div>
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 animate-pulse">
          <div className="h-6 bg-dark-700 rounded w-1/2 mb-4" />
          <div className="space-y-2">
            <div className="h-4 bg-dark-700 rounded" />
            <div className="h-4 bg-dark-700 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}
