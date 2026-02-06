import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "../EmptyState";

describe("EmptyState", () => {
  it("should render title", () => {
    render(<EmptyState title="No results" />);
    expect(screen.getByText("No results")).toBeInTheDocument();
  });

  it("should render description when provided", () => {
    render(
      <EmptyState title="No results" description="Try a different search" />
    );
    expect(screen.getByText("Try a different search")).toBeInTheDocument();
  });

  it("should not render description when not provided", () => {
    const { container } = render(<EmptyState title="No results" />);
    const descriptions = container.querySelectorAll("p");
    expect(descriptions.length).toBe(0);
  });

  it("should render icon when provided", () => {
    render(
      <EmptyState
        title="No results"
        icon={<span data-testid="test-icon">Icon</span>}
      />
    );
    expect(screen.getByTestId("test-icon")).toBeInTheDocument();
  });

  it("should not render icon when not provided", () => {
    const { container } = render(<EmptyState title="No results" />);
    const iconWrapper = container.querySelector(".mb-4.text-gray-400");
    expect(iconWrapper).not.toBeInTheDocument();
  });

  it("should render action when provided", () => {
    render(
      <EmptyState
        title="No results"
        action={<button>Try again</button>}
      />
    );
    expect(screen.getByText("Try again")).toBeInTheDocument();
  });

  it("should apply custom className", () => {
    const { container } = render(
      <EmptyState title="No results" className="custom-class" />
    );
    expect(container.firstChild).toHaveClass("custom-class");
  });
});
