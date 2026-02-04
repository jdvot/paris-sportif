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
let refreshInProgress = false;

// Buffer time before expiration (5 seconds - just enough to avoid race conditions)
const EXPIRY_BUFFER_MS = 5 * 1000;
// Threshold to trigger proactive refresh (2 minutes before expiry)
const REFRESH_THRESHOLD_MS = 2 * 60 * 1000;

/**
 * Set the cached token (called by onAuthStateChange)
 * @param token The access token or null
 * @param expiresIn Optional expiration time in seconds
 */
export function setAuthToken(token: string | null, expiresIn?: number): void {
  console.log('[TokenStore] Setting token:', !!token, expiresIn ? `expires in ${expiresIn}s` : '');
  cachedToken = token;
  tokenExpiresAt = token && expiresIn ? Date.now() + expiresIn * 1000 : null;
  refreshInProgress = false;
}

/**
 * Trigger a proactive token refresh via Supabase
 */
async function triggerRefresh(): Promise<void> {
  if (refreshInProgress || typeof window === 'undefined') return;
  refreshInProgress = true;

  try {
    console.log('[TokenStore] Triggering proactive refresh...');
    // Dynamic import to avoid circular dependencies
    const { createClient } = await import('@/lib/supabase/client');
    const supabase = createClient();
    const { data, error } = await supabase.auth.refreshSession();
    if (error) {
      console.error('[TokenStore] Refresh failed:', error.message);
    } else if (data.session) {
      console.log('[TokenStore] Refresh successful');
      // Token will be updated via onAuthStateChange
    }
  } catch (e) {
    console.error('[TokenStore] Refresh error:', e);
  } finally {
    refreshInProgress = false;
  }
}

/**
 * Get the cached token for API requests
 * Returns the token if still valid, triggers refresh if close to expiry
 */
export function getAuthToken(): string | null {
  if (!cachedToken) return null;

  const now = Date.now();

  // If token is actually expired, return null
  if (tokenExpiresAt && now > tokenExpiresAt - EXPIRY_BUFFER_MS) {
    console.log('[TokenStore] Token expired, returning null');
    return null;
  }

  // If token is close to expiry, trigger refresh in background but still return the token
  if (tokenExpiresAt && now > tokenExpiresAt - REFRESH_THRESHOLD_MS) {
    console.log('[TokenStore] Token expiring soon, triggering refresh');
    triggerRefresh();
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
