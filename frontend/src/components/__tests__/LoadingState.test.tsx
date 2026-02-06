import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingState } from "../LoadingState";

describe("LoadingState", () => {
  describe("minimal variant", () => {
    it("should render with default loading message", () => {
      render(<LoadingState variant="minimal" />);
      // Mock translation returns the key "loading"
      expect(screen.getByText("loading")).toBeInTheDocument();
    });

    it("should render with custom message", () => {
      render(<LoadingState variant="minimal" message="Custom loading..." />);
      expect(screen.getByText("Custom loading...")).toBeInTheDocument();
    });

    it("should render spinner animation", () => {
      const { container } = render(<LoadingState variant="minimal" />);
      const spinner = container.querySelector(".animate-spin");
      expect(spinner).toBeInTheDocument();
    });
  });

  describe("picks variant (default)", () => {
    it("should render default picks skeleton", () => {
      const { container } = render(<LoadingState />);
      // Should render 5 skeleton cards by default
      const skeletonCards = container.querySelectorAll(".animate-stagger-in");
      expect(skeletonCards.length).toBe(5);
    });

    it("should render custom count of skeleton cards", () => {
      const { container } = render(<LoadingState count={3} />);
      const skeletonCards = container.querySelectorAll(".animate-stagger-in");
      expect(skeletonCards.length).toBe(3);
    });
  });

  describe("stats variant", () => {
    it("should render 4 stat card skeletons", () => {
      const { container } = render(<LoadingState variant="stats" />);
      const statCards = container.querySelectorAll(".animate-pulse");
      expect(statCards.length).toBeGreaterThan(0);
    });

    it("should show loading message", () => {
      render(<LoadingState variant="stats" />);
      // Mock translation returns the key "loading"
      expect(screen.getByText("loading")).toBeInTheDocument();
    });
  });

  describe("matches variant", () => {
    it("should render 5 match row skeletons", () => {
      const { container } = render(<LoadingState variant="matches" />);
      // Each skeleton row has the divide-y wrapper
      const rows = container.querySelectorAll(".divide-y > div");
      expect(rows.length).toBe(5);
    });
  });
});
