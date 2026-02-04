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

  console.log("[Callback] Processing OAuth callback, next:", next);

  if (code) {
    const cookieStore = await cookies();

    // Create supabase client that can set cookies on the response
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options);
            });
          },
        },
      }
    );

    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      // Validate that the session was actually created
      const {
        data: { user },
        error: userError,
      } = await supabase.auth.getUser();

      if (user && !userError) {
        console.log("[Callback] OAuth success, user:", user.email);

        // Handle different environments
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

        // Use NextResponse.redirect - cookies are already set via cookieStore
        return NextResponse.redirect(redirectUrl);
      }

      console.error("[Callback] User validation failed:", userError);
    } else {
      console.error("[Callback] Code exchange failed:", error);
    }
  } else {
    console.error("[Callback] No code provided");
  }

  return NextResponse.redirect(`${origin}/auth/error`);
}
