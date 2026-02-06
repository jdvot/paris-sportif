/**
 * Auth helper for getting Supabase token
 * Separated from custom-instance.ts to allow Orval to parse the mutator file
 *
 * Uses the global token store which is populated by onAuthStateChange
 * in the Providers component. This avoids calling getSession() during
 * API requests which can cause AbortError issues.
 */

import { getAuthToken, isAuthInitialized, waitForAuthReady } from "../auth/token-store";
import { logger } from "@/lib/logger";

// Timeout for waiting for auth to be ready (3 seconds max)
const AUTH_READY_TIMEOUT_MS = 3000;

/**
 * Get auth token for API requests
 *
 * IMPORTANT: This now waits for auth to be initialized before returning.
 * This prevents API calls from firing before we know the auth state.
 */
export async function getSupabaseToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    logger.log("[AuthHelper] Server-side, no token available");
    return null; // Server-side, no token
  }

  // If auth is not yet initialized, wait for it (with timeout)
  if (!isAuthInitialized()) {
    logger.log("[AuthHelper] Auth not initialized, waiting...");
    try {
      await Promise.race([
        waitForAuthReady(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("Auth init timeout")), AUTH_READY_TIMEOUT_MS)
        ),
      ]);
      logger.log("[AuthHelper] Auth ready, proceeding");
    } catch {
      logger.warn("[AuthHelper] Auth wait timed out, proceeding without token");
    }
  }

  const token = getAuthToken();
  logger.log("[AuthHelper] getSupabaseToken() called, token:", token ? "present" : "MISSING", "authInitialized:", isAuthInitialized());
  return token;
}
