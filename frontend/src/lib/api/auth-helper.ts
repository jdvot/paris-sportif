/**
 * Auth helper for getting Supabase token
 * Separated from custom-instance.ts to allow Orval to parse the mutator file
 */

/**
 * Get auth token from Supabase session (browser only)
 * Uses dynamic import to avoid SSR issues
 */
export async function getSupabaseToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null; // Server-side, no token
  }

  try {
    // Dynamic import to avoid SSR issues with Supabase
    const { createClient } = await import("../supabase/client");
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || null;
  } catch {
    return null;
  }
}
