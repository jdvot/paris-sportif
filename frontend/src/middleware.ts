import { updateSession } from "@/lib/supabase/middleware";
import { NextResponse, type NextRequest } from "next/server";

// Routes that DON'T require authentication (public pages)
const PUBLIC_ROUTES = [
  "/",           // Homepage - public (shows different content based on auth)
  "/auth/login",
  "/auth/signup",
  "/auth/forgot-password",
  "/auth/callback",
  "/auth/confirm",
  "/auth/error",
  "/auth/reset-password",
  "/plans",      // Page des abonnements - public (pour upgrade)
  "/privacy",    // Privacy policy - public
  "/terms",      // Terms of service - public
];

// Auth callback routes that should not redirect even when authenticated
// Using a Set for O(1) lookup instead of string matching
const AUTH_CALLBACK_ROUTES = new Set([
  "/auth/callback",
  "/auth/confirm",
  "/auth/error",
  "/auth/reset-password",
]);

// Routes that require premium role
const PREMIUM_ROUTES = ["/analysis", "/picks/all"];

// Routes that require admin role
const ADMIN_ROUTES = ["/admin", "/sync"];

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  console.log("[Middleware] ===== START =====");
  console.log("[Middleware] Request:", pathname);
  console.log("[Middleware] Full URL:", request.url);

  const { supabaseResponse, user, supabase } = await updateSession(request);
  console.log("[Middleware] updateSession complete - user:", user?.email || "none", "id:", user?.id || "none");

  // Check if route is public
  const isAuthRoute = pathname.startsWith("/auth/");
  const isPublicRoute = PUBLIC_ROUTES.some((route) =>
    route === "/" ? pathname === "/" : pathname.startsWith(route)
  );
  const isAuthCallbackRoute = AUTH_CALLBACK_ROUTES.has(pathname);

  console.log("[Middleware] Route analysis:", {
    isAuthRoute,
    isPublicRoute,
    isAuthCallbackRoute,
    pathname,
  });

  if (isPublicRoute) {
    console.log("[Middleware] Public route detected");
    // Redirect authenticated users away from auth pages to their intended destination
    // Use Set lookup instead of string matching for callback routes
    if (user && isAuthRoute && !isAuthCallbackRoute) {
      // Check if there's a 'next' parameter to redirect to
      const nextUrl = request.nextUrl.searchParams.get("next") || "/";

      console.log("[Middleware] User authenticated on auth page, redirecting to:", nextUrl);
      console.log("[Middleware] ===== END (redirect to next) =====");
      return NextResponse.redirect(new URL(nextUrl, request.url));
    }
    console.log("[Middleware] ===== END (public route passthrough) =====");
    return supabaseResponse;
  }

  // ALL other routes require authentication
  if (!user) {
    console.log("[Middleware] No user for protected route:", pathname, "- redirecting to login");
    // Redirect to login with return URL
    const loginUrl = new URL("/auth/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    console.log("[Middleware] ===== END (redirect to login) =====");
    return NextResponse.redirect(loginUrl);
  }

  console.log("[Middleware] User:", user.email, "accessing protected route:", pathname);

  // Check role-based access for premium and admin routes
  const requiresRoleCheck =
    PREMIUM_ROUTES.some((route) => pathname.startsWith(route)) ||
    ADMIN_ROUTES.some((route) => pathname.startsWith(route));

  console.log("[Middleware] Requires role check:", requiresRoleCheck);

  if (requiresRoleCheck) {
    // Fetch user profile to get role
    console.log("[Middleware] Fetching user profile for role check...");
    const { data: profile, error: profileError } = await supabase
      .from("user_profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    if (profileError) {
      console.error("[Middleware] Profile fetch error:", profileError.message);
    }

    const role = profile?.role || "free";
    console.log("[Middleware] User role:", role);

    // Check premium routes
    if (PREMIUM_ROUTES.some((route) => pathname.startsWith(route))) {
      console.log("[Middleware] Premium route check - role:", role);
      if (role === "free") {
        console.log("[Middleware] ===== END (redirect to upgrade) =====");
        return NextResponse.redirect(new URL("/upgrade", request.url));
      }
    }

    // Check admin routes
    if (ADMIN_ROUTES.some((route) => pathname.startsWith(route))) {
      console.log("[Middleware] Admin route check - role:", role);
      if (role !== "admin") {
        console.log("[Middleware] ===== END (redirect to home - not admin) =====");
        return NextResponse.redirect(new URL("/", request.url));
      }
    }
  }

  console.log("[Middleware] ===== END (passthrough) =====");
  return supabaseResponse;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API proxy routes - forwarded to backend, auth handled there)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - icons (PWA icons folder)
     * - public folder files
     * - manifest.webmanifest, sw.js (PWA files)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|icons|manifest\\.webmanifest|sw\\.js|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|json)$).*)",
  ],
};
