"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import dynamic from "next/dynamic";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Trophy,
  DollarSign,
  Loader2,
  AlertCircle,
} from "lucide-react";

const DashboardChart = dynamic(() => import("@/components/DashboardChart").then(m => ({ default: m.DashboardChart })), { ssr: false });
import { useGetPredictionStats } from "@/lib/api/endpoints/predictions/predictions";
import type { PredictionStatsResponse } from "@/lib/api/models";
import { getCompetitionName } from "@/lib/constants";

// Default stats when no data is available
const defaultStats = {
  total_predictions: 0,
  verified_predictions: 0,
  correct_predictions: 0,
  accuracy: 0,
  roi_simulated: 0,
  by_competition: {},
  by_bet_type: {},
};

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const [period, setPeriod] = useState("30");

  // Fetch real stats from API
  const { data: response, isLoading, error } = useGetPredictionStats(
    { days: parseInt(period) },
    { query: { staleTime: 5 * 60 * 1000, retry: 2 } }
  );

  // Extract stats from response
  const apiStats = (response?.data as PredictionStatsResponse | undefined);
  const stats = apiStats || defaultStats;

  // Calculate derived values
  const totalPredictions = stats.total_predictions || 0;
  const verifiedPredictions = stats.verified_predictions || 0;
  const correctPredictions = stats.correct_predictions || 0;
  const accuracy = stats.accuracy || 0;
  const roi = stats.roi_simulated || 0;

  // Calculate win/loss from verified predictions
  const won = correctPredictions;
  const lost = verifiedPredictions - correctPredictions;
  const pending = totalPredictions - verifiedPredictions;

  // Convert by_competition to array for chart
  const byCompetitionData = Object.entries(stats.by_competition || {}).map(([code, data]) => {
    const compData = data as { total?: number; correct?: number; accuracy?: number };
    return {
      competition: getCompetitionName(code),
      total: compData.total || 0,
      won: compData.correct || 0,
      lost: (compData.total || 0) - (compData.correct || 0),
      win_rate: (compData.accuracy || 0) * 100,
    };
  });

  // Estimated profit calculation based on ROI (hypothetical €10 stake per bet)
  // NOTE: This is illustrative only - actual profit depends on user's real stakes
  const stakePerBet = 10;
  const totalStake = totalPredictions * stakePerBet;
  const profit = totalStake * (roi / 100);

  const statCards = [
    {
      title: t("totalPredictions"),
      value: totalPredictions,
      icon: Target,
      description: pending > 0 ? t("pending", { count: pending }) : t("allVerified"),
    },
    {
      title: t("winRate"),
      value: verifiedPredictions > 0 ? `${(accuracy * 100).toFixed(1)}%` : "N/A",
      icon: Trophy,
      description: verifiedPredictions > 0 ? `${won}W - ${lost}L` : t("noVerifiedBets"),
      positive: accuracy > 0.5,
    },
    {
      title: t("roi"),
      value: verifiedPredictions > 0 ? `${roi > 0 ? "+" : ""}${roi.toFixed(1)}%` : "N/A",
      icon: roi >= 0 ? TrendingUp : TrendingDown,
      description: t("roiDesc"),
      positive: roi > 0,
    },
    {
      title: t("estProfit"),
      value: verifiedPredictions > 0 ? `€${profit.toFixed(2)}` : "N/A",
      icon: DollarSign,
      description: t("staked", { amount: `€${totalStake.toFixed(0)}` }),
      positive: profit > 0,
    },
  ];

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-muted-foreground">{t("loading")}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <Card className="border-red-500/30 bg-red-500/5">
          <CardContent className="p-6 flex items-start gap-4">
            <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-red-500">{t("errorTitle")}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {t("errorMessage")}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t("title")}</h1>
          <p className="text-muted-foreground">
            {t("subtitle")}
          </p>
        </div>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[180px] focus:ring-2 focus:ring-primary focus:ring-offset-2">
            <SelectValue placeholder={t("selectPeriod")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">{t("last7days")}</SelectItem>
            <SelectItem value="30">{t("last30days")}</SelectItem>
            <SelectItem value="90">{t("last90days")}</SelectItem>
            <SelectItem value="365">{t("lastYear")}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon
                className={"h-4 w-4 " + (
                  stat.positive === undefined
                    ? "text-muted-foreground"
                    : stat.positive
                    ? "text-green-500"
                    : "text-red-500"
                )}
              />
            </CardHeader>
            <CardContent>
              <div
                className={"text-2xl font-bold " + (
                  stat.positive === undefined
                    ? ""
                    : stat.positive
                    ? "text-green-500"
                    : "text-red-500"
                )}
              >
                {stat.value}
              </div>
              <p className="text-xs text-muted-foreground">{stat.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {totalPredictions === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <Target className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">{t("noPredictions")}</h3>
            <p className="text-muted-foreground">
              {t("noPredictionsDesc")}
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <Tabs defaultValue="competitions" className="space-y-4">
            <TabsList>
              <TabsTrigger value="competitions" className="focus:ring-2 focus:ring-primary focus:ring-offset-1">
                {t("byCompetition")}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="competitions" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>{t("performanceByCompetition")}</CardTitle>
                  <CardDescription>
                    {t("winRateAcrossLeagues")}
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-[300px]">
                  {byCompetitionData.length > 0 ? (
                    <DashboardChart data={byCompetitionData} winRateLabel={t("winRate")} />
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      {t("noCompetitionData")}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {byCompetitionData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t("detailedStats")}</CardTitle>
                <CardDescription>
                  {t("breakdownByCompetition")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {byCompetitionData.map((comp) => (
                    <div
                      key={comp.competition}
                      className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
                    >
                      <div className="flex items-center gap-3">
                        <div className="font-medium">{comp.competition}</div>
                        <Badge variant="outline">{t("picks", { count: comp.total })}</Badge>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-sm">
                          <span className="text-green-500">{comp.won}W</span>
                          {" - "}
                          <span className="text-red-500">{comp.lost}L</span>
                        </div>
                        <Badge
                          variant={comp.win_rate >= 60 ? "default" : comp.win_rate >= 50 ? "secondary" : "destructive"}
                        >
                          {comp.win_rate.toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
