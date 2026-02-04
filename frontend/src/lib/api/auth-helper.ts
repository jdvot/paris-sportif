/**
 * Auth helper for getting Supabase token
 * Separated from custom-instance.ts to allow Orval to parse the mutator file
 *
 * Uses the global token store which is populated by onAuthStateChange
 * in the Providers component. This avoids calling getSession() during
 * API requests which can cause AbortError issues.
 */

import { getAuthToken } from "../auth/token-store";

/**
 * Get auth token for API requests
 *
 * This is synchronous and returns the cached token from the global store.
 * The token is kept fresh by onAuthStateChange listener in Providers.
 */
export async function getSupabaseToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    console.log("[AuthHelper] Server-side, no token available");
    return null; // Server-side, no token
  }

  const token = getAuthToken();
  console.log("[AuthHelper] getSupabaseToken() called, token:", token ? "present" : "MISSING");
  return token;
}
