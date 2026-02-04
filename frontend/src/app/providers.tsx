"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { createClient } from "@/lib/supabase/client";
import { setAuthToken, clearAuthToken } from "@/lib/auth/token-store";

// Flag to prevent multiple redirects
let isRedirecting = false;

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

  // Reset redirect flag on mount (new page load)
  useEffect(() => {
    isRedirecting = false;
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
      try {
        // Clear OAuth pending flag if present
        if (typeof window !== 'undefined') {
          sessionStorage.removeItem('oauth_pending');
        }

        // Read session from cookies - this is synchronous, no network call
        // The middleware has already refreshed the token if needed
        const { data: { session } } = await supabase.auth.getSession();

        if (session?.access_token) {
          setAuthToken(session.access_token, session.expires_in);
          console.log('[Providers] Token set from session');

          // Clear redirect marker - we have a session
          if (typeof window !== 'undefined') {
            sessionStorage.removeItem('auth_redirect_time');
          }
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
        setIsReady(true);
      }
    };

    initializeAuth();

    // Listen for auth state changes AFTER initial hydration
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event: string, session: { access_token?: string; expires_in?: number } | null) => {
      console.log('[Providers] Auth state changed:', event, !!session);

      // Update token store with new token
      if (session?.access_token) {
        setAuthToken(session.access_token, session.expires_in);
      } else {
        clearAuthToken();
      }

      // When user signs in (including OAuth callback), invalidate all queries
      // so they refetch with the new auth token
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        console.log('[Providers] Invalidating queries after auth change');
        queryClient.invalidateQueries();
      }

      // When user signs out, clear the cache and token
      if (event === 'SIGNED_OUT') {
        console.log('[Providers] Clearing cache after sign out');
        clearAuthToken();
        queryClient.clear();
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [queryClient]);

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
