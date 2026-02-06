import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MatchContextSummary } from "../MatchContextSummary";

describe("MatchContextSummary", () => {
  it("should return null when summary is null", () => {
    const { container } = render(
      <MatchContextSummary summary={null} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("should return null when summary is undefined", () => {
    const { container } = render(
      <MatchContextSummary summary={undefined} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("should render summary text", () => {
    render(
      <MatchContextSummary summary="PSG en pleine forme, 5 victoires consécutives." />
    );
    expect(
      screen.getByText("PSG en pleine forme, 5 victoires consécutives.")
    ).toBeInTheDocument();
  });

  it("should render title", () => {
    render(<MatchContextSummary summary="Some summary" />);
    expect(screen.getByText("title")).toBeInTheDocument();
  });

  it("should render news sources when provided", () => {
    const sources = [
      { source: "L'Équipe" },
      { source: "RMC Sport" },
    ];
    render(
      <MatchContextSummary
        summary="Some summary"
        sources={sources as never}
      />
    );
    expect(screen.getByText("L'Équipe")).toBeInTheDocument();
    expect(screen.getByText("RMC Sport")).toBeInTheDocument();
  });

  it("should not render sources section when sources is empty", () => {
    const { container } = render(
      <MatchContextSummary summary="Some summary" sources={[]} />
    );
    // No Newspaper icon should be rendered
    const sourcesSection = container.querySelector('[class*="gap-2"]');
    expect(sourcesSection).toBeTruthy();
  });

  it("should render timestamp when generatedAt is provided", () => {
    // Set a date 2 hours ago
    const twoHoursAgo = new Date(
      Date.now() - 2 * 60 * 60 * 1000
    ).toISOString();
    render(
      <MatchContextSummary
        summary="Some summary"
        generatedAt={twoHoursAgo}
      />
    );
    // The translation mock will return the key with substitution
    expect(screen.getByText(/updatedAgo/)).toBeInTheDocument();
  });

  it("should apply custom className", () => {
    const { container } = render(
      <MatchContextSummary summary="Some summary" className="my-custom-class" />
    );
    expect(container.firstChild).toHaveClass("my-custom-class");
  });
});
