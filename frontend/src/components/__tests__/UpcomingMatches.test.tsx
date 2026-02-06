import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { UpcomingMatches } from "../UpcomingMatches";

// Mock the API hook
vi.mock("@/lib/api/endpoints/matches/matches", () => ({
  useGetUpcomingMatches: vi.fn(),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

import { useGetUpcomingMatches } from "@/lib/api/endpoints/matches/matches";

const mockMatches = [
  {
    id: 1,
    external_id: "123",
    home_team: { name: "PSG", logo_url: null },
    away_team: { name: "Lyon", logo_url: null },
    competition: "Ligue 1",
    competition_code: "FL1",
    match_date: "2026-02-10T20:00:00Z",
    status: "SCHEDULED",
  },
  {
    id: 2,
    external_id: "456",
    home_team: { name: "Arsenal", logo_url: null },
    away_team: { name: "Chelsea", logo_url: null },
    competition: "Premier League",
    competition_code: "PL",
    match_date: "2026-02-11T15:00:00Z",
    status: "SCHEDULED",
  },
];

describe("UpcomingMatches", () => {
  it("should render loading state", () => {
    vi.mocked(useGetUpcomingMatches).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as ReturnType<typeof useGetUpcomingMatches>);

    const { container } = render(<UpcomingMatches />);
    const spinner = container.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
  });

  it("should render error state", () => {
    vi.mocked(useGetUpcomingMatches).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
    } as ReturnType<typeof useGetUpcomingMatches>);

    render(<UpcomingMatches />);
    expect(screen.getByText("loadError")).toBeInTheDocument();
  });

  it("should render empty state when no matches", () => {
    vi.mocked(useGetUpcomingMatches).mockReturnValue({
      data: { data: { matches: [] } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetUpcomingMatches>);

    render(<UpcomingMatches />);
    expect(screen.getByText("empty")).toBeInTheDocument();
  });

  it("should render matches list", () => {
    vi.mocked(useGetUpcomingMatches).mockReturnValue({
      data: { data: { matches: mockMatches } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetUpcomingMatches>);

    render(<UpcomingMatches />);
    expect(screen.getByText("PSG vs Lyon")).toBeInTheDocument();
    expect(screen.getByText("Arsenal vs Chelsea")).toBeInTheDocument();
  });

  it("should render view all link", () => {
    vi.mocked(useGetUpcomingMatches).mockReturnValue({
      data: { data: { matches: mockMatches } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetUpcomingMatches>);

    render(<UpcomingMatches />);
    expect(screen.getByText("viewAll")).toBeInTheDocument();
  });

  it("should show max 5 matches", () => {
    const sixMatches = Array.from({ length: 6 }, (_, i) => ({
      ...mockMatches[0],
      id: i + 1,
      external_id: `${i + 1}`,
    }));

    vi.mocked(useGetUpcomingMatches).mockReturnValue({
      data: { data: { matches: sixMatches } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetUpcomingMatches>);

    render(<UpcomingMatches />);
    // Only 5 match links should be rendered (each is a Link)
    const matchLinks = screen.getAllByText("PSG vs Lyon");
    expect(matchLinks.length).toBe(5);
  });

  it("should render competition name", () => {
    vi.mocked(useGetUpcomingMatches).mockReturnValue({
      data: { data: { matches: mockMatches } },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useGetUpcomingMatches>);

    render(<UpcomingMatches />);
    expect(screen.getByText("Ligue 1")).toBeInTheDocument();
    expect(screen.getByText("Premier League")).toBeInTheDocument();
  });
});
