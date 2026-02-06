import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "../Header";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// Mock child components
vi.mock("../ThemeToggle", () => ({
  ThemeToggle: () => <button data-testid="theme-toggle">Theme</button>,
}));
vi.mock("../LanguageSwitcher", () => ({
  LanguageSwitcher: () => <button data-testid="lang-switcher">Lang</button>,
}));
vi.mock("../AuthButton", () => ({
  AuthButton: () => <button data-testid="auth-button">Auth</button>,
}));
vi.mock("../Logo", () => ({
  Logo: () => <span data-testid="logo">Logo</span>,
}));

// Mock useUserPreferences
vi.mock("@/lib/hooks/useUserPreferences", () => ({
  useUserPreferences: () => ({ data: null, isLoading: false }),
}));

describe("Header", () => {
  it("should render the logo", () => {
    render(<Header />);
    expect(screen.getByTestId("logo")).toBeInTheDocument();
  });

  it("should render navigation links", () => {
    render(<Header />);
    // All nav items are rendered twice (desktop + mobile)
    const homeLinks = screen.getAllByText("home");
    expect(homeLinks.length).toBeGreaterThanOrEqual(2);
  });

  it("should render theme toggle", () => {
    render(<Header />);
    expect(screen.getByTestId("theme-toggle")).toBeInTheDocument();
  });

  it("should render language switcher", () => {
    render(<Header />);
    expect(screen.getByTestId("lang-switcher")).toBeInTheDocument();
  });

  it("should render auth button", () => {
    render(<Header />);
    expect(screen.getByTestId("auth-button")).toBeInTheDocument();
  });

  it("should have sticky positioning", () => {
    const { container } = render(<Header />);
    const header = container.querySelector("header");
    expect(header).toHaveClass("sticky", "top-0");
  });

  it("should render desktop and mobile navigation", () => {
    const { container } = render(<Header />);
    const desktopNav = container.querySelector("nav.hidden.md\\:flex");
    const mobileNav = container.querySelector("nav.md\\:hidden");
    expect(desktopNav).toBeInTheDocument();
    expect(mobileNav).toBeInTheDocument();
  });

  it("should render all 6 navigation items", () => {
    render(<Header />);
    const expectedKeys = ["home", "picks", "bets", "calibration", "matches", "standings"];
    for (const key of expectedKeys) {
      const links = screen.getAllByText(key);
      expect(links.length).toBeGreaterThanOrEqual(1);
    }
  });
});
