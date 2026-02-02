"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState } from "react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ApiError } from "@/lib/api/custom-instance";
import { createClient } from "@/lib/supabase/client";

// Flag to prevent multiple redirects
let isRedirecting = false;

function handleAuthError(status: number) {
  // Prevent multiple redirects
  if (isRedirecting) return;

  if (status === 401) {
    console.log('[Auth] 401 detected, redirecting to login...');
    isRedirecting = true;
    const supabase = createClient();
    supabase.auth.signOut().then(() => {
      window.location.href = "/auth/login";
    });
  } else if (status === 403) {
    console.log('[Auth] 403 detected, redirecting to plans...');
    isRedirecting = true;
    window.location.href = "/plans";
  }
}

export function Providers({ children }: { children: React.ReactNode }) {
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

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
