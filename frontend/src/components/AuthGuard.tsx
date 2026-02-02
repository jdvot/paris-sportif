"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Loader2 } from "lucide-react";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * AuthGuard component that shows a fullscreen loader while checking authentication.
 * Redirects to login if the user is not authenticated.
 * Note: The middleware already handles server-side auth checks, so this is a client-side backup.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const [authState, setAuthState] = useState<"loading" | "authenticated" | "redirecting">("loading");

  useEffect(() => {
    let isMounted = true;
    let timeoutId: NodeJS.Timeout;

    const checkAuth = async () => {
      try {
        const supabase = createClient();

        // Add timeout to prevent infinite loading
        const timeoutPromise = new Promise<null>((_, reject) => {
          timeoutId = setTimeout(() => reject(new Error("Auth check timeout")), 5000);
        });

        const sessionPromise = supabase.auth.getSession();

        const result = await Promise.race([sessionPromise, timeoutPromise]);
        clearTimeout(timeoutId);

        if (!isMounted) return;

        if (!result || !result.data?.session) {
          // No session - redirect to login
          console.log("[AuthGuard] No session, redirecting to login...");
          setAuthState("redirecting");
          window.location.href = "/auth/login";
          return;
        }

        // User is authenticated
        console.log("[AuthGuard] Session valid, user authenticated");
        setAuthState("authenticated");
      } catch (err) {
        // Ignore AbortError - this happens during normal navigation/unmount
        if (err instanceof Error && err.name === "AbortError") {
          console.log("[AuthGuard] Request aborted (normal during navigation)");
          return;
        }

        // On timeout or error, trust that middleware already checked auth
        // and render children instead of blocking forever
        console.warn("[AuthGuard] Auth check failed, trusting middleware:", err);
        if (isMounted) {
          setAuthState("authenticated");
        }
      }
    };

    checkAuth();

    // Listen for auth state changes
    const supabase = createClient();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      console.log("[AuthGuard] Auth state change:", event);
      if (event === "SIGNED_OUT" || !session) {
        setAuthState("redirecting");
        window.location.href = "/auth/login";
      }
    });

    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
      subscription.unsubscribe();
    };
  }, []);

  // Show fullscreen loader while checking auth or redirecting
  if (authState === "loading" || authState === "redirecting") {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-white dark:bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary-500" />
          <p className="text-gray-600 dark:text-slate-400 text-sm">
            {authState === "loading" ? "Verification en cours..." : "Redirection..."}
          </p>
        </div>
      </div>
    );
  }

  // Authenticated - render children
  return <>{children}</>;
}
