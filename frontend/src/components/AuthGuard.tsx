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
  const [authState, setAuthState] = useState<"loading" | "authenticated" | "redirecting">("loading");

  useEffect(() => {
    let isMounted = true;

    const checkAuth = async () => {
      try {
        const supabase = createClient();
        const { data: { session }, error } = await supabase.auth.getSession();

        if (!isMounted) return;

        if (error || !session) {
          // No session - redirect to login
          console.log("[AuthGuard] No session, redirecting to login...");
          setAuthState("redirecting");
          // Use window.location for reliable redirect
          window.location.href = "/auth/login";
          return;
        }

        // User is authenticated
        console.log("[AuthGuard] Session valid, user authenticated");
        setAuthState("authenticated");
      } catch (err) {
        console.error("[AuthGuard] Error checking auth:", err);
        if (isMounted) {
          setAuthState("redirecting");
          window.location.href = "/auth/login";
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
