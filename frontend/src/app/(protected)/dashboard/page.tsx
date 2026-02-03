"use client";

import { useState } from "react";
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
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Trophy,
  DollarSign,
} from "lucide-react";

const demoStats = {
  period_days: 30,
  summary: {
    total_predictions: 47,
    won: 28,
    lost: 15,
    pending: 4,
    win_rate: 65.1,
    roi: 12.5,
    total_stake: 470.0,
    total_return: 528.75,
    profit: 58.75,
  },
  by_competition: [
    { competition: "Premier League", total: 18, won: 12, lost: 6, win_rate: 66.7 },
    { competition: "Ligue 1", total: 12, won: 7, lost: 5, win_rate: 58.3 },
    { competition: "La Liga", total: 9, won: 5, lost: 4, win_rate: 55.6 },
    { competition: "Serie A", total: 8, won: 4, lost: 0, win_rate: 100.0 },
  ],
  roi_history: [
    { week: "2026-01-06", roi: 5.2, cumulative_profit: 15.0 },
    { week: "2026-01-13", roi: 8.1, cumulative_profit: 32.0 },
    { week: "2026-01-20", roi: 6.5, cumulative_profit: 28.0 },
    { week: "2026-01-27", roi: 12.5, cumulative_profit: 58.75 },
  ],
};

export default function DashboardPage() {
  const [period, setPeriod] = useState("30");
  const stats = demoStats;

  const statCards = [
    {
      title: "Total Predictions",
      value: stats.summary.total_predictions,
      icon: Target,
      description: stats.summary.pending + " pending",
    },
    {
      title: "Win Rate",
      value: stats.summary.win_rate.toFixed(1) + "%",
      icon: Trophy,
      description: stats.summary.won + "W - " + stats.summary.lost + "L",
      positive: stats.summary.win_rate > 50,
    },
    {
      title: "ROI",
      value: (stats.summary.roi > 0 ? "+" : "") + stats.summary.roi.toFixed(1) + "%",
      icon: stats.summary.roi >= 0 ? TrendingUp : TrendingDown,
      description: "Return on investment",
      positive: stats.summary.roi > 0,
    },
    {
      title: "Profit",
      value: "€" + stats.summary.profit.toFixed(2),
      icon: DollarSign,
      description: "Staked: €" + stats.summary.total_stake,
      positive: stats.summary.profit > 0,
    },
  ];

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Your betting performance and statistics
          </p>
        </div>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
            <SelectItem value="365">Last year</SelectItem>
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

      <Tabs defaultValue="roi" className="space-y-4">
        <TabsList>
          <TabsTrigger value="roi">ROI Evolution</TabsTrigger>
          <TabsTrigger value="competitions">By Competition</TabsTrigger>
        </TabsList>

        <TabsContent value="roi" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>ROI Over Time</CardTitle>
              <CardDescription>
                Cumulative return on investment progression
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stats.roi_history}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="week"
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return date.getDate() + "/" + (date.getMonth() + 1);
                    }}
                    className="text-xs"
                  />
                  <YAxis
                    tickFormatter={(value) => value + "%"}
                    className="text-xs"
                  />
                  <Tooltip
                    formatter={(value: number) => [value.toFixed(1) + "%", "ROI"]}
                    labelFormatter={(label) => "Week of " + label}
                  />
                  <Line
                    type="monotone"
                    dataKey="roi"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={{ fill: "hsl(var(--primary))" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="competitions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance by Competition</CardTitle>
              <CardDescription>
                Win rate across different leagues
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.by_competition} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => v + "%"} />
                  <YAxis dataKey="competition" type="category" width={120} className="text-xs" />
                  <Tooltip
                    formatter={(value: number) => [value.toFixed(1) + "%", "Win Rate"]}
                  />
                  <Bar dataKey="win_rate" radius={[0, 4, 4, 0]}>
                    {stats.by_competition.map((entry, index) => (
                      <Cell
                        key={"cell-" + index}
                        fill={entry.win_rate >= 60 ? "hsl(var(--chart-1))" : entry.win_rate >= 50 ? "hsl(var(--chart-2))" : "hsl(var(--chart-3))"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Detailed Statistics</CardTitle>
          <CardDescription>
            Breakdown by competition
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {stats.by_competition.map((comp) => (
              <div
                key={comp.competition}
                className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
              >
                <div className="flex items-center gap-3">
                  <div className="font-medium">{comp.competition}</div>
                  <Badge variant="outline">{comp.total} picks</Badge>
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
    </div>
  );
}
