import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import type { CookieOptions } from "@supabase/ssr";

/**
 * OAuth callback route handler
 *
 * IMPORTANT: In Next.js Route Handlers, cookies().set() does NOT automatically
 * transfer to NextResponse.redirect(). We must collect cookies and set them
 * explicitly on the redirect response.
 *
 * The flow:
 * 1. Exchange OAuth code for session
 * 2. Collect all cookies that Supabase wants to set
 * 3. Create redirect response
 * 4. Set cookies on the redirect response (with httpOnly: false for client access)
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/";

  console.log("[Callback] OAuth callback - code:", !!code, "next:", next);

  if (code) {
    const cookieStore = await cookies();

    // Collect cookies to set on the redirect response
    const collectedCookies: { name: string; value: string; options: CookieOptions }[] = [];

    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            // Collect cookies instead of setting them via cookieStore
            // We'll set them on the redirect response
            console.log("[Callback] Collecting", cookiesToSet.length, "cookies");
            collectedCookies.push(...cookiesToSet);
          },
        },
      }
    );

    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      console.log("[Callback] Session exchanged successfully");

      // Determine redirect URL based on environment
      const forwardedHost = request.headers.get("x-forwarded-host");
      const isLocalEnv = process.env.NODE_ENV === "development";

      let redirectUrl: string;
      if (isLocalEnv) {
        redirectUrl = `${origin}${next}`;
      } else if (forwardedHost) {
        redirectUrl = `https://${forwardedHost}${next}`;
      } else {
        redirectUrl = `${origin}${next}`;
      }

      console.log("[Callback] Redirecting to:", redirectUrl);

      // Create redirect response
      const response = NextResponse.redirect(redirectUrl);

      // Set ALL collected cookies on the redirect response
      // CRITICAL: httpOnly must be false for browser client to read them
      collectedCookies.forEach(({ name, value, options }) => {
        const cookieOptions = {
          ...options,
          // Ensure browser JavaScript can read the cookies
          httpOnly: false,
          // Ensure cookies work in production with HTTPS
          secure: process.env.NODE_ENV === "production",
          // Allow cookies to be sent with the redirect
          sameSite: "lax" as const,
          // Ensure path is set correctly
          path: "/",
        };
        console.log("[Callback] Setting cookie:", name, "options:", JSON.stringify(cookieOptions));
        response.cookies.set(name, value, cookieOptions);
      });

      console.log("[Callback] Cookies set on response:", collectedCookies.length);
      return response;
    }

    console.error("[Callback] Exchange failed:", error.message);
  }

  // Return to error page
  return NextResponse.redirect(`${origin}/auth/error`);
}
