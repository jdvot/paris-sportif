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
 * - Token expiration tracking (returns null 5s before expiry)
 * - Cross-tab refresh coordination via BroadcastChannel
 * - Debug logging for troubleshooting auth issues
 */

let cachedToken: string | null = null;
let tokenExpiresAt: number | null = null;
let refreshInProgress = false;

// Flag to track if auth has been initialized
// This distinguishes "not logged in" from "not yet checked"
let authInitialized = false;

// Promise that resolves when auth is initialized
let authReadyResolve: (() => void) | null = null;
const authReadyPromise = new Promise<void>((resolve) => {
  authReadyResolve = resolve;
});

// Buffer time before expiration (5 seconds - just enough to avoid race conditions)
const EXPIRY_BUFFER_MS = 5 * 1000;
// Threshold to trigger proactive refresh (2 minutes before expiry)
const REFRESH_THRESHOLD_MS = 2 * 60 * 1000;

// Cross-tab coordination via BroadcastChannel
const CHANNEL_NAME = 'auth-token-refresh';
let broadcastChannel: BroadcastChannel | null = null;

// Initialize BroadcastChannel for cross-tab coordination
if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
  try {
    broadcastChannel = new BroadcastChannel(CHANNEL_NAME);
    broadcastChannel.onmessage = (event) => {
      if (event.data.type === 'REFRESH_STARTED') {
        // Another tab started refresh, mark as in progress
        refreshInProgress = true;
        console.log('[TokenStore] Another tab started refresh');
      } else if (event.data.type === 'TOKEN_UPDATED' && event.data.token) {
        // Another tab completed refresh, update our cache
        cachedToken = event.data.token;
        tokenExpiresAt = event.data.expiresAt;
        refreshInProgress = false;
        console.log('[TokenStore] Token updated from another tab');
      } else if (event.data.type === 'REFRESH_COMPLETED') {
        refreshInProgress = false;
      }
    };
  } catch (e) {
    console.warn('[TokenStore] BroadcastChannel not available:', e);
  }
}

/**
 * Set the cached token (called by onAuthStateChange)
 * Broadcasts to other tabs for synchronization
 * @param token The access token or null
 * @param expiresIn Optional expiration time in seconds
 */
export function setAuthToken(token: string | null, expiresIn?: number): void {
  console.log('[TokenStore] Setting token:', !!token, expiresIn ? `expires in ${expiresIn}s` : '', 'authInitialized:', authInitialized);
  cachedToken = token;
  tokenExpiresAt = token && expiresIn ? Date.now() + expiresIn * 1000 : null;
  refreshInProgress = false;

  // Mark auth as initialized (we now know the auth state)
  if (!authInitialized) {
    authInitialized = true;
    authReadyResolve?.();
    console.log('[TokenStore] Auth initialized');
  }

  // Broadcast token update to other tabs
  if (token && broadcastChannel) {
    broadcastChannel.postMessage({
      type: 'TOKEN_UPDATED',
      token,
      expiresAt: tokenExpiresAt,
    });
  }
}

/**
 * Trigger a proactive token refresh via Supabase
 * Broadcasts to other tabs to prevent duplicate refreshes
 */
async function triggerRefresh(): Promise<void> {
  if (refreshInProgress || typeof window === 'undefined') return;
  refreshInProgress = true;

  // Notify other tabs that refresh is starting
  broadcastChannel?.postMessage({ type: 'REFRESH_STARTED' });

  try {
    console.log('[TokenStore] Triggering proactive refresh...');
    // Dynamic import to avoid circular dependencies
    const { createClient } = await import('@/lib/supabase/client');
    const supabase = createClient();
    const { data, error } = await supabase.auth.refreshSession();
    if (error) {
      console.error('[TokenStore] Refresh failed:', error.message);
      broadcastChannel?.postMessage({ type: 'REFRESH_COMPLETED' });
    } else if (data.session) {
      console.log('[TokenStore] Refresh successful');
      // Token will be updated via onAuthStateChange, which calls setAuthToken
    }
  } catch (e) {
    console.error('[TokenStore] Refresh error:', e);
    broadcastChannel?.postMessage({ type: 'REFRESH_COMPLETED' });
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

/**
 * Check if auth has been initialized
 * Use this to distinguish between "not logged in" and "auth not yet checked"
 */
export function isAuthInitialized(): boolean {
  return authInitialized;
}

/**
 * Wait for auth to be initialized
 * Returns immediately if already initialized
 */
export function waitForAuthReady(): Promise<void> {
  if (authInitialized) {
    return Promise.resolve();
  }
  return authReadyPromise;
}

/**
 * Mark auth as initialized without a token (for unauthenticated state)
 * Called by Providers when getSession returns no session
 */
export function markAuthInitialized(): void {
  if (!authInitialized) {
    console.log('[TokenStore] Marking auth as initialized (no session)');
    authInitialized = true;
    authReadyResolve?.();
  }
}
