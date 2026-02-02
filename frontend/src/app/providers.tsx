"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ApiError } from "@/lib/api/custom-instance";
import { createClient } from "@/lib/supabase/client";

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  // Use ref to always have access to current router in the error handler
  const routerRef = useRef(router);
  useEffect(() => {
    routerRef.current = router;
  }, [router]);

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
              if (err.status === 401) {
                // Session expired - sign out and redirect to login
                console.log('[Auth] 401 detected, redirecting to login...');
                const supabase = createClient();
                supabase.auth.signOut().then(() => {
                  routerRef.current.push("/auth/login");
                });
              } else if (err.status === 403) {
                // Premium access required - redirect to plans
                console.log('[Auth] 403 detected, redirecting to plans...');
                routerRef.current.push("/plans");
              }
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
              if (err.status === 401) {
                console.log('[Auth] 401 detected on mutation, redirecting to login...');
                const supabase = createClient();
                supabase.auth.signOut().then(() => {
                  routerRef.current.push("/auth/login");
                });
              } else if (err.status === 403) {
                console.log('[Auth] 403 detected on mutation, redirecting to plans...');
                routerRef.current.push("/plans");
              }
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
