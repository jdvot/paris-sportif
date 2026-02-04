"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState, useEffect, useRef, useCallback } from "react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { createClient } from "@/lib/supabase/client";
import { setAuthToken, clearAuthToken, markAuthInitialized } from "@/lib/auth/token-store";

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

  /**
   * Initialize auth using getSession() + onAuthStateChange
   *
   * WORKAROUND for Next.js 15 + @supabase/ssr bug:
   * The INITIAL_SESSION event from onAuthStateChange doesn't fire correctly.
   * Instead, we explicitly call getSession() to read the session from cookies,
   * then use onAuthStateChange only for subsequent updates.
   */
  useEffect(() => {
    // Track if this effect instance is still active (not cleaned up)
    let isActive = true;

    console.log('[Providers] Setting up auth...');

    // Clear OAuth pending flag if present
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('oauth_pending');
    }

    const supabase = createClient();

    // STEP 1: Use getSession() to read session from cookies
    // This is the workaround for INITIAL_SESSION not firing in Next.js 15
    console.log('[Providers] Calling getSession() to read cookies...');
    supabase.auth.getSession().then(({ data, error }: { data: { session: { access_token?: string; expires_in?: number; user?: { email?: string } } | null }; error: { message?: string } | null }) => {
      // Ignore if component was unmounted (StrictMode cleanup)
      if (!isActive) {
        console.log('[Providers] getSession() completed but component unmounted, ignoring');
        return;
      }

      console.log('[Providers] getSession() result:', {
        hasSession: !!data?.session,
        hasUser: !!data?.session?.user,
        userEmail: data?.session?.user?.email,
        error: error?.message,
      });

      if (data?.session?.access_token) {
        console.log('[Providers] Session found! Setting token...');
        setAuthToken(data.session.access_token, data.session.expires_in);

        // Clear redirect marker
        if (typeof window !== 'undefined') {
          sessionStorage.removeItem('auth_redirect_time');
        }

        // Set up periodic validation
        if (!validationIntervalRef.current) {
          validationIntervalRef.current = setInterval(() => {
            console.log('[Providers] Periodic validation');
            validateUserWithServer();
          }, USER_VALIDATION_INTERVAL_MS);
        }
      } else {
        console.log('[Providers] No session found');
        markAuthInitialized();
      }

      // Mark as ready after getSession completes
      setIsReady(true);
      console.log('[Providers] isReady = true');
    }).catch((err: unknown) => {
      // Ignore AbortError from StrictMode unmount
      const error = err as { name?: string };
      if (error?.name === 'AbortError') {
        console.log('[Providers] getSession() aborted (StrictMode unmount), will retry on remount');
        return;
      }

      if (!isActive) return;

      console.error('[Providers] getSession() error:', err);
      markAuthInitialized();
      setIsReady(true);
    });

    // STEP 2: Set up onAuthStateChange for future events (SIGNED_IN, SIGNED_OUT, etc.)
    // We skip INITIAL_SESSION because we handled it above with getSession()
    console.log('[Providers] Setting up onAuthStateChange listener');
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event: string, session: { access_token?: string; expires_in?: number; user?: { email?: string } } | null) => {
      console.log('[Providers] onAuthStateChange:', event, 'session:', !!session);

      // Skip INITIAL_SESSION - we already handled it with getSession()
      if (event === 'INITIAL_SESSION') {
        console.log('[Providers] Skipping INITIAL_SESSION (handled by getSession)');
        return;
      }

      // Handle sign in
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        if (session?.access_token) {
          setAuthToken(session.access_token, session.expires_in);
          console.log('[Providers] Token updated after', event, 'user:', session.user?.email);
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
        console.log('[Providers] SIGNED_OUT - clearing auth');
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

    return () => {
      console.log('[Providers] Cleanup');
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
