import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import type { CookieOptions } from "@supabase/ssr";

/**
 * OAuth callback route handler
 *
 * This route exchanges the OAuth code for a session and redirects the user.
 * CRITICAL: Cookies must be set on the redirect response itself, not via cookieStore.
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/";

  console.log("[Callback] ===== OAUTH CALLBACK START =====");
  console.log("[Callback] Full URL:", request.url);
  console.log("[Callback] Origin:", origin);
  console.log("[Callback] Code present:", !!code);
  console.log("[Callback] Next param:", next);
  console.log("[Callback] Timestamp:", new Date().toISOString());

  if (code) {
    console.log("[Callback] Getting cookie store...");
    const cookieStore = await cookies();

    // Log existing cookies before exchange
    const existingCookies = cookieStore.getAll();
    const supabaseCookies = existingCookies.filter((c) => c.name.startsWith("sb-"));
    console.log("[Callback] Existing Supabase cookies:", supabaseCookies.map((c) => c.name));

    // Collect cookies to set on the redirect response
    // IMPORTANT: We can't use cookieStore.set() because it doesn't work with NextResponse.redirect()
    const cookiesToSet: { name: string; value: string; options: CookieOptions }[] = [];

    // Create supabase client that collects cookies instead of setting them immediately
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            const cookies = cookieStore.getAll();
            console.log("[Callback] getAll() called, returning", cookies.length, "cookies");
            return cookies;
          },
          setAll(cookies) {
            console.log("[Callback] setAll() called with", cookies.length, "cookies:", cookies.map((c) => c.name));
            // Collect cookies instead of setting them - we'll set them on the redirect response
            cookiesToSet.push(...cookies);
          },
        },
      }
    );

    console.log("[Callback] Exchanging code for session...");
    const { data: sessionData, error } = await supabase.auth.exchangeCodeForSession(code);
    console.log("[Callback] exchangeCodeForSession result - session:", !!sessionData?.session, "error:", error?.message || "none");
    console.log("[Callback] Cookies collected:", cookiesToSet.length);

    if (!error && sessionData?.session) {
      console.log("[Callback] OAuth SUCCESS - user:", sessionData.session.user.email, "id:", sessionData.session.user.id);

      // Handle different environments
      const forwardedHost = request.headers.get("x-forwarded-host");
      const isLocalEnv = process.env.NODE_ENV === "development";

      console.log("[Callback] Environment:", isLocalEnv ? "development" : "production");
      console.log("[Callback] x-forwarded-host:", forwardedHost || "none");

      let redirectUrl: string;
      if (isLocalEnv) {
        redirectUrl = `${origin}${next}`;
      } else if (forwardedHost) {
        redirectUrl = `https://${forwardedHost}${next}`;
      } else {
        redirectUrl = `${origin}${next}`;
      }

      console.log("[Callback] Redirecting to:", redirectUrl);

      // Create redirect response and set ALL cookies on it
      const response = NextResponse.redirect(redirectUrl);

      cookiesToSet.forEach(({ name, value, options }) => {
        console.log("[Callback] Setting cookie on response:", name, "options:", JSON.stringify(options));
        // CRITICAL: Ensure cookies are NOT httpOnly so client JavaScript can read them
        // This is required for onAuthStateChange to detect the session
        const isProduction = process.env.VERCEL_ENV === "production" || process.env.NODE_ENV === "production";
        response.cookies.set(name, value, {
          ...options,
          httpOnly: false, // Must be false for client-side access
          secure: true, // Always true for Vercel HTTPS
          sameSite: "lax", // Lax is recommended for auth cookies
          path: "/", // Ensure cookie is available on all paths
        });
        console.log("[Callback] Cookie set:", name, "secure:", true, "isProduction:", isProduction);
      });

      console.log("[Callback] Response cookies set:", response.cookies.getAll().map(c => c.name));
      console.log("[Callback] First cookie details:", JSON.stringify(response.cookies.getAll()[0]));
      console.log("[Callback] ===== OAUTH CALLBACK END (success) =====");

      return response;
    }

    if (error) {
      console.error("[Callback] Code exchange failed:", error.message, error.status);
    } else {
      console.error("[Callback] No session returned from exchange");
    }
  } else {
    console.error("[Callback] No code provided in callback URL");
  }

  console.log("[Callback] ===== OAUTH CALLBACK END (error) =====");
  return NextResponse.redirect(`${origin}/auth/error`);
}
