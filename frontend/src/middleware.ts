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

  const { supabaseResponse, user, supabase } = await updateSession(request);

  // Check if route is public
  const isAuthRoute = pathname.startsWith("/auth/");
  const isPublicRoute = PUBLIC_ROUTES.some((route) =>
    route === "/" ? pathname === "/" : pathname.startsWith(route)
  );
  const isAuthCallbackRoute = AUTH_CALLBACK_ROUTES.has(pathname);

  if (isPublicRoute) {
    // Redirect authenticated users away from auth pages to their intended destination
    // Use Set lookup instead of string matching for callback routes
    if (user && isAuthRoute && !isAuthCallbackRoute) {
      // Check if there's a 'next' parameter to redirect to (prevent open redirect)
      const rawNext = request.nextUrl.searchParams.get("next") || "/";
      const nextUrl = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/";

      return NextResponse.redirect(new URL(nextUrl, request.url));
    }
    return supabaseResponse;
  }

  // ALL other routes require authentication
  if (!user) {
    // Redirect to login with return URL
    const loginUrl = new URL("/auth/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Check role-based access for premium and admin routes
  const requiresRoleCheck =
    PREMIUM_ROUTES.some((route) => pathname.startsWith(route)) ||
    ADMIN_ROUTES.some((route) => pathname.startsWith(route));

  if (requiresRoleCheck) {
    // Fetch user profile to get role
    const { data: profile } = await supabase
      .from("user_profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    const role = profile?.role || "free";

    // Check premium routes
    if (PREMIUM_ROUTES.some((route) => pathname.startsWith(route))) {
      if (role === "free") {
        return NextResponse.redirect(new URL("/upgrade", request.url));
      }
    }

    // Check admin routes
    if (ADMIN_ROUTES.some((route) => pathname.startsWith(route))) {
      if (role !== "admin") {
        return NextResponse.redirect(new URL("/", request.url));
      }
    }
  }

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
