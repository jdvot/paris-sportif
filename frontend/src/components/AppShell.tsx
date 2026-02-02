"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Loader2 } from "lucide-react";
import { Header } from "./Header";

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
 */
export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [authState, setAuthState] = useState<"loading" | "authenticated" | "redirecting">(
    // Start as authenticated for public routes to avoid flash
    isPublicRoute(pathname) ? "authenticated" : "loading"
  );

  useEffect(() => {
    // Skip auth check for public routes
    if (isPublicRoute(pathname)) {
      setAuthState("authenticated");
      return;
    }

    let isMounted = true;
    let timeoutId: NodeJS.Timeout;

    const checkAuth = async () => {
      try {
        const supabase = createClient();

        // Short timeout - don't block UI for too long
        const timeoutPromise = new Promise<null>((_, reject) => {
          timeoutId = setTimeout(() => reject(new Error("Auth check timeout")), 3000);
        });

        const sessionPromise = supabase.auth.getSession();

        const result = await Promise.race([sessionPromise, timeoutPromise]);
        clearTimeout(timeoutId);

        if (!isMounted) return;

        if (!result || !result.data?.session) {
          // No session - redirect to login immediately
          console.log("[AppShell] No session, redirecting to login...");
          setAuthState("redirecting");
          redirectToLogin(pathname);
          return;
        }

        // User is authenticated
        console.log("[AppShell] Session valid, user authenticated");
        setAuthState("authenticated");
      } catch (err) {
        // Ignore AbortError - this happens during normal navigation/unmount
        if (err instanceof Error && err.name === "AbortError") {
          console.log("[AppShell] Request aborted (normal during navigation)");
          return;
        }

        // On timeout, redirect to login (don't trust stale session)
        console.warn("[AppShell] Auth check failed, redirecting:", err);
        if (isMounted) {
          setAuthState("redirecting");
          redirectToLogin(pathname);
        }
      }
    };

    checkAuth();

    // Listen for auth state changes
    const supabase = createClient();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      console.log("[AppShell] Auth state change:", event);
      if (event === "SIGNED_OUT" || (!session && !isPublicRoute(pathname))) {
        setAuthState("redirecting");
        redirectToLogin(pathname);
      }
    });

    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
      subscription.unsubscribe();
    };
  }, [pathname]);

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
