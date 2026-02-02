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

    // Use getUser() instead of getSession() - it validates with the server
    // and properly handles cookies that were just set (e.g., after OAuth)
    const { data: userData, error: userError } = await supabase.auth.getUser();

    if (userError) {
      console.log("[Auth] getUser error:", userError.message);
      return null;
    }

    if (userData.user) {
      // User is authenticated, get the session for the token
      const { data: sessionData } = await supabase.auth.getSession();
      if (sessionData.session?.access_token) {
        console.log("[Auth] Token found for user:", userData.user.email);
        return sessionData.session.access_token;
      }

      // Session not in cache yet, try refresh
      const { data: refreshData } = await supabase.auth.refreshSession();
      if (refreshData.session?.access_token) {
        console.log("[Auth] Token found after refresh");
        return refreshData.session.access_token;
      }
    }

    console.log("[Auth] No authenticated user");
    return null;
  } catch (err) {
    console.error("[Auth] Error getting token:", err);
    return null;
  }
}
