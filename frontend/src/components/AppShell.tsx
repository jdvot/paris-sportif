"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Loader2 } from "lucide-react";
import { Header } from "./Header";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";

// Public routes that don't require authentication
const PUBLIC_ROUTES = [
  "/auth/login",
  "/auth/signup",
  "/auth/forgot-password",
  "/auth/callback",
  "/auth/confirm",
  "/auth/error",
  "/auth/reset-password",
  "/plans",
];

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some((route) => pathname.startsWith(route));
}

/**
 * Redirect to login with current path as ?next= parameter
 */
function redirectToLogin(currentPath: string) {
  const loginUrl = `/auth/login?next=${encodeURIComponent(currentPath)}`;
  window.location.replace(loginUrl);
}

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * AppShell - Handles authentication check and shows fullscreen loader
 * This component wraps the entire app to ensure the loader covers everything
 *
 * IMPORTANT: To avoid race conditions after OAuth callback:
 * 1. Subscribe to onAuthStateChange FIRST
 * 2. Then check initial session
 * 3. Give cookies time to hydrate after OAuth redirect
 */
export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [authState, setAuthState] = useState<"loading" | "authenticated" | "redirecting">(
    // Start as authenticated for public routes to avoid flash
    isPublicRoute(pathname) ? "authenticated" : "loading"
  );
  // Track if auth was resolved by onAuthStateChange to avoid double-redirect
  const authResolvedRef = useRef(false);

  useEffect(() => {
    // Skip auth check for public routes
    if (isPublicRoute(pathname)) {
      setAuthState("authenticated");
      return;
    }

    let isMounted = true;
    let fallbackTimeoutId: NodeJS.Timeout;

    // Use a single Supabase client instance for consistency
    const supabase = createClient();

    // STEP 1: Subscribe to auth state changes FIRST
    // This catches the SIGNED_IN event from OAuth before getSession returns
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event: AuthChangeEvent, session: Session | null) => {
      console.log("[AppShell] Auth event:", event, "hasSession:", !!session);

      if (!isMounted) return;

      if (event === "SIGNED_IN" && session) {
        // User just logged in (e.g., from OAuth callback)
        authResolvedRef.current = true;
        setAuthState("authenticated");
        clearTimeout(fallbackTimeoutId);
      } else if (event === "SIGNED_OUT") {
        // User logged out
        authResolvedRef.current = true;
        setAuthState("redirecting");
        redirectToLogin(pathname);
      } else if (event === "TOKEN_REFRESHED" && !session) {
        // Token refresh failed - session expired
        authResolvedRef.current = true;
        setAuthState("redirecting");
        redirectToLogin(pathname);
      } else if (event === "INITIAL_SESSION") {
        // Initial session loaded from cookies
        if (session) {
          authResolvedRef.current = true;
          setAuthState("authenticated");
          clearTimeout(fallbackTimeoutId);
        }
        // If no session on INITIAL_SESSION, wait for fallback timeout
      }
    });

    // STEP 2: Check initial session (backup for when no events fire)
    const checkInitialSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        console.log("[AppShell] getSession result:", !!session);

        if (!isMounted || authResolvedRef.current) return;

        if (session) {
          authResolvedRef.current = true;
          setAuthState("authenticated");
          clearTimeout(fallbackTimeoutId);
        }
        // If no session, let the fallback timeout handle redirect
      } catch (err) {
        // Ignore AbortError - this happens during normal navigation/unmount
        if (err instanceof Error && err.name === "AbortError") {
          console.log("[AppShell] Request aborted (normal during navigation)");
          return;
        }
        console.warn("[AppShell] getSession error:", err);
      }
    };

    checkInitialSession();

    // STEP 3: Fallback timeout - redirect if no auth after delay
    // This gives OAuth cookies time to hydrate (important after callback redirect)
    fallbackTimeoutId = setTimeout(() => {
      if (isMounted && !authResolvedRef.current && authState === "loading") {
        console.log("[AppShell] Fallback timeout - no session, redirecting to login");
        setAuthState("redirecting");
        redirectToLogin(pathname);
      }
    }, 1500); // 1.5 seconds is enough for cookies to hydrate

    return () => {
      isMounted = false;
      authResolvedRef.current = false;
      clearTimeout(fallbackTimeoutId);
      subscription.unsubscribe();
    };
  }, [pathname, authState]);

  // Show fullscreen loader while checking auth or redirecting (covers EVERYTHING)
  if (authState === "loading" || authState === "redirecting") {
    return (
      <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-white dark:bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary-500" />
          <p className="text-gray-600 dark:text-slate-400 text-sm">
            {authState === "loading" ? "Verification en cours..." : "Redirection..."}
          </p>
        </div>
      </div>
    );
  }

  // Authenticated - render full app with header
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        {children}
      </main>
      <footer className="border-t border-gray-200 dark:border-slate-700 py-6 text-center text-gray-600 dark:text-slate-400 text-sm">
        <p>Paris Sportif - Predictions basees sur IA</p>
        <p className="mt-1 text-xs">
          Avertissement: Les paris comportent des risques. Jouez
          responsablement.
        </p>
      </footer>
    </div>
  );
}
