import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  const supabaseCookies = request.cookies.getAll().filter((c) => c.name.startsWith("sb-"));

  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY");
  }

  const supabase = createServerClient(
    supabaseUrl,
    supabaseAnonKey,
    {
      cookies: {
        getAll() {
          const cookies = request.cookies.getAll();
          return cookies;
        },
        setAll(cookiesToSet) {
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

  // Add timeout to prevent middleware hanging if Supabase is slow
  const timeoutPromise = new Promise<{ data: { user: null }; error: { message: string }; timedOut: true }>((resolve) => {
    setTimeout(() => resolve({ data: { user: null }, error: { message: 'Timeout' }, timedOut: true }), 3000);
  });

  const result = await Promise.race([
    supabase.auth.getUser().then(r => ({ ...r, timedOut: false })),
    timeoutPromise,
  ]) as { data: { user: import('@supabase/supabase-js').User | null }; error?: { message: string } | null; timedOut: boolean };

  let user = result.data.user;

  // On timeout or error, fallback to getSession() which reads from cookies
  if (!user && supabaseCookies.length > 0) {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        user = session.user;
      }
    } catch {
      // getSession() fallback failed, proceed without user
    }
  }

  return { supabaseResponse, user, supabase };
}
