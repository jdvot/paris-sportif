import { test, expect } from "@playwright/test";

test.describe("Smoke tests", () => {
  test("the app starts and returns a valid HTML page", async ({ page }) => {
    const response = await page.goto("/");
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(500);
  });

  test("the page has a valid title", async ({ page }) => {
    await page.goto("/");
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(0);
  });

  test("the login page loads without server errors", async ({ page }) => {
    const response = await page.goto("/auth/login");
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(500);
  });

  test("the signup page loads without server errors", async ({ page }) => {
    const response = await page.goto("/auth/signup");
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(500);
  });
});
