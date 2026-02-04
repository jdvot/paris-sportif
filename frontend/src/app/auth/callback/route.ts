import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

/**
 * OAuth callback route handler - Official Supabase pattern
 *
 * Uses cookieStore.set() directly in setAll - Next.js 15 propagates
 * these cookies to the redirect response automatically.
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/";

  console.log("[Callback] OAuth callback - code:", !!code, "next:", next);

  if (code) {
    // Next.js 15: cookies() returns a Promise
    const cookieStore = await cookies();

    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            console.log("[Callback] setAll called with", cookiesToSet.length, "cookies");
            cookiesToSet.forEach(({ name, value, options }) => {
              console.log("[Callback] Setting cookie:", name);
              cookieStore.set(name, value, options);
            });
          },
        },
      }
    );

    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      console.log("[Callback] Session exchanged successfully");

      // Determine redirect URL
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
      return NextResponse.redirect(redirectUrl);
    }

    console.error("[Callback] Exchange failed:", error.message);
  }

  return NextResponse.redirect(`${origin}/auth/error`);
}
