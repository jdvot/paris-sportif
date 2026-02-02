"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ApiError } from "@/lib/api/custom-instance";
import { createClient } from "@/lib/supabase/client";
import { setAuthToken, clearAuthToken } from "@/lib/auth/token-store";

// Flag to prevent multiple redirects (reset on page load)
let isRedirecting = false;

function handleAuthError(status: number) {
  // Prevent multiple redirects
  if (isRedirecting || typeof window === 'undefined') return;

  if (status === 401) {
    console.log('[Auth] 401 detected, forcing redirect to login...');
    isRedirecting = true;
    // Force immediate redirect - don't wait for signOut
    const currentPath = window.location.pathname;
    const loginUrl = `/auth/login?next=${encodeURIComponent(currentPath)}`;

    // Sign out in background, redirect immediately
    const supabase = createClient();
    supabase.auth.signOut().catch(() => {});
    window.location.replace(loginUrl);
  } else if (status === 403) {
    console.log('[Auth] 403 detected, redirecting to plans...');
    isRedirecting = true;
    window.location.replace("/plans");
  }
}

export function Providers({ children }: { children: React.ReactNode }) {
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

  // Listen for auth state changes and update token store + invalidate queries
  // This is crucial for hydrating the session after OAuth callback
  useEffect(() => {
    const supabase = createClient();

    // Get initial session and populate token store
    supabase.auth.getSession().then(({ data: { session } }) => {
      console.log('[Providers] Initial session:', !!session);
      if (session?.access_token) {
        setAuthToken(session.access_token);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      console.log('[Providers] Auth state changed:', event, !!session);

      // Update token store with new token
      if (session?.access_token) {
        setAuthToken(session.access_token);
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

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
