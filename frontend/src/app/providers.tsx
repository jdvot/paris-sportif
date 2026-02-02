"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ApiError } from "@/lib/api/custom-instance";
import { createClient } from "@/lib/supabase/client";

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  // Memoized auth error handler
  const handleAuthError = useCallback((error: unknown) => {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        // Session expired - sign out and redirect to login
        const supabase = createClient();
        supabase.auth.signOut().then(() => {
          router.push("/auth/login");
        });
      } else if (error.status === 403) {
        // Premium access required - redirect to plans
        router.push("/plans");
      }
    }
  }, [router]);

  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              // Don't retry on auth errors
              if (error instanceof ApiError && [401, 403].includes(error.status)) {
                return false;
              }
              return failureCount < 3;
            },
          },
        },
        queryCache: new QueryCache({
          onError: (error) => handleAuthError(error),
        }),
        mutationCache: new MutationCache({
          onError: (error) => handleAuthError(error),
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
