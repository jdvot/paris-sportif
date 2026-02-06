"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState, useEffect, useRef, useCallback } from "react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { createClient } from "@/lib/supabase/client";
import { setAuthToken, clearAuthToken, markAuthInitialized } from "@/lib/auth/token-store";
import { logger } from "@/lib/logger";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";

// Flag to prevent multiple redirects
let isRedirecting = false;

// Interval for server-side user validation (5 minutes)
const USER_VALIDATION_INTERVAL_MS = 5 * 60 * 1000;

/**
 * Manually parse Supabase session from chunked cookies
 * Workaround for getSession() hanging bug in @supabase/ssr
 *
 * Supabase stores session in chunked cookies like:
 * - sb-{project_ref}-auth-token.0
 * - sb-{project_ref}-auth-token.1
 * etc.
 */
function parseSessionFromCookies(): { access_token: string; expires_in: number; user: { email?: string } } | null {
  if (typeof document === 'undefined') return null;

  try {
    const cookies = document.cookie.split(';').reduce((acc, cookie) => {
      const [name, value] = cookie.trim().split('=');
      if (name) acc[name] = value;
      return acc;
    }, {} as Record<string, string>);

    // Find all Supabase auth token chunks
    const authTokenChunks: { index: number; value: string }[] = [];

    for (const [name, value] of Object.entries(cookies)) {
      // Match both sb-xxx-auth-token.N (chunked) and sb-xxx-auth-token (single)
      const chunkMatch = name.match(/^sb-[^-]+-auth-token\.(\d+)$/);
      const singleMatch = name.match(/^sb-[^-]+-auth-token$/);

      if (chunkMatch) {
        authTokenChunks.push({ index: parseInt(chunkMatch[1], 10), value });
      } else if (singleMatch && !authTokenChunks.length) {
        // Single cookie (not chunked)
        authTokenChunks.push({ index: 0, value });
      }
    }

    if (authTokenChunks.length === 0) {
      logger.log('[CookieParser] No auth token cookies found');
      return null;
    }

    // Sort by index and concatenate
    authTokenChunks.sort((a, b) => a.index - b.index);
    const encodedSession = authTokenChunks.map(c => c.value).join('');

    logger.log('[CookieParser] Found', authTokenChunks.length, 'cookie chunks');

    // Decode - Supabase uses base64url encoding with 'base64-' prefix
    let sessionJson: string;
    if (encodedSession.startsWith('base64-')) {
      // Remove prefix and decode
      const base64 = encodedSession.slice(7);
      // base64url to base64
      const base64Standard = base64.replace(/-/g, '+').replace(/_/g, '/');
      sessionJson = atob(base64Standard);
    } else {
      // Try direct decode
      sessionJson = decodeURIComponent(encodedSession);
    }

    const session = JSON.parse(sessionJson);

    if (!session.access_token) {
      logger.log('[CookieParser] Session missing access_token');
      return null;
    }

    logger.log('[CookieParser] Successfully parsed session for:', session.user?.email);

    return {
      access_token: session.access_token,
      expires_in: session.expires_in || 3600,
      user: session.user || {}
    };
  } catch (err) {
    logger.error('[CookieParser] Failed to parse session:', err);
    return null;
  }
}

// Check if we recently redirected (persists across page loads)
function wasRecentlyRedirected(): boolean {
  if (typeof window === 'undefined') return false;
  const redirectTime = sessionStorage.getItem('auth_redirect_time');
  if (!redirectTime) return false;
  // Consider redirects within last 5 seconds as "recent"
  return Date.now() - parseInt(redirectTime, 10) < 5000;
}

// Clear all Supabase cookies manually (fallback when signOut fails)
function clearSupabaseCookies() {
  if (typeof document === 'undefined') return;

  // Get all cookies
  const cookies = document.cookie.split(';');

  // Clear all sb- prefixed cookies (Supabase cookies)
  cookies.forEach(cookie => {
    const cookieName = cookie.split('=')[0].trim();
    if (cookieName.startsWith('sb-')) {
      // Clear for all possible paths and domains
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname}`;
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=.${window.location.hostname}`;
    }
  });

  logger.log('[Auth] Manually cleared Supabase cookies');
}

async function handleAuthError(status: number) {
  // Prevent multiple redirects
  if (isRedirecting || typeof window === 'undefined') return;

  const currentPath = window.location.pathname;

  // Don't redirect if already on an auth page - prevents redirect loops
  if (currentPath.startsWith('/auth/')) {
    logger.log('[Auth] Already on auth page, skipping redirect');
    return;
  }

  // Don't redirect if we just redirected (prevent race condition loops)
  if (wasRecentlyRedirected()) {
    logger.log('[Auth] Recently redirected, skipping to prevent loop');
    return;
  }

  if (status === 401) {
    logger.log('[Auth] 401 detected, clearing auth and redirecting...');
    isRedirecting = true;

    // Mark that we're redirecting (persists across the navigation)
    sessionStorage.setItem('auth_redirect_time', Date.now().toString());

    const loginUrl = `/auth/login?next=${encodeURIComponent(currentPath)}`;

    // Try to sign out properly first
    let signOutSuccess = false;
    try {
      const supabase = createClient();
      await supabase.auth.signOut();
      signOutSuccess = true;
      logger.log('[Auth] Sign out complete');
    } catch (e) {
      const error = e as { name?: string };
      logger.error('[Auth] Sign out failed:', error.name || 'Unknown error');

      // If signOut failed (especially AbortError), manually clear cookies
      // This ensures middleware won't see the user on next request
      if (error?.name === 'AbortError' || !signOutSuccess) {
        clearSupabaseCookies();
      }
    }

    // Clear token store
    clearAuthToken();

    // Hard redirect to login (this will reload the page and clear any in-flight requests)
    window.location.replace(loginUrl);
  }
  // 403 errors are handled locally by components (e.g., showing upgrade prompts)
  // No global redirect for 403
}

export function Providers({ children }: { children: React.ReactNode }) {
  // Hydration gate: block rendering until auth is initialized
  const [isReady, setIsReady] = useState(false);
  const validationIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Reset redirect flag on mount (new page load)
  useEffect(() => {
    isRedirecting = false;
    logger.log('[Providers] Component mounted, reset redirect flag');
  }, []);

  /**
   * Validate user with server using getUser()
   * Best practice: getSession() reads from cache, getUser() validates with server
   * This ensures we detect if user has logged out from another device/browser
   */
  const validateUserWithServer = useCallback(async () => {
    logger.log('[Providers] Starting server-side user validation...');
    try {
      const supabase = createClient();
      const { data: { user }, error } = await supabase.auth.getUser();

      if (error) {
        logger.error('[Providers] User validation failed:', error.message);
        // User is no longer valid - clear auth and let next API call trigger redirect
        clearAuthToken();
        return false;
      }

      if (!user) {
        logger.log('[Providers] User validation: no user returned');
        clearAuthToken();
        return false;
      }

      logger.log('[Providers] User validation successful:', user.email);
      return true;
    } catch (err) {
      const error = err as { name?: string; message?: string };
      // Don't treat AbortError as validation failure
      if (error?.name === 'AbortError') {
        logger.log('[Providers] User validation aborted (navigation)');
        return true; // Assume valid, will re-validate on next interval
      }
      logger.error('[Providers] User validation error:', error?.message);
      return false;
    }
  }, []);

  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              // Don't retry on auth errors or abort errors
              const apiError = error as { status?: number; name?: string };
              if (apiError?.name === 'AbortError') {
                return false;
              }
              if (apiError?.name === 'ApiError' && [401, 403].includes(apiError.status || 0)) {
                return false;
              }
              return failureCount < 3;
            },
          },
        },
        queryCache: new QueryCache({
          onError: (error) => {
            // Ignore AbortError (React Query cancellation)
            const err = error as { name?: string; status?: number; message?: string };
            if (err?.name === 'AbortError') {
              return;
            }

            logger.log('[QueryCache] Error caught:', err?.name, err?.status, err?.message);

            // Check for auth error by status (works in minified code)
            // ApiError has status property, other errors don't
            if (typeof err?.status === 'number' && err.status > 0) {
              handleAuthError(err.status);
            }
          },
        }),
        mutationCache: new MutationCache({
          onError: (error) => {
            const err = error as { name?: string; status?: number; message?: string };
            if (err?.name === 'AbortError') {
              return;
            }

            logger.log('[MutationCache] Error caught:', err?.name, err?.status, err?.message);

            // Check for auth error by status (works in minified code)
            if (typeof err?.status === 'number' && err.status > 0) {
              handleAuthError(err.status);
            }
          },
        }),
      })
  );

  /**
   * Initialize auth with a robust pattern:
   * 1. Call getSession() once to bootstrap auth state (with timeout)
   * 2. Set up onAuthStateChange for subsequent events
   * 3. Use finally block to GUARANTEE isReady is always set
   *
   * This approach handles all edge cases:
   * - INITIAL_SESSION never fires (Next.js 15 bug)
   * - getSession() hangs (Supabase bug #35754)
   * - AbortError from React StrictMode
   * - No cookies/session available
   */
  useEffect(() => {
    let isActive = true;

    logger.log('[Providers] Starting auth initialization...');

    // Clear OAuth pending flag if present
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('oauth_pending');
    }

    const supabase = createClient();

    // Helper to mark ready (idempotent)
    const markReady = () => {
      if (isActive) {
        logger.log('[Providers] Setting isReady = true');
        setIsReady(true);
      }
    };

    // Helper to set up session from access token
    const setupSession = (accessToken: string, expiresIn: number, userEmail?: string) => {
      logger.log('[Providers] Setting up session for:', userEmail);
      setAuthToken(accessToken, expiresIn);

      // Clear redirect marker
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('auth_redirect_time');
      }

      // Set up periodic validation
      if (!validationIntervalRef.current) {
        validationIntervalRef.current = setInterval(() => {
          logger.log('[Providers] Periodic validation');
          validateUserWithServer();
        }, USER_VALIDATION_INTERVAL_MS);
      }
    };

    // Step 1: Bootstrap auth with getSession() + timeout + cookie fallback
    const initAuth = async () => {
      try {
        logger.log('[Providers] Calling getSession()...');

        // Create a promise that resolves with a special marker after 2 seconds
        const timeoutPromise = new Promise<{ data: { session: null }; error: null; timedOut: true }>((resolve) => {
          setTimeout(() => {
            logger.warn('[Providers] getSession() timeout after 2s');
            resolve({ data: { session: null }, error: null, timedOut: true });
          }, 2000);
        });

        // Race between getSession and timeout
        const result = await Promise.race([
          supabase.auth.getSession().then((r: { data: { session: Session | null }; error: unknown }) => ({ ...r, timedOut: false })),
          timeoutPromise,
        ]);

        if (!isActive) return;

        const { data, error, timedOut } = result as { data: { session: Session | null }; error: unknown; timedOut: boolean };

        if (error) {
          logger.error('[Providers] getSession error:', (error as { message?: string }).message);
          markAuthInitialized();
        } else if (data.session?.access_token) {
          // getSession worked! Use the session
          setupSession(data.session.access_token, data.session.expires_in, data.session.user?.email);
        } else if (timedOut) {
          // getSession timed out - try cookie fallback
          logger.log('[Providers] getSession timed out, trying cookie fallback...');
          const cookieSession = parseSessionFromCookies();

          if (cookieSession) {
            logger.log('[Providers] Cookie fallback successful!');
            setupSession(cookieSession.access_token, cookieSession.expires_in, cookieSession.user?.email);
          } else {
            logger.log('[Providers] No session from cookies either');
            markAuthInitialized();
          }
        } else {
          logger.log('[Providers] No session from getSession');
          markAuthInitialized();
        }
      } catch (err) {
        const error = err as { name?: string; message?: string };
        // Don't treat AbortError as failure (StrictMode double-mount)
        if (error?.name === 'AbortError') {
          logger.log('[Providers] getSession aborted (StrictMode)');
          // Still try cookie fallback on abort
          const cookieSession = parseSessionFromCookies();
          if (cookieSession) {
            logger.log('[Providers] Cookie fallback after abort successful!');
            setupSession(cookieSession.access_token, cookieSession.expires_in, cookieSession.user?.email);
          } else {
            markAuthInitialized();
          }
        } else {
          logger.error('[Providers] getSession failed:', error?.message);
          markAuthInitialized();
        }
      } finally {
        // CRITICAL: Always mark ready, even on error/timeout
        markReady();
      }
    };

    // Step 2: Set up onAuthStateChange for future events
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event: AuthChangeEvent, session: Session | null) => {
      logger.log('[Providers] onAuthStateChange:', event, 'session:', !!session);

      // Skip INITIAL_SESSION - we handle this via getSession() above
      if (event === 'INITIAL_SESSION') {
        logger.log('[Providers] INITIAL_SESSION (skipped, using getSession)');
        return;
      }

      // Handle sign in (new sign in or tab refocus)
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        if (session?.access_token) {
          setAuthToken(session.access_token, session.expires_in);
          logger.log('[Providers] Token updated after', event, 'user:', session.user?.email);
          queryClient.invalidateQueries();

          // Start periodic validation if not already running
          if (!validationIntervalRef.current) {
            validationIntervalRef.current = setInterval(() => {
              validateUserWithServer();
            }, USER_VALIDATION_INTERVAL_MS);
          }
        }
        return;
      }

      // Handle sign out
      if (event === 'SIGNED_OUT') {
        logger.log('[Providers] SIGNED_OUT - clearing auth');
        clearAuthToken();
        queryClient.clear();

        if (validationIntervalRef.current) {
          clearInterval(validationIntervalRef.current);
          validationIntervalRef.current = null;
        }
        return;
      }

      // Handle other events (USER_UPDATED, PASSWORD_RECOVERY, etc.)
      if (session?.access_token) {
        setAuthToken(session.access_token, session.expires_in);
      } else {
        clearAuthToken();
      }
    });

    // Start auth initialization
    initAuth();

    return () => {
      logger.log('[Providers] Cleanup');
      isActive = false;
      subscription.unsubscribe();
      if (validationIntervalRef.current) {
        clearInterval(validationIntervalRef.current);
        validationIntervalRef.current = null;
      }
    };
  }, [queryClient, validateUserWithServer]);

  // Block rendering until auth is initialized to prevent race conditions
  // where API requests fire before the token is in the store
  if (!isReady) {
    // Return null or a minimal skeleton to prevent flash
    return null;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
