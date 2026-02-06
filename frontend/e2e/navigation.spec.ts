import { test, expect } from "@playwright/test";

test.describe("Navigation and auth redirects", () => {
  test("unauthenticated user accessing /picks is redirected to login", async ({
    page,
  }) => {
    await page.goto("/picks");
    // The middleware should redirect to /auth/login?next=/picks
    await expect(page).toHaveURL(/\/auth\/login/);
    // Verify the redirect preserves the return URL
    expect(page.url()).toContain("next=%2Fpicks");
  });

  test("unauthenticated user accessing /dashboard is redirected to login", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/auth\/login/);
    expect(page.url()).toContain("next=%2Fdashboard");
  });

  test("unauthenticated user accessing /profile is redirected to login", async ({
    page,
  }) => {
    await page.goto("/profile");
    await expect(page).toHaveURL(/\/auth\/login/);
    expect(page.url()).toContain("next=%2Fprofile");
  });

  test("unauthenticated user accessing /matches is redirected to login", async ({
    page,
  }) => {
    await page.goto("/matches");
    await expect(page).toHaveURL(/\/auth\/login/);
    expect(page.url()).toContain("next=%2Fmatches");
  });

  test("landing page (/) is accessible without authentication", async ({
    page,
  }) => {
    const response = await page.goto("/");
    expect(response).not.toBeNull();
    // The home page is public, so it should not redirect to login
    const url = new URL(page.url());
    expect(url.pathname).toBe("/");
  });

  test("login page is accessible without authentication", async ({ page }) => {
    const response = await page.goto("/auth/login");
    expect(response).not.toBeNull();
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test("signup page is accessible without authentication", async ({
    page,
  }) => {
    const response = await page.goto("/auth/signup");
    expect(response).not.toBeNull();
    await expect(page).toHaveURL(/\/auth\/signup/);
  });

  test("forgot password page is accessible without authentication", async ({
    page,
  }) => {
    const response = await page.goto("/auth/forgot-password");
    expect(response).not.toBeNull();
    await expect(page).toHaveURL(/\/auth\/forgot-password/);
  });
});
