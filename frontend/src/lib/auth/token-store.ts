/**
 * Global token store for API authentication
 *
 * This module maintains a cached access token that is updated by
 * onAuthStateChange listener in the Providers component.
 *
 * This approach avoids calling getSession() during API requests,
 * which can cause AbortError issues with React Query.
 *
 * Features:
 * - Token expiration tracking (returns null 60s before expiry)
 * - Debug logging for troubleshooting auth issues
 */

let cachedToken: string | null = null;
let tokenExpiresAt: number | null = null;

// Buffer time before expiration (60 seconds)
const EXPIRY_BUFFER_MS = 60 * 1000;

/**
 * Set the cached token (called by onAuthStateChange)
 * @param token The access token or null
 * @param expiresIn Optional expiration time in seconds
 */
export function setAuthToken(token: string | null, expiresIn?: number): void {
  console.log('[TokenStore] Setting token:', !!token, expiresIn ? `expires in ${expiresIn}s` : '');
  cachedToken = token;
  tokenExpiresAt = token && expiresIn ? Date.now() + expiresIn * 1000 : null;
}

/**
 * Get the cached token for API requests
 * Returns null if token is expired or will expire within 60 seconds
 */
export function getAuthToken(): string | null {
  // If token has expiration tracking and is expired (with buffer), return null
  if (tokenExpiresAt && Date.now() > tokenExpiresAt - EXPIRY_BUFFER_MS) {
    console.log('[TokenStore] Token expired or expiring soon, returning null');
    return null;
  }
  return cachedToken;
}

/**
 * Clear the cached token (called on sign out)
 */
export function clearAuthToken(): void {
  console.log('[TokenStore] Clearing token');
  cachedToken = null;
  tokenExpiresAt = null;
}

/**
 * Check if a token is currently stored (for debugging)
 */
export function hasAuthToken(): boolean {
  return cachedToken !== null;
}
