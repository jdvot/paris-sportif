import { createBrowserClient } from "@supabase/ssr";

/**
 * Singleton pattern for Supabase browser client
 *
 * IMPORTANT: In React/Next.js, creating multiple Supabase client instances
 * can cause issues with auth state management. Using a singleton ensures:
 * 1. Consistent auth state across all components
 * 2. onAuthStateChange listeners work correctly
 * 3. No race conditions between different client instances
 */
let supabaseClient: ReturnType<typeof createBrowserClient> | null = null;

export function createClient() {
  if (supabaseClient) {
    return supabaseClient;
  }

  supabaseClient = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  return supabaseClient;
}
