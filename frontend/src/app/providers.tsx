"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState, useEffect, useRef, useCallback } from "react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { createClient } from "@/lib/supabase/client";
import { setAuthToken, clearAuthToken } from "@/lib/auth/token-store";

// Flag to prevent multiple redirects
let isRedirecting = false;

// Interval for server-side user validation (5 minutes)
const USER_VALIDATION_INTERVAL_MS = 5 * 60 * 1000;

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

  console.log('[Auth] Manually cleared Supabase cookies');
}

async function handleAuthError(status: number) {
  // Prevent multiple redirects
  if (isRedirecting || typeof window === 'undefined') return;

  const currentPath = window.location.pathname;

  // Don't redirect if already on an auth page - prevents redirect loops
  if (currentPath.startsWith('/auth/')) {
    console.log('[Auth] Already on auth page, skipping redirect');
    return;
  }

  // Don't redirect if we just redirected (prevent race condition loops)
  if (wasRecentlyRedirected()) {
    console.log('[Auth] Recently redirected, skipping to prevent loop');
    return;
  }

  if (status === 401) {
    console.log('[Auth] 401 detected, clearing auth and redirecting...');
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
      console.log('[Auth] Sign out complete');
    } catch (e) {
      const error = e as { name?: string };
      console.error('[Auth] Sign out failed:', error.name || 'Unknown error');

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
  const initStarted = useRef(false);
  const validationIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Reset redirect flag on mount (new page load)
  useEffect(() => {
    isRedirecting = false;
    console.log('[Providers] Component mounted, reset redirect flag');
  }, []);

  /**
   * Validate user with server using getUser()
   * Best practice: getSession() reads from cache, getUser() validates with server
   * This ensures we detect if user has logged out from another device/browser
   */
  const validateUserWithServer = useCallback(async () => {
    console.log('[Providers] Starting server-side user validation...');
    try {
      const supabase = createClient();
      const { data: { user }, error } = await supabase.auth.getUser();

      if (error) {
        console.error('[Providers] User validation failed:', error.message);
        // User is no longer valid - clear auth and let next API call trigger redirect
        clearAuthToken();
        return false;
      }

      if (!user) {
        console.log('[Providers] User validation: no user returned');
        clearAuthToken();
        return false;
      }

      console.log('[Providers] User validation successful:', user.email);
      return true;
    } catch (err) {
      const error = err as { name?: string; message?: string };
      // Don't treat AbortError as validation failure
      if (error?.name === 'AbortError') {
        console.log('[Providers] User validation aborted (navigation)');
        return true; // Assume valid, will re-validate on next interval
      }
      console.error('[Providers] User validation error:', error?.message);
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

            console.log('[QueryCache] Error caught:', err?.name, err?.status, err?.message);

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

            console.log('[MutationCache] Error caught:', err?.name, err?.status, err?.message);

            // Check for auth error by status (works in minified code)
            if (typeof err?.status === 'number' && err.status > 0) {
              handleAuthError(err.status);
            }
          },
        }),
      })
  );

  // Initialize auth and listen for state changes
  // CRITICAL: Block rendering until auth is hydrated to prevent race conditions
  useEffect(() => {
    // Prevent double initialization in StrictMode
    if (initStarted.current) return;
    initStarted.current = true;

    const supabase = createClient();

    // Initialize auth: simply read session from cookies (set by middleware/callback)
    // No network calls needed - middleware handles token refresh
    const initializeAuth = async () => {
      console.log('[Providers] initializeAuth starting...');
      try {
        // Clear OAuth pending flag if present
        if (typeof window !== 'undefined') {
          sessionStorage.removeItem('oauth_pending');
          console.log('[Providers] Cleared oauth_pending flag');
        }

        // Read session from cookies - this is synchronous, no network call
        // The middleware has already refreshed the token if needed
        console.log('[Providers] Calling getSession()...');
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          console.error('[Providers] getSession() error:', sessionError.message);
        }

        console.log('[Providers] getSession() result - session:', !!session, 'token:', !!session?.access_token);

        if (session?.access_token) {
          setAuthToken(session.access_token, session.expires_in);
          console.log('[Providers] Token set from session, expires_in:', session.expires_in);

          // Clear redirect marker - we have a session
          if (typeof window !== 'undefined') {
            sessionStorage.removeItem('auth_redirect_time');
            console.log('[Providers] Cleared auth_redirect_time');
          }

          // Validate user with server on init (best practice per Supabase docs)
          // "The only way to ensure a user has logged out is getUser()"
          console.log('[Providers] Initial server validation with getUser()...');
          const isValid = await validateUserWithServer();
          console.log('[Providers] Initial validation result:', isValid);

          // Set up periodic validation (every 5 minutes)
          if (validationIntervalRef.current) {
            clearInterval(validationIntervalRef.current);
          }
          validationIntervalRef.current = setInterval(() => {
            console.log('[Providers] Periodic validation triggered');
            validateUserWithServer();
          }, USER_VALIDATION_INTERVAL_MS);
          console.log('[Providers] Set up periodic validation every', USER_VALIDATION_INTERVAL_MS / 1000, 'seconds');
        } else {
          console.log('[Providers] No session found');
        }
      } catch (err) {
        const error = err as { name?: string; message?: string };

        if (error?.name === 'AbortError') {
          // Navigation cancelled the request - this is fine
          // Keep existing auth state, the next render will re-init
          console.log('[Providers] Auth init aborted, keeping existing state');
        } else {
          console.error('[Providers] Auth init error:', err);
          clearAuthToken();
        }
      } finally {
        console.log('[Providers] initializeAuth complete, setting isReady=true');
        setIsReady(true);
      }
    };

    initializeAuth();

    // Listen for auth state changes AFTER initial hydration
    console.log('[Providers] Setting up onAuthStateChange listener');
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event: string, session: { access_token?: string; expires_in?: number } | null) => {
      console.log('[Providers] onAuthStateChange fired:', {
        event,
        hasSession: !!session,
        hasToken: !!session?.access_token,
        expiresIn: session?.expires_in,
      });

      // Update token store with new token
      if (session?.access_token) {
        setAuthToken(session.access_token, session.expires_in);
        console.log('[Providers] Token updated in store');
      } else {
        clearAuthToken();
        console.log('[Providers] Token cleared from store');
      }

      // When user signs in (including OAuth callback), invalidate all queries
      // so they refetch with the new auth token
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        console.log('[Providers] Invalidating queries after auth change');
        queryClient.invalidateQueries();

        // Start periodic validation if not already running
        if (!validationIntervalRef.current && session?.access_token) {
          validationIntervalRef.current = setInterval(() => {
            console.log('[Providers] Periodic validation triggered');
            validateUserWithServer();
          }, USER_VALIDATION_INTERVAL_MS);
          console.log('[Providers] Started periodic validation');
        }
      }

      // When user signs out, clear the cache and token
      if (event === 'SIGNED_OUT') {
        console.log('[Providers] Clearing cache after sign out');
        clearAuthToken();
        queryClient.clear();

        // Stop periodic validation
        if (validationIntervalRef.current) {
          clearInterval(validationIntervalRef.current);
          validationIntervalRef.current = null;
          console.log('[Providers] Stopped periodic validation');
        }
      }
    });

    return () => {
      console.log('[Providers] Cleaning up auth subscription');
      subscription.unsubscribe();
      if (validationIntervalRef.current) {
        clearInterval(validationIntervalRef.current);
        validationIntervalRef.current = null;
        console.log('[Providers] Cleared validation interval');
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
