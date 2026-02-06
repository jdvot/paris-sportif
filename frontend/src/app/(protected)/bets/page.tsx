"use client";

import { useState } from "react";
import { format } from "date-fns";
import { fr, enUS } from "date-fns/locale";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  XCircle,
  Clock,
  Plus,
  Trash2,
  AlertTriangle,
  Calculator,
  PiggyBank,
  BarChart3,
} from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { cn } from "@/lib/utils";
import { logger } from "@/lib/logger";
import {
  useGetBankrollApiV1BetsBankrollGet,
  useListBetsApiV1BetsGet,
  useUpdateBankrollApiV1BetsBankrollPut,
  useCreateBetApiV1BetsPost,
  useUpdateBetApiV1BetsBetIdPatch,
  useDeleteBetApiV1BetsBetIdDelete,
} from "@/lib/api/endpoints/bets-bankroll/bets-bankroll";
import { useGetUpcomingMatches } from "@/lib/api/endpoints/matches/matches";
import type { BankrollResponse, BetResponse } from "@/lib/api/models";
import { useQueryClient } from "@tanstack/react-query";

type TabType = "bets" | "bankroll" | "stats";
type FilterType = "all" | "pending" | "won" | "lost";

export default function BetsPage() {
  const t = useTranslations("bets");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const dateLocale = locale === "fr" ? fr : enUS;
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<TabType>("bets");
  const [filter, setFilter] = useState<FilterType>("all");
  const [showAddForm, setShowAddForm] = useState(false);

  // Form state
  const [formMatchId, setFormMatchId] = useState<number | null>(null);
  const [formPrediction, setFormPrediction] = useState<string>("home_win");
  const [formOdds, setFormOdds] = useState<string>("");
  const [formAmount, setFormAmount] = useState<string>("");
  const [formConfidence, setFormConfidence] = useState<string>("");

  // Bankroll form state
  const [initialBankroll, setInitialBankroll] = useState<string>("");
  const [alertThreshold, setAlertThreshold] = useState<string>("20");
  const [defaultStakePct, setDefaultStakePct] = useState<string>("2");

  // Fetch data
  const { data: bankrollResponse } =
    useGetBankrollApiV1BetsBankrollGet();
  const { data: betsResponse, isLoading: betsLoading } = useListBetsApiV1BetsGet(
    filter === "all" ? undefined : { status: filter }
  );
  const { data: matchesResponse } = useGetUpcomingMatches({ days: 7 });

  // Mutations
  const updateBankrollMutation = useUpdateBankrollApiV1BetsBankrollPut();
  const createBetMutation = useCreateBetApiV1BetsPost();
  const updateBetMutation = useUpdateBetApiV1BetsBetIdPatch();
  const deleteBetMutation = useDeleteBetApiV1BetsBetIdDelete();

  const bankroll = (bankrollResponse?.data as BankrollResponse) || null;
  const bets = (betsResponse?.data as BetResponse[]) || [];
  const matches = (matchesResponse?.data as { matches?: unknown[] })?.matches || [];

  // Handle bankroll save
  const handleSaveBankroll = async () => {
    if (!initialBankroll) return;
    try {
      await updateBankrollMutation.mutateAsync({
        data: {
          initial_bankroll: parseFloat(initialBankroll),
          alert_threshold: parseFloat(alertThreshold),
          default_stake_pct: parseFloat(defaultStakePct),
        },
      });
      queryClient.invalidateQueries({ queryKey: ["/api/v1/bets/bankroll"] });
    } catch (error) {
      logger.error("Failed to update bankroll:", error);
    }
  };

  // Handle add bet
  const handleAddBet = async () => {
    if (!formMatchId || !formOdds || !formAmount) return;
    try {
      await createBetMutation.mutateAsync({
        data: {
          match_id: formMatchId,
          prediction: formPrediction,
          odds: parseFloat(formOdds),
          amount: parseFloat(formAmount),
          confidence: formConfidence ? parseFloat(formConfidence) : undefined,
        },
      });
      queryClient.invalidateQueries({ queryKey: ["/api/v1/bets"] });
      queryClient.invalidateQueries({ queryKey: ["/api/v1/bets/bankroll"] });
      setShowAddForm(false);
      setFormMatchId(null);
      setFormOdds("");
      setFormAmount("");
      setFormConfidence("");
    } catch (error) {
      logger.error("Failed to create bet:", error);
    }
  };

  // Handle update bet status
  const handleUpdateStatus = async (betId: number, status: string) => {
    try {
      await updateBetMutation.mutateAsync({
        betId,
        data: { status },
      });
      queryClient.invalidateQueries({ queryKey: ["/api/v1/bets"] });
      queryClient.invalidateQueries({ queryKey: ["/api/v1/bets/bankroll"] });
    } catch (error) {
      logger.error("Failed to update bet:", error);
    }
  };

  // Handle delete bet
  const handleDeleteBet = async (betId: number) => {
    try {
      await deleteBetMutation.mutateAsync({ betId });
      queryClient.invalidateQueries({ queryKey: ["/api/v1/bets"] });
      queryClient.invalidateQueries({ queryKey: ["/api/v1/bets/bankroll"] });
    } catch (error) {
      logger.error("Failed to delete bet:", error);
    }
  };

  const tabs = [
    { id: "bets" as TabType, label: t("tabs.bets"), icon: Wallet },
    { id: "bankroll" as TabType, label: t("tabs.bankroll"), icon: PiggyBank },
    { id: "stats" as TabType, label: t("tabs.stats"), icon: BarChart3 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Wallet className="w-8 h-8 text-primary-500" />
            {t("title")}
          </h1>
          <p className="text-gray-600 dark:text-dark-400 mt-1">{t("subtitle")}</p>
        </div>
        {activeTab === "bets" && (
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {t("bet.add")}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-dark-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors",
              activeTab === tab.id
                ? "border-primary-500 text-primary-600 dark:text-primary-400"
                : "border-transparent text-gray-500 dark:text-dark-400 hover:text-gray-700 dark:hover:text-dark-300"
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Bankroll Summary (always visible) */}
      {bankroll && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 text-center">
            <PiggyBank className="w-6 h-6 text-primary-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {bankroll.current_bankroll.toFixed(2)}€
            </p>
            <p className="text-xs text-gray-600 dark:text-dark-400">{t("bankroll.current")}</p>
          </div>
          <div
            className={cn(
              "border rounded-xl p-4 text-center",
              bankroll.profit_loss >= 0
                ? "bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/30"
                : "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
            )}
          >
            {bankroll.profit_loss >= 0 ? (
              <TrendingUp className="w-6 h-6 text-green-500 mx-auto mb-2" />
            ) : (
              <TrendingDown className="w-6 h-6 text-red-500 mx-auto mb-2" />
            )}
            <p
              className={cn(
                "text-2xl font-bold",
                bankroll.profit_loss >= 0
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-600 dark:text-red-400"
              )}
            >
              {bankroll.profit_loss >= 0 ? "+" : ""}
              {bankroll.profit_loss.toFixed(2)}€
            </p>
            <p className="text-xs text-gray-600 dark:text-dark-400">{t("bankroll.profitLoss")}</p>
          </div>
          <div
            className={cn(
              "border rounded-xl p-4 text-center",
              bankroll.roi_pct >= 0
                ? "bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/30"
                : "bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
            )}
          >
            <Calculator className="w-6 h-6 text-primary-500 mx-auto mb-2" />
            <p
              className={cn(
                "text-2xl font-bold",
                bankroll.roi_pct >= 0
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-600 dark:text-red-400"
              )}
            >
              {bankroll.roi_pct >= 0 ? "+" : ""}
              {bankroll.roi_pct.toFixed(1)}%
            </p>
            <p className="text-xs text-gray-600 dark:text-dark-400">{t("bankroll.roi")}</p>
          </div>
          <div className="bg-primary-50 dark:bg-primary-500/10 border border-primary-200 dark:border-primary-500/30 rounded-xl p-4 text-center">
            <BarChart3 className="w-6 h-6 text-primary-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">
              {bankroll.win_rate.toFixed(0)}%
            </p>
            <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.winRate")}</p>
          </div>
        </div>
      )}

      {/* Alert if below threshold */}
      {bankroll?.is_below_threshold && (
        <div className="bg-yellow-50 dark:bg-yellow-500/10 border border-yellow-200 dark:border-yellow-500/30 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-yellow-500" />
          <p className="text-yellow-800 dark:text-yellow-300 font-medium">
            {t("bankroll.belowThreshold")}
          </p>
        </div>
      )}

      {/* Tab Content */}
      {activeTab === "bets" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-2">
            {(["all", "pending", "won", "lost"] as FilterType[]).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  "px-3 py-1.5 text-sm rounded-lg transition-colors",
                  filter === f
                    ? "bg-primary-500 text-white"
                    : "bg-gray-100 dark:bg-dark-700 text-gray-600 dark:text-dark-400 hover:bg-gray-200 dark:hover:bg-dark-600"
                )}
              >
                {t(`filter.${f}`)}
              </button>
            ))}
          </div>

          {/* Add Bet Form */}
          {showAddForm && (
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 space-y-4">
              <h3 className="font-semibold text-gray-900 dark:text-white">{t("bet.add")}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 dark:text-dark-400 mb-1">
                    {t("form.selectMatch")}
                  </label>
                  <select
                    value={formMatchId || ""}
                    onChange={(e) => setFormMatchId(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg text-sm"
                  >
                    <option value="">{t("form.selectMatch")}</option>
                    {(matches as { id: number; home_team: string; away_team: string }[]).map((match) => (
                      <option key={match.id} value={match.id}>
                        {match.home_team} vs {match.away_team}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-dark-400 mb-1">
                    {t("form.selectPrediction")}
                  </label>
                  <select
                    value={formPrediction}
                    onChange={(e) => setFormPrediction(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg text-sm"
                  >
                    <option value="home_win">{t("form.homeWin")}</option>
                    <option value="draw">{t("form.draw")}</option>
                    <option value="away_win">{t("form.awayWin")}</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-dark-400 mb-1">
                    {t("bet.odds")}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="1.01"
                    value={formOdds}
                    onChange={(e) => setFormOdds(e.target.value)}
                    placeholder={t("form.enterOdds")}
                    className="w-full px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-dark-400 mb-1">
                    {t("bet.amount")}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formAmount}
                    onChange={(e) => setFormAmount(e.target.value)}
                    placeholder={t("form.enterAmount")}
                    className="w-full px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg text-sm"
                  />
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowAddForm(false)}
                  className="px-4 py-2 text-gray-600 dark:text-dark-400 hover:bg-gray-100 dark:hover:bg-dark-700 rounded-lg transition-colors"
                >
                  {tCommon("cancel")}
                </button>
                <button
                  onClick={handleAddBet}
                  disabled={!formMatchId || !formOdds || !formAmount}
                  className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50"
                >
                  {t("form.submit")}
                </button>
              </div>
            </div>
          )}

          {/* Bets List */}
          {betsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-gray-100 dark:bg-dark-700 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : bets.length === 0 ? (
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-8 text-center">
              <Wallet className="w-12 h-12 text-gray-400 dark:text-dark-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                {t("empty")}
              </h3>
              <p className="text-gray-600 dark:text-dark-400 mb-4">{t("emptyHint")}</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t("bet.add")}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {bets.map((bet) => (
                <div
                  key={bet.id}
                  className={cn(
                    "bg-white dark:bg-dark-800/50 border rounded-xl p-4 transition-all",
                    bet.status === "won"
                      ? "border-green-300 dark:border-green-500/30"
                      : bet.status === "lost"
                      ? "border-red-300 dark:border-red-500/30"
                      : "border-gray-200 dark:border-dark-700"
                  )}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div
                        className={cn(
                          "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0",
                          bet.status === "won"
                            ? "bg-green-100 dark:bg-green-500/20"
                            : bet.status === "lost"
                            ? "bg-red-100 dark:bg-red-500/20"
                            : "bg-yellow-100 dark:bg-yellow-500/20"
                        )}
                      >
                        {bet.status === "won" ? (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        ) : bet.status === "lost" ? (
                          <XCircle className="w-5 h-5 text-red-500" />
                        ) : (
                          <Clock className="w-5 h-5 text-yellow-500" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-gray-900 dark:text-white">
                          {t("bet.match")} #{bet.match_id}
                        </p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-dark-400">
                          <span>
                            {bet.prediction === "home_win"
                              ? t("form.homeWin")
                              : bet.prediction === "draw"
                              ? t("form.draw")
                              : t("form.awayWin")}
                          </span>
                          <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-dark-700 rounded">
                            @{bet.odds.toFixed(2)}
                          </span>
                          <span>{bet.amount.toFixed(2)}€</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-right">
                        <p
                          className={cn(
                            "text-lg font-bold",
                            bet.status === "won"
                              ? "text-green-600 dark:text-green-400"
                              : bet.status === "lost"
                              ? "text-red-600 dark:text-red-400"
                              : "text-gray-900 dark:text-white"
                          )}
                        >
                          {bet.status === "won"
                            ? `+${(bet.actual_return || bet.potential_return - bet.amount).toFixed(2)}€`
                            : bet.status === "lost"
                            ? `-${bet.amount.toFixed(2)}€`
                            : `${bet.potential_return.toFixed(2)}€`}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-dark-400">
                          {format(new Date(bet.created_at), "d MMM", { locale: dateLocale })}
                        </p>
                      </div>
                      {bet.status === "pending" && (
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleUpdateStatus(bet.id, "won")}
                            className="p-1.5 text-green-500 hover:bg-green-100 dark:hover:bg-green-500/20 rounded-lg transition-colors"
                            title={t("bet.markWon")}
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleUpdateStatus(bet.id, "lost")}
                            className="p-1.5 text-red-500 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-lg transition-colors"
                            title={t("bet.markLost")}
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteBet(bet.id)}
                            className="p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-700 rounded-lg transition-colors"
                            title={t("bet.delete")}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "bankroll" && (
        <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t("bankroll.title")}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm text-gray-600 dark:text-dark-400 mb-1">
                {t("bankroll.initial")}
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={initialBankroll || bankroll?.initial_bankroll || ""}
                onChange={(e) => setInitialBankroll(e.target.value)}
                placeholder="1000"
                className="w-full px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 dark:text-dark-400 mb-1">
                {t("bankroll.alertThreshold")}
              </label>
              <input
                type="number"
                step="1"
                min="0"
                max="100"
                value={alertThreshold}
                onChange={(e) => setAlertThreshold(e.target.value)}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg"
              />
              <p className="text-xs text-gray-500 dark:text-dark-500 mt-1">
                {t("bankroll.alertThresholdHint")}
              </p>
            </div>
            <div>
              <label className="block text-sm text-gray-600 dark:text-dark-400 mb-1">
                {t("bankroll.defaultStake")}
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="100"
                value={defaultStakePct}
                onChange={(e) => setDefaultStakePct(e.target.value)}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-dark-700 border border-gray-200 dark:border-dark-600 rounded-lg"
              />
              <p className="text-xs text-gray-500 dark:text-dark-500 mt-1">
                {t("bankroll.defaultStakeHint")}
              </p>
            </div>
          </div>
          <button
            onClick={handleSaveBankroll}
            disabled={!initialBankroll && !bankroll?.initial_bankroll}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50"
          >
            {t("bankroll.save")}
          </button>
        </div>
      )}

      {activeTab === "stats" && bankroll && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{bankroll.total_bets}</p>
              <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.totalBets")}</p>
            </div>
            <div className="bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                {bankroll.won_bets}
              </p>
              <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.won")}</p>
            </div>
            <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {bankroll.lost_bets}
              </p>
              <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.lost")}</p>
            </div>
            <div className="bg-yellow-50 dark:bg-yellow-500/10 border border-yellow-200 dark:border-yellow-500/30 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                {bankroll.pending_bets}
              </p>
              <p className="text-xs text-gray-600 dark:text-dark-400">{t("stats.pending")}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-6">
              <h4 className="font-semibold text-gray-900 dark:text-white mb-4">
                {t("stats.totalStaked")}
              </h4>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {bankroll.total_staked.toFixed(2)}€
              </p>
            </div>
            <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-6">
              <h4 className="font-semibold text-gray-900 dark:text-white mb-4">
                {t("stats.totalReturned")}
              </h4>
              <p
                className={cn(
                  "text-3xl font-bold",
                  bankroll.total_returned >= bankroll.total_staked
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                )}
              >
                {bankroll.total_returned.toFixed(2)}€
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Info Banner */}
      <div className="bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30 rounded-xl p-4">
        <p className="text-sm text-blue-800 dark:text-blue-300">{t("infoBanner")}</p>
      </div>
    </div>
  );
}
