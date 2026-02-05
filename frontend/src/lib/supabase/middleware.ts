import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  console.log("[updateSession] Starting for path:", request.nextUrl.pathname);

  // Log existing cookies (only sb- prefixed for Supabase)
  const allCookies = request.cookies.getAll();
  const supabaseCookies = allCookies.filter((c) => c.name.startsWith("sb-"));
  console.log("[updateSession] Supabase cookies found:", supabaseCookies.map((c) => c.name));

  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          const cookies = request.cookies.getAll();
          console.log("[updateSession] getAll() called, returning", cookies.length, "cookies");
          return cookies;
        },
        setAll(cookiesToSet) {
          console.log("[updateSession] setAll() called with", cookiesToSet.length, "cookies:", cookiesToSet.map((c) => c.name));
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({
            request,
          });
          // Let Supabase manage cookie options - don't override httpOnly
          // Supabase SSR handles this correctly for browser client access
          cookiesToSet.forEach(({ name, value, options }) => {
            supabaseResponse.cookies.set(name, value, options);
          });
        },
      },
    }
  );

  // IMPORTANT: Avoid writing any logic between createServerClient and
  // supabase.auth.getUser(). A simple mistake could make it very hard to debug
  // issues with users being randomly logged out.
  console.log("[updateSession] Calling getUser()...");

  // Add timeout to prevent middleware hanging if Supabase is slow
  const timeoutPromise = new Promise<{ data: { user: null }; error: { message: string }; timedOut: true }>((resolve) => {
    setTimeout(() => resolve({ data: { user: null }, error: { message: 'Timeout' }, timedOut: true }), 3000);
  });

  const result = await Promise.race([
    supabase.auth.getUser().then(r => ({ ...r, timedOut: false })),
    timeoutPromise,
  ]) as { data: { user: import('@supabase/supabase-js').User | null }; error?: { message: string } | null; timedOut: boolean };

  let user = result.data.user;

  if (result.error) {
    console.error("[updateSession] getUser() error:", result.error.message);
  }

  // On timeout or error, fallback to getSession() which reads from cookies
  if (!user && supabaseCookies.length > 0) {
    console.log("[updateSession] getUser() failed but cookies exist, trying getSession()...");
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        console.log("[updateSession] getSession() fallback successful:", session.user.email);
        user = session.user;
      }
    } catch (sessionError) {
      console.error("[updateSession] getSession() fallback failed:", sessionError);
    }
  }

  console.log("[updateSession] Final result - user:", user?.email || "none", "id:", user?.id || "none");

  return { supabaseResponse, user, supabase };
}
