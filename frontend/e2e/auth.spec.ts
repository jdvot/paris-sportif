import { test, expect } from "@playwright/test";

test.describe("Login page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/auth/login");
  });

  test("renders the login form with email and password fields", async ({
    page,
  }) => {
    // Email input
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toHaveAttribute("id", "email");

    // Password input
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeVisible();
    await expect(passwordInput).toHaveAttribute("id", "password");
  });

  test("has a submit button for login", async ({ page }) => {
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toBeVisible();
    await expect(submitButton).toBeEnabled();
    // The button text is in French: "Se connecter"
    await expect(submitButton).toContainText("Se connecter");
  });

  test("has a Google sign-in button", async ({ page }) => {
    const googleButton = page.getByRole("button", {
      name: /Continuer avec Google/i,
    });
    await expect(googleButton).toBeVisible();
  });

  test("has a link to the signup page", async ({ page }) => {
    const signupLink = page.getByRole("link", {
      name: /Creer un compte/i,
    });
    await expect(signupLink).toBeVisible();
    await expect(signupLink).toHaveAttribute("href", "/auth/signup");
  });

  test("has a forgot password link", async ({ page }) => {
    const forgotLink = page.getByRole("link", {
      name: /Mot de passe oubli/i,
    });
    await expect(forgotLink).toBeVisible();
    await expect(forgotLink).toHaveAttribute("href", "/auth/forgot-password");
  });

  test("email field accepts input", async ({ page }) => {
    const emailInput = page.locator("#email");
    await emailInput.fill("test@example.com");
    await expect(emailInput).toHaveValue("test@example.com");
  });

  test("password field accepts input and toggles visibility", async ({
    page,
  }) => {
    const passwordInput = page.locator("#password");
    await passwordInput.fill("mypassword123");
    await expect(passwordInput).toHaveValue("mypassword123");

    // Initially the field is type="password" (hidden)
    await expect(passwordInput).toHaveAttribute("type", "password");

    // Click the toggle visibility button (the eye icon button next to the password)
    const toggleButton = page.locator("#password ~ button");
    await toggleButton.click();

    // Now it should be type="text" (visible)
    await expect(passwordInput).toHaveAttribute("type", "text");
  });
});
