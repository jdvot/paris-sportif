import { updateSession } from "@/lib/supabase/middleware";
import { NextResponse, type NextRequest } from "next/server";

// Routes that DON'T require authentication (public pages)
const PUBLIC_ROUTES = [
  "/auth/login",
  "/auth/signup",
  "/auth/forgot-password",
  "/auth/callback",
  "/auth/confirm",
  "/",           // Home page - public pour démonstration
  "/matches",    // Liste des matchs - public
  "/standings",  // Classements - public
  "/picks",      // Picks basiques - public (picks/all est premium)
  "/plans",      // Page des abonnements - public
];

// Routes that require premium role
const PREMIUM_ROUTES = ["/analysis", "/picks/all"];

// Routes that require admin role
const ADMIN_ROUTES = ["/admin", "/sync"];

export async function middleware(request: NextRequest) {
  const { supabaseResponse, user, supabase } = await updateSession(request);
  const pathname = request.nextUrl.pathname;

  // Check if route is public
  const isAuthRoute = pathname.startsWith("/auth/");
  const isPublicRoute = PUBLIC_ROUTES.some((route) =>
    route === "/" ? pathname === "/" : pathname.startsWith(route)
  );

  if (isPublicRoute) {
    // Redirect authenticated users away from auth pages only (not other public pages)
    if (user && isAuthRoute && !pathname.includes("/callback") && !pathname.includes("/confirm")) {
      return NextResponse.redirect(new URL("/", request.url));
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
