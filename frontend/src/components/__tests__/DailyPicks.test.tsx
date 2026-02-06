import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock the API hook
vi.mock("@/lib/api/endpoints/predictions/predictions", () => ({
  useGetDailyPicks: vi.fn(),
}));

// Mock custom-instance
vi.mock("@/lib/api/custom-instance", () => ({
  customInstance: vi.fn().mockResolvedValue({ data: { picks: [] } }),
}));

// Mock utils
vi.mock("@/lib/utils", () => ({
  cn: (...args: string[]) => args.filter(Boolean).join(" "),
  isAuthError: () => false,
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

// Mock LoadingState
vi.mock("@/components/LoadingState", () => ({
  LoadingState: ({ message }: { message?: string }) => (
    <div data-testid="loading-state">{message || "Loading..."}</div>
  ),
}));

// Mock ValueBetBadge
vi.mock("@/components/ValueBetBadge", () => ({
  ValueBetIndicator: () => <span data-testid="value-bet">VB</span>,
}));

// Mock constants
vi.mock("@/lib/constants", () => ({
  getConfidenceTier: (confidence: number) => ({
    label: confidence >= 0.7 ? "High" : "Medium",
    textClass: "text-green-500",
    bgClass: "bg-green-100",
    color: "green",
    min: 0.5,
  }),
  formatConfidence: (c: number) => `${Math.round(c * 100)}%`,
  formatValue: (v: number) => v.toFixed(2),
  isValueBet: (v: number) => v > 1.1,
}));

import { useGetDailyPicks } from "@/lib/api/endpoints/predictions/predictions";

const mockDailyPicks = [
  {
    rank: 1,
    prediction: {
      match_id: 101,
      home_team: "PSG",
      away_team: "Marseille",
      competition: "Ligue 1",
      match_date: "2026-02-10T21:00:00Z",
      confidence: 0.78,
      value_score: 1.3,
      recommended_bet: "home_win",
      probabilities: { home_win: 0.65, draw: 0.20, away_win: 0.15 },
      explanation: "PSG dominant at home this season.",
      key_factors: ["Home advantage", "Form", "Injuries"],
    },
  },
  {
    rank: 2,
    prediction: {
      match_id: 102,
      home_team: "Liverpool",
      away_team: "Man City",
      competition: "Premier League",
      match_date: "2026-02-11T17:30:00Z",
      confidence: 0.62,
      value_score: 0.9,
      recommended_bet: "draw",
      probabilities: { home_win: 0.35, draw: 0.35, away_win: 0.30 },
      explanation: "Very tight match expected.",
      key_factors: ["Top 2 clash", "Equal form"],
    },
  },
];

describe("DailyPicks", () => {
  it("should render loading state", async () => {
    vi.mocked(useGetDailyPicks).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useGetDailyPicks>);

    const { DailyPicks } = await import("../DailyPicks");
    render(<DailyPicks />);
    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
  });

  it("should render without crashing on error", async () => {
    vi.mocked(useGetDailyPicks).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("API error"),
    } as ReturnType<typeof useGetDailyPicks>);

    const { DailyPicks } = await import("../DailyPicks");
    const { container } = render(<DailyPicks />);
    // Component should render something (error state or fallback)
    expect(container.firstChild).toBeTruthy();
  });

  it("should render picks with team names", async () => {
    vi.mocked(useGetDailyPicks).mockReturnValue({
      data: { data: { picks: mockDailyPicks, generated_at: "2026-02-10T10:00:00Z" } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetDailyPicks>);

    const { DailyPicks } = await import("../DailyPicks");
    render(<DailyPicks />);
    expect(screen.getByText("PSG vs Marseille")).toBeInTheDocument();
    expect(screen.getByText("Liverpool vs Man City")).toBeInTheDocument();
  });

  it("should render rank numbers", async () => {
    vi.mocked(useGetDailyPicks).mockReturnValue({
      data: { data: { picks: mockDailyPicks, generated_at: "2026-02-10T10:00:00Z" } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetDailyPicks>);

    const { DailyPicks } = await import("../DailyPicks");
    render(<DailyPicks />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("should render confidence scores", async () => {
    vi.mocked(useGetDailyPicks).mockReturnValue({
      data: { data: { picks: mockDailyPicks, generated_at: "2026-02-10T10:00:00Z" } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetDailyPicks>);

    const { DailyPicks } = await import("../DailyPicks");
    render(<DailyPicks />);
    expect(screen.getByText(/78%/)).toBeInTheDocument();
  });

  it("should render key factors", async () => {
    vi.mocked(useGetDailyPicks).mockReturnValue({
      data: { data: { picks: mockDailyPicks, generated_at: "2026-02-10T10:00:00Z" } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetDailyPicks>);

    const { DailyPicks } = await import("../DailyPicks");
    render(<DailyPicks />);
    expect(screen.getByText("Home advantage")).toBeInTheDocument();
  });

  it("should render probability bars with progressbar role", async () => {
    vi.mocked(useGetDailyPicks).mockReturnValue({
      data: { data: { picks: mockDailyPicks, generated_at: "2026-02-10T10:00:00Z" } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetDailyPicks>);

    const { DailyPicks } = await import("../DailyPicks");
    render(<DailyPicks />);
    const progressBars = screen.getAllByRole("progressbar");
    expect(progressBars.length).toBeGreaterThan(0);
  });

  it("should have aria-labels on pick links", async () => {
    vi.mocked(useGetDailyPicks).mockReturnValue({
      data: { data: { picks: mockDailyPicks, generated_at: "2026-02-10T10:00:00Z" } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetDailyPicks>);

    const { DailyPicks } = await import("../DailyPicks");
    const { container } = render(<DailyPicks />);
    const links = container.querySelectorAll("a[aria-label]");
    expect(links.length).toBeGreaterThan(0);
  });
});
