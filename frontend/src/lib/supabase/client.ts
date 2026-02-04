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

// Validate required environment variables
function validateEnvVars(): { url: string; anonKey: string } {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    const missing = [];
    if (!url) missing.push("NEXT_PUBLIC_SUPABASE_URL");
    if (!anonKey) missing.push("NEXT_PUBLIC_SUPABASE_ANON_KEY");
    throw new Error(
      `Missing required Supabase environment variables: ${missing.join(", ")}. ` +
      `Please check your .env.local file.`
    );
  }

  return { url, anonKey };
}

export function createClient() {
  if (supabaseClient) {
    return supabaseClient;
  }

  const { url, anonKey } = validateEnvVars();

  supabaseClient = createBrowserClient(url, anonKey);

  return supabaseClient;
}
