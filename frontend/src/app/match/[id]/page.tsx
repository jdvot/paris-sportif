"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
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
  const matchId = Number(params.id);

  const { data: match, isLoading: matchLoading, error: matchError } = useQuery({
    queryKey: ["match", matchId],
    queryFn: () => fetchMatch(matchId),
    enabled: !!matchId,
  });

  const { data: prediction, isLoading: predictionLoading, error: predictionError } = useQuery({
    queryKey: ["prediction", matchId],
    queryFn: () => fetchPrediction(matchId, true),
    enabled: !!matchId,
    retry: false, // Don't retry on 500 errors
  });

  const { data: headToHead } = useQuery({
    queryKey: ["headToHead", matchId],
    queryFn: () => fetchHeadToHead(matchId, 10),
    enabled: !!match,
  });

  // Fetch form for both teams
  const homeTeamId = match?.homeTeam
    ? Math.abs(hash(match.homeTeam) % 10000)
    : null;
  const awayTeamId = match?.awayTeam
    ? Math.abs(hash(match.awayTeam) % 10000)
    : null;

  const { data: homeForm } = useQuery({
    queryKey: ["teamForm", homeTeamId],
    queryFn: () => fetchTeamForm(homeTeamId!, 5),
    enabled: !!homeTeamId,
  });

  const { data: awayForm } = useQuery({
    queryKey: ["teamForm", awayTeamId],
    queryFn: () => fetchTeamForm(awayTeamId!, 5),
    enabled: !!awayTeamId,
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
    <div className="space-y-6">
      {/* Match Header */}
      <MatchHeader match={match} />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Prediction */}
        <div className="lg:col-span-2 space-y-6">
          {predictionLoading && (
            <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
              <div className="animate-pulse space-y-4">
                <div className="h-6 bg-dark-700 rounded w-1/3"></div>
                <div className="h-20 bg-dark-700 rounded"></div>
              </div>
            </div>
          )}

          {!predictionLoading && !prediction && (
            <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6">
              <div className="flex items-center gap-3 text-dark-400">
                <Target className="w-6 h-6" />
                <div>
                  <h3 className="font-semibold text-white">Predictions non disponibles</h3>
                  <p className="text-sm">Les predictions pour ce match seront bientot disponibles.</p>
                </div>
              </div>
            </div>
          )}

          {prediction && <PredictionSection prediction={prediction} />}

          {prediction && <KeyFactorsSection prediction={prediction} />}

          {homeForm && awayForm && (
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
  const matchDate = parseISO(match.matchDate);
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

  return (
    <div className="bg-gradient-to-r from-dark-800/50 to-dark-900/50 border border-dark-700 rounded-xl overflow-hidden">
      <div className="p-8">
        {/* Competition and Status */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-accent-400" />
            <span className="text-accent-400 font-semibold">
              {match.competition}
            </span>
            {match.matchday && (
              <span className="text-dark-400 text-sm">
                • Journee {match.matchday}
              </span>
            )}
          </div>
          <div
            className={cn(
              "px-3 py-1 rounded-lg border font-semibold text-sm",
              statusColors[match.status]
            )}
          >
            {statusLabels[match.status]}
          </div>
        </div>

        {/* Teams and Score */}
        <div className="flex items-center justify-between gap-4">
          {/* Home Team */}
          <div className="flex-1 text-center">
            <h2 className="text-3xl font-bold text-white mb-2">
              {match.homeTeam}
            </h2>
            {match.status === "finished" && match.homeScore !== undefined && (
              <p className="text-4xl font-bold text-primary-400">
                {match.homeScore}
              </p>
            )}
          </div>

          {/* VS and Date */}
          <div className="flex flex-col items-center gap-2 px-6">
            <p className="text-2xl font-bold text-dark-400">vs</p>
            <div className="flex items-center gap-2 text-dark-400 text-sm whitespace-nowrap">
              <Clock className="w-4 h-4" />
              <span>
                {format(matchDate, "dd MMM yyyy 'a' HH:mm", { locale: fr })}
              </span>
            </div>
          </div>

          {/* Away Team */}
          <div className="flex-1 text-center">
            <h2 className="text-3xl font-bold text-white mb-2">
              {match.awayTeam}
            </h2>
            {match.status === "finished" && match.awayScore !== undefined && (
              <p className="text-4xl font-bold text-accent-400">
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

  const confidence = prediction.confidence ?? 0;
  const confidenceColor =
    confidence >= 0.7
      ? "text-primary-400"
      : confidence >= 0.6
        ? "text-yellow-400"
        : "text-orange-400";

  // Support both API formats
  const homeProb = prediction.homeProb ?? prediction.probabilities?.homeWin ?? 0;
  const drawProb = prediction.drawProb ?? prediction.probabilities?.draw ?? 0;
  const awayProb = prediction.awayProb ?? prediction.probabilities?.awayWin ?? 0;
  const isHomeRecommended = prediction.recommendedBet === "home" || prediction.recommendedBet === "home_win";
  const isAwayRecommended = prediction.recommendedBet === "away" || prediction.recommendedBet === "away_win";

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Target className="w-6 h-6 text-primary-400" />
          Prediction
        </h2>
        <div className={cn("text-right", confidenceColor)}>
          <p className="font-bold text-lg">
            {Math.round(confidence * 100)}%
          </p>
          <p className="text-xs text-dark-300">Confiance</p>
        </div>
      </div>

      {/* Probabilities */}
      <div className="space-y-4">
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
      <div className="flex items-center gap-3 p-4 bg-primary-500/10 border border-primary-500/30 rounded-lg">
        <CheckCircle className="w-6 h-6 text-primary-400 flex-shrink-0" />
        <div>
          <p className="text-primary-400 font-bold">
            {betLabels[prediction.recommendedBet]}
          </p>
          <p className="text-sm text-primary-300">
            Cote Value: +{Math.round((prediction.valueScore ?? 0) * 100)}%
          </p>
        </div>
      </div>

      {/* Expected Goals */}
      {(prediction.expectedHomeGoals !== undefined || prediction.expectedAwayGoals !== undefined) && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-dark-700/50 rounded-lg p-4">
            <p className="text-dark-400 text-sm mb-1">Buts attendus (Domicile)</p>
            <p className="text-3xl font-bold text-primary-400">
              {prediction.expectedHomeGoals?.toFixed(2) ?? "-"}
            </p>
          </div>
          <div className="bg-dark-700/50 rounded-lg p-4">
            <p className="text-dark-400 text-sm mb-1">Buts attendus (Exterieur)</p>
            <p className="text-3xl font-bold text-accent-400">
              {prediction.expectedAwayGoals?.toFixed(2) ?? "-"}
            </p>
          </div>
        </div>
      )}

      {/* Explanation */}
      {prediction.explanation && (
        <div className="p-4 bg-dark-700/50 rounded-lg border border-dark-600">
          <p className="text-dark-300 leading-relaxed">
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
  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 space-y-4">
      <h3 className="text-xl font-bold text-white flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-accent-400" />
        Facteurs Cles
      </h3>

      <div className="space-y-2">
        {prediction.keyFactors.map((factor, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-3 bg-dark-700/50 rounded-lg"
          >
            <CheckCircle className="w-5 h-5 text-primary-400 flex-shrink-0 mt-0.5" />
            <p className="text-dark-200">{factor}</p>
          </div>
        ))}
      </div>

      {prediction.riskFactors && prediction.riskFactors.length > 0 && (
        <div className="space-y-2 pt-4 border-t border-dark-700">
          <h4 className="text-sm font-semibold text-yellow-400">
            Facteurs de Risque
          </h4>
          {prediction.riskFactors.map((factor, index) => (
            <div
              key={index}
              className="flex items-start gap-3 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20"
            >
              <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-yellow-200 text-sm">{factor}</p>
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
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 space-y-6">
      <h3 className="text-xl font-bold text-white flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-primary-400" />
        Forme Recente
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <TeamFormCard form={homeForm} isHome={true} />
        <TeamFormCard form={awayForm} isHome={false} />
      </div>
    </div>
  );
}

function TeamFormCard({ form, isHome }: { form: TeamForm; isHome: boolean }) {
  const formString = form.formString || "VVVVV";
  const formResults = formString.split("").slice(0, 5);
  const color = isHome ? "primary" : "accent";

  return (
    <div className="bg-dark-700/50 rounded-lg p-4 space-y-4">
      <div>
        <h4 className="font-bold text-white mb-1">{form.teamName}</h4>
        <p className={cn("text-sm font-mono", color === "primary" ? "text-primary-400" : "text-accent-400")}>
          {formString}
        </p>
      </div>

      {/* Last 5 matches */}
      <div className="flex gap-2">
        {formResults.map((result, i) => {
          const bgColor =
            result === "V"
              ? "bg-primary-500"
              : result === "D"
                ? "bg-gray-500"
                : "bg-red-500";
          return (
            <div
              key={i}
              className={cn(
                "flex-1 h-8 rounded flex items-center justify-center text-white font-semibold text-sm",
                bgColor
              )}
            >
              {result === "V" ? "V" : result === "D" ? "N" : "D"}
            </div>
          );
        })}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-dark-400">Points (5 derniers)</p>
          <p className="text-lg font-bold text-white">
            {form.pointsLast5 ?? "-"}
          </p>
        </div>
        <div>
          <p className="text-dark-400">Buts marques/match</p>
          <p className="text-lg font-bold text-primary-400">
            {form.goalsScoredAvg?.toFixed(1) ?? "-"}
          </p>
        </div>
        <div>
          <p className="text-dark-400">Buts encaisses/match</p>
          <p className="text-lg font-bold text-orange-400">
            {form.goalsConcededAvg?.toFixed(1) ?? "-"}
          </p>
        </div>
        <div>
          <p className="text-dark-400">Matchs sans encaisser</p>
          <p className="text-lg font-bold text-accent-400">
            {form.cleanSheets ?? "-"}
          </p>
        </div>
      </div>

      {/* xG Stats if available */}
      {(form.xgForAvg !== undefined || form.xgAgainstAvg !== undefined) && (
        <div className="grid grid-cols-2 gap-2 text-sm border-t border-dark-600 pt-2">
          <div>
            <p className="text-dark-400">xG pour/match</p>
            <p className="text-lg font-bold text-primary-300">
              {form.xgForAvg?.toFixed(2) ?? "-"}
            </p>
          </div>
          <div>
            <p className="text-dark-400">xG contre/match</p>
            <p className="text-lg font-bold text-orange-300">
              {form.xgAgainstAvg?.toFixed(2) ?? "-"}
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
            Victoires {homeTeam}
          </span>
          <span className="text-2xl font-bold text-primary-400">
            {headToHead.homeWins}
          </span>
        </div>
        <div className="flex items-center justify-between p-3 bg-gray-500/10 border border-gray-500/20 rounded-lg">
          <span className="text-gray-300 font-semibold">Matchs nuls</span>
          <span className="text-2xl font-bold text-gray-400">
            {headToHead.draws}
          </span>
        </div>
        <div className="flex items-center justify-between p-3 bg-accent-500/10 border border-accent-500/20 rounded-lg">
          <span className="text-accent-300 font-semibold">
            Victoires {awayTeam}
          </span>
          <span className="text-2xl font-bold text-accent-400">
            {headToHead.awayWins}
          </span>
        </div>
      </div>

      {/* Recent Matches */}
      {headToHead.matches.length > 0 && (
        <div className="space-y-2 border-t border-dark-700 pt-4">
          <h4 className="text-sm font-semibold text-dark-300">Derniers Matchs</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {headToHead.matches.map((match) => (
              <div
                key={match.id}
                className="p-2 bg-dark-700/50 rounded text-xs space-y-1"
              >
                <p className="font-semibold text-dark-100">
                  {match.homeTeam} vs {match.awayTeam}
                </p>
                <p className="text-dark-400">
                  {match.status === "finished"
                    ? `${match.homeScore} - ${match.awayScore}`
                    : format(parseISO(match.matchDate), "dd MMM yyyy", {
                        locale: fr,
                      })}
                </p>
              </div>
            ))}
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
  if (!prediction.modelContributions) return null;

  const models = Object.entries(prediction.modelContributions);

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 space-y-4">
      <h3 className="text-xl font-bold text-white flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-accent-400" />
        Contributions des Modeles
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {models.map(([modelName, contribution]) => (
          <ModelContributionCard
            key={modelName}
            modelName={modelName}
            contribution={contribution}
          />
        ))}
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

  // Support both formats
  const homeProb = contribution.homeProb ?? contribution.homeWin ?? 0;
  const drawProb = contribution.drawProb ?? contribution.draw ?? 0;
  const awayProb = contribution.awayProb ?? contribution.awayWin ?? 0;
  const weight = contribution.weight ?? 0.25;

  return (
    <div className="bg-dark-700/50 rounded-lg p-4 space-y-2">
      <div>
        <p className="text-dark-300 text-sm font-semibold">
          {displayName[modelName] || modelName}
        </p>
        <p className="text-xs text-dark-400">
          Poids: {Math.round(weight * 100)}%
        </p>
      </div>

      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-dark-400">Domicile:</span>
          <span className="text-primary-400 font-semibold">
            {Math.round(homeProb * 100)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-dark-400">Nul:</span>
          <span className="text-yellow-400 font-semibold">
            {Math.round(drawProb * 100)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-dark-400">Exterieur:</span>
          <span className="text-accent-400 font-semibold">
            {Math.round(awayProb * 100)}%
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
  if (!prediction.llmAdjustments) return null;

  const adjustments = prediction.llmAdjustments;

  return (
    <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 space-y-4">
      <h3 className="text-xl font-bold text-white flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-primary-400" />
        Ajustements IA
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
        <div className="p-4 bg-dark-700/50 rounded-lg border border-dark-600">
          <p className="text-sm text-dark-300 leading-relaxed">
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
  value: number;
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

  const displayValue = value !== undefined && value !== null
    ? `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`
    : "-";

  return (
    <div className={cn("p-4 rounded-lg border", bgColorClasses[color])}>
      <p className="text-dark-400 text-sm mb-2">{label}</p>
      <p className={cn("text-2xl font-bold", colorClasses[color])}>
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

/**
 * Simple hash function to generate consistent team IDs from team names
 */
function hash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return hash;
}
