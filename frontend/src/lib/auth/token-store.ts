/**
 * Global token store for API authentication
 *
 * This module maintains a cached access token that is updated by
 * onAuthStateChange listener in the Providers component.
 *
 * This approach avoids calling getSession() during API requests,
 * which can cause AbortError issues with React Query.
 */

let cachedToken: string | null = null;

/**
 * Set the cached token (called by onAuthStateChange)
 */
export function setAuthToken(token: string | null): void {
  cachedToken = token;
}

/**
 * Get the cached token for API requests
 */
export function getAuthToken(): string | null {
  return cachedToken;
}

/**
 * Clear the cached token (called on sign out)
 */
export function clearAuthToken(): void {
  cachedToken = null;
}
