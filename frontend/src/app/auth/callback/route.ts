import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

/**
 * OAuth callback route handler
 *
 * This route exchanges the OAuth code for a session and redirects the user.
 * Important: We validate the session with getUser() before redirecting to ensure
 * cookies are properly set and the user is authenticated.
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/picks";

  console.log("[Callback] Processing OAuth callback, next:", next);

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      // Validate that the session was actually created by checking the user
      // This ensures cookies are properly set before redirecting
      const {
        data: { user },
        error: userError,
      } = await supabase.auth.getUser();

      if (user && !userError) {
        console.log("[Callback] OAuth success, user:", user.email);

        // Handle different environments (Vercel preview, production, local)
        const forwardedHost = request.headers.get("x-forwarded-host");
        const isLocalEnv = process.env.NODE_ENV === "development";

        let redirectUrl: string;
        if (isLocalEnv) {
          // Local development
          redirectUrl = `${origin}${next}`;
        } else if (forwardedHost) {
          // Vercel deployment - use forwarded host
          redirectUrl = `https://${forwardedHost}${next}`;
        } else {
          // Fallback to origin
          redirectUrl = `${origin}${next}`;
        }

        console.log("[Callback] Redirecting to:", redirectUrl);
        return NextResponse.redirect(redirectUrl);
      }

      console.error("[Callback] User validation failed:", userError);
    } else {
      console.error("[Callback] Code exchange failed:", error);
    }
  } else {
    console.error("[Callback] No code provided");
  }

  // Return the user to an error page with instructions
  return NextResponse.redirect(`${origin}/auth/error`);
}
