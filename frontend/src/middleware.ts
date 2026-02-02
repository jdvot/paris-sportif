import { updateSession } from "@/lib/supabase/middleware";
import { NextResponse, type NextRequest } from "next/server";

// Routes that require authentication
const PROTECTED_ROUTES = ["/profile", "/history", "/alerts"];

// Routes that require premium role
const PREMIUM_ROUTES = ["/analysis", "/picks/all"];

// Routes that require admin role
const ADMIN_ROUTES = ["/admin", "/sync"];

// Routes that should redirect to home if authenticated
const AUTH_ROUTES = ["/auth/login", "/auth/signup"];

// Public routes that don't need any checks
const PUBLIC_ROUTES = ["/", "/matches", "/standings", "/picks", "/auth"];

export async function middleware(request: NextRequest) {
  const { supabaseResponse, user, supabase } = await updateSession(request);
  const pathname = request.nextUrl.pathname;

  // Allow public routes
  if (PUBLIC_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`))) {
    // But redirect authenticated users away from auth pages
    if (user && AUTH_ROUTES.some((route) => pathname.startsWith(route))) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return supabaseResponse;
  }

  // Check authentication for protected routes
  if (
    PROTECTED_ROUTES.some((route) => pathname.startsWith(route)) ||
    PREMIUM_ROUTES.some((route) => pathname.startsWith(route)) ||
    ADMIN_ROUTES.some((route) => pathname.startsWith(route))
  ) {
    if (!user) {
      // Redirect to login with return URL
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(loginUrl);
    }

    // Check role-based access for premium and admin routes
    if (
      PREMIUM_ROUTES.some((route) => pathname.startsWith(route)) ||
      ADMIN_ROUTES.some((route) => pathname.startsWith(route))
    ) {
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
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
