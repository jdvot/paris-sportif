import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

/**
 * OAuth callback route handler
 *
 * This route exchanges the OAuth code for a session and redirects the user.
 * Important: Cookies must be properly set on the redirect response.
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

    // Create supabase client that can set cookies on the response
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
          setAll(cookiesToSet) {
            console.log("[Callback] setAll() called with", cookiesToSet.length, "cookies:", cookiesToSet.map((c) => c.name));
            cookiesToSet.forEach(({ name, value, options }) => {
              console.log("[Callback] Setting cookie:", name, "options:", JSON.stringify(options));
              cookieStore.set(name, value, options);
            });
          },
        },
      }
    );

    console.log("[Callback] Exchanging code for session...");
    const { data: sessionData, error } = await supabase.auth.exchangeCodeForSession(code);
    console.log("[Callback] exchangeCodeForSession result - session:", !!sessionData?.session, "error:", error?.message || "none");

    if (!error) {
      // Validate that the session was actually created
      console.log("[Callback] Validating user with getUser()...");
      const {
        data: { user },
        error: userError,
      } = await supabase.auth.getUser();

      console.log("[Callback] getUser() result - user:", user?.email || "none", "error:", userError?.message || "none");

      if (user && !userError) {
        console.log("[Callback] OAuth SUCCESS - user:", user.email, "id:", user.id);

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
        console.log("[Callback] ===== OAUTH CALLBACK END (success) =====");

        // Use NextResponse.redirect - cookies are already set via cookieStore
        return NextResponse.redirect(redirectUrl);
      }

      console.error("[Callback] User validation failed:", userError?.message);
    } else {
      console.error("[Callback] Code exchange failed:", error.message, error.status);
    }
  } else {
    console.error("[Callback] No code provided in callback URL");
  }

  console.log("[Callback] ===== OAUTH CALLBACK END (error) =====");
  return NextResponse.redirect(`${origin}/auth/error`);
}
