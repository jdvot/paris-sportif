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
 */
export async function getSupabaseToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null; // Server-side, no token
  }

  try {
    const supabase = await getSupabaseClient();

    // First try getSession (faster, uses cached session)
    const { data: sessionData } = await supabase.auth.getSession();
    if (sessionData.session?.access_token) {
      console.log("[Auth] Token found from session");
      return sessionData.session.access_token;
    }

    // If no session, try refreshing (handles edge cases after OAuth)
    const { data: refreshData, error } = await supabase.auth.refreshSession();
    if (!error && refreshData.session?.access_token) {
      console.log("[Auth] Token found after refresh");
      return refreshData.session.access_token;
    }

    console.log("[Auth] No token available");
    return null;
  } catch (err) {
    console.error("[Auth] Error getting token:", err);
    return null;
  }
}
