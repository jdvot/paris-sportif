"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Loader2 } from "lucide-react";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * AuthGuard component that shows a fullscreen loader while checking authentication.
 * Redirects to login if the user is not authenticated.
 * This prevents users from seeing the dashboard content before auth is verified.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        // No session - redirect to login
        router.replace("/auth/login");
        return;
      }

      // User is authenticated
      setIsAuthenticated(true);
      setIsLoading(false);
    };

    checkAuth();

    // Listen for auth state changes
    const supabase = createClient();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT" || !session) {
        router.replace("/auth/login");
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  // Show fullscreen loader while checking auth
  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-white dark:bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary-500" />
          <p className="text-gray-600 dark:text-slate-400 text-sm">
            Verification en cours...
          </p>
        </div>
      </div>
    );
  }

  // Not authenticated - will redirect, show nothing
  if (!isAuthenticated) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-white dark:bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary-500" />
          <p className="text-gray-600 dark:text-slate-400 text-sm">
            Redirection...
          </p>
        </div>
      </div>
    );
  }

  // Authenticated - render children
  return <>{children}</>;
}
