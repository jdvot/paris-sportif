"use client";

import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";

interface CompetitionData {
  competition: string;
  total: number;
  won: number;
  lost: number;
  win_rate: number;
}

interface DashboardChartProps {
  data: CompetitionData[];
  winRateLabel: string;
}

export function DashboardChart({ data, winRateLabel }: DashboardChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => v + "%"} />
        <YAxis dataKey="competition" type="category" width={120} className="text-xs" />
        <Tooltip
          formatter={(value: number) => [value.toFixed(1) + "%", winRateLabel]}
        />
        <Bar dataKey="win_rate" radius={[0, 4, 4, 0]}>
          {data.map((entry, index) => (
            <Cell
              key={"cell-" + index}
              fill={entry.win_rate >= 60 ? "hsl(var(--chart-1))" : entry.win_rate >= 50 ? "hsl(var(--chart-2))" : "hsl(var(--chart-3))"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
