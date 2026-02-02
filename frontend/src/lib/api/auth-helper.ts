/**
 * Auth helper for getting Supabase token
 * Separated from custom-instance.ts to allow Orval to parse the mutator file
 */

// Cache the supabase client to avoid recreating it
let supabaseClient: ReturnType<typeof import("../supabase/client").createClient> | null = null;

async function getSupabaseClient() {
  if (!supabaseClient) {
    const { createClient } = await import("../supabase/client");
    supabaseClient = createClient();
  }
  return supabaseClient;
}

/**
 * Get auth token from Supabase session (browser only)
 * Uses dynamic import to avoid SSR issues
 *
 * IMPORTANT: This function uses getSession() which reads from local cache.
 * It does NOT make network calls, so it won't be affected by AbortSignal.
 * The session is kept fresh by onAuthStateChange listener in the app.
 */
export async function getSupabaseToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null; // Server-side, no token
  }

  try {
    const supabase = await getSupabaseClient();

    // Use getSession() - reads from local storage/cache, no network call
    // This is fast and won't be affected by AbortSignal from React Query
    const { data: sessionData } = await supabase.auth.getSession();

    if (sessionData.session?.access_token) {
      return sessionData.session.access_token;
    }

    // No session in cache - user is not authenticated
    return null;
  } catch (err) {
    // Re-throw AbortError so React Query can handle cancellation properly
    if (err instanceof Error && err.name === 'AbortError') {
      throw err;
    }
    console.error("[Auth] Error getting token:", err);
    return null;
  }
}
