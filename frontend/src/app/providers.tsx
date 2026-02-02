"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ApiError } from "@/lib/api/custom-instance";
import { createClient } from "@/lib/supabase/client";
import { setAuthToken, clearAuthToken } from "@/lib/auth/token-store";

// Flag to prevent multiple redirects (reset on page load)
let isRedirecting = false;

function handleAuthError(status: number) {
  // Prevent multiple redirects
  if (isRedirecting || typeof window === 'undefined') return;

  const currentPath = window.location.pathname;

  // Don't redirect if already on an auth page - prevents redirect loops
  if (currentPath.startsWith('/auth/')) {
    console.log('[Auth] Already on auth page, skipping redirect');
    return;
  }

  if (status === 401) {
    console.log('[Auth] 401 detected, forcing redirect to login...');
    isRedirecting = true;
    const loginUrl = `/auth/login?next=${encodeURIComponent(currentPath)}`;

    // Sign out in background, redirect immediately
    const supabase = createClient();
    supabase.auth.signOut().catch(() => {});
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
            const err = error as { name?: string; status?: number };
            if (err?.name === 'AbortError') {
              return;
            }

            // Check for ApiError by instance or by property (for minified code)
            const isApiError = error instanceof ApiError ||
              (err?.name === 'ApiError' && typeof err?.status === 'number');

            if (isApiError && err.status) {
              handleAuthError(err.status);
            }
          },
        }),
        mutationCache: new MutationCache({
          onError: (error) => {
            const err = error as { name?: string; status?: number };
            if (err?.name === 'AbortError') {
              return;
            }

            const isApiError = error instanceof ApiError ||
              (err?.name === 'ApiError' && typeof err?.status === 'number');

            if (isApiError && err.status) {
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
          }
        } else {
          // No valid user - clear any stale token
          clearAuthToken();
        }
      } catch (err) {
        // Timeout or other error - log and continue without auth
        console.error('[Providers] Auth init error:', err);
        clearAuthToken();
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
