import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBoundary, withErrorBoundary } from "../ErrorBoundary";

// Component that throws an error
function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error");
  }
  return <div>No error</div>;
}

// Suppress console.error for expected errors in tests
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalConsoleError;
});

describe("ErrorBoundary", () => {
  it("should render children when there is no error", () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("should render error UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText("Erreur de chargement")).toBeInTheDocument();
    expect(screen.getByText("Ce composant n'a pas pu etre affiche.")).toBeInTheDocument();
  });

  it("should render custom fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText("Custom fallback")).toBeInTheDocument();
    expect(screen.queryByText("Erreur de chargement")).not.toBeInTheDocument();
  });

  it("should call onError callback when error occurs", () => {
    const onError = vi.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "Test error" }),
      expect.any(Object)
    );
  });

  it("should reset error state when reset button is clicked", () => {
    // Use a component that can be controlled
    let shouldThrow = true;
    function ControlledError() {
      if (shouldThrow) {
        throw new Error("Test error");
      }
      return <div>No error</div>;
    }

    const { rerender } = render(
      <ErrorBoundary>
        <ControlledError />
      </ErrorBoundary>
    );

    // Verify error UI is shown
    expect(screen.getByText("Erreur de chargement")).toBeInTheDocument();

    // Change the flag before clicking reset
    shouldThrow = false;

    // Find and click the reset button
    const resetButton = screen.getByRole("button");
    fireEvent.click(resetButton);

    // After reset, the non-throwing content should be visible
    expect(screen.getByText("No error")).toBeInTheDocument();
  });
});

describe("withErrorBoundary HOC", () => {
  it("should wrap component with error boundary", () => {
    function TestComponent() {
      return <div>Wrapped content</div>;
    }

    const WrappedComponent = withErrorBoundary(TestComponent);
    render(<WrappedComponent />);

    expect(screen.getByText("Wrapped content")).toBeInTheDocument();
  });

  it("should catch errors in wrapped component", () => {
    function FailingComponent() {
      throw new Error("Component error");
    }

    const WrappedComponent = withErrorBoundary(FailingComponent);
    render(<WrappedComponent />);

    expect(screen.getByText("Erreur de chargement")).toBeInTheDocument();
  });

  it("should use custom fallback in HOC", () => {
    function FailingComponent() {
      throw new Error("Component error");
    }

    const WrappedComponent = withErrorBoundary(
      FailingComponent,
      <div>HOC fallback</div>
    );
    render(<WrappedComponent />);

    expect(screen.getByText("HOC fallback")).toBeInTheDocument();
  });
});
