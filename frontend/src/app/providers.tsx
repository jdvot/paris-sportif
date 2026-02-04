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
    console.log('[Auth] 401 detected, signing out and redirecting to login...');
    isRedirecting = true;

    // Mark that we're redirecting (persists across the navigation)
    sessionStorage.setItem('auth_redirect_time', Date.now().toString());

    const loginUrl = `/auth/login?next=${encodeURIComponent(currentPath)}`;

    // IMPORTANT: Wait for signOut to complete before redirecting
    // This ensures cookies are cleared so middleware doesn't redirect back
    try {
      const supabase = createClient();
      await supabase.auth.signOut();
      console.log('[Auth] Sign out complete, redirecting...');
    } catch (e) {
      console.error('[Auth] Sign out error (continuing anyway):', e);
    }

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

    // Initialize auth: validate user with server, then get token
    const initializeAuth = async () => {
      try {
        // Use getUser() first to validate with server (not just local storage)
        // Wrap with timeout to prevent hanging (known Supabase issue)
        const getUserWithTimeout = async () => {
          const timeoutPromise = new Promise<{ data: { user: null }; error: Error }>((resolve) =>
            setTimeout(() => resolve({ data: { user: null }, error: new Error('Auth timeout') }), 10000)
          );
          return Promise.race([supabase.auth.getUser(), timeoutPromise]);
        };

        const { data: { user }, error: userError } = await getUserWithTimeout();
        console.log('[Providers] Initial user check:', !!user, userError?.message || '');

        if (user && !userError) {
          // User is valid, get the session for the token
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.access_token) {
            // Pass expiration info to token store
            const expiresIn = session.expires_in;
            setAuthToken(session.access_token, expiresIn);
            console.log('[Providers] Token set, expires in:', expiresIn, 'seconds');

            // Clear redirect marker - we're authenticated now
            if (typeof window !== 'undefined') {
              sessionStorage.removeItem('auth_redirect_time');
            }
          }
        } else {
          // No valid user - clear any stale token
          clearAuthToken();
        }
      } catch (err) {
        // Handle different error types
        const error = err as { name?: string; message?: string };

        // AbortError = request cancelled (navigation, component unmount)
        // Don't clear token - user may still be valid
        if (error?.name === 'AbortError') {
          console.log('[Providers] Auth init aborted (navigation), keeping existing token');
          // Don't clear token on AbortError - just continue
        } else {
          // Timeout or other error - log and continue without auth
          console.error('[Providers] Auth init error:', err);
          clearAuthToken();
        }
      } finally {
        // Always mark as ready, even on error
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
