/**
 * Custom fetch instance for Orval-generated API hooks
 * Handles API requests with proper base URL, error handling, and authentication
 *
 * Orval generates calls like: customInstance<T>(url, { method: 'GET', signal })
 * So we support both (url, options) and (config) formats
 */

// In browser: use relative URLs to leverage Next.js rewrites
// On server: use full API URL for direct access
const API_BASE_URL = typeof window !== 'undefined'
  ? ''
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

/**
 * Get auth token from Supabase session (browser only)
 */
async function getAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null; // Server-side, no token
  }

  try {
    // Dynamic import to avoid SSR issues
    const { createClient } = await import("@/lib/supabase/client");
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token || null;
  } catch {
    return null;
  }
}

/**
 * Custom instance for Orval - handles fetch requests
 *
 * @param urlOrConfig - Either a URL string or a config object
 * @param options - Optional RequestInit when first param is URL
 */
export const customInstance = async <T>(
  urlOrConfig: string | { url: string; method?: string; headers?: Record<string, string>; params?: Record<string, unknown>; data?: unknown; signal?: AbortSignal },
  options?: RequestInit & { params?: Record<string, unknown>; data?: unknown },
): Promise<T> => {
  // Determine if first arg is URL string or config object
  const isUrlString = typeof urlOrConfig === 'string';

  const url = isUrlString ? urlOrConfig : urlOrConfig.url;
  const method = isUrlString ? (options?.method || 'GET') : (urlOrConfig.method || 'GET');
  const headers = isUrlString ? options?.headers : urlOrConfig.headers;
  const params = isUrlString ? options?.params : urlOrConfig.params;
  const data = isUrlString ? options?.data : urlOrConfig.data;
  const signal = isUrlString ? options?.signal : urlOrConfig.signal;

  let fullUrl = `${API_BASE_URL}${url}`;

  // Build query parameters from params object
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      fullUrl += (fullUrl.includes('?') ? '&' : '?') + queryString;
    }
  }

  // Get auth token
  const token = await getAuthToken();

  const response = await fetch(fullUrl, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...headers,
    },
    body: data ? JSON.stringify(data) : undefined,
    signal,
  });

  if (!response.ok) {
    // Handle auth errors specifically
    if (response.status === 401) {
      throw new Error("Authentification requise. Veuillez vous connecter.");
    }
    if (response.status === 403) {
      throw new Error("Acces refuse. Abonnement premium requis.");
    }

    let errorMessage = `API Error: ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      // Use default error message
    }
    throw new Error(errorMessage);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {
      data: {},
      status: response.status,
    } as T;
  }

  try {
    const jsonData = JSON.parse(text);
    // Wrap in Orval expected format
    return {
      data: jsonData,
      status: response.status,
    } as T;
  } catch {
    throw new Error(`Invalid JSON response from ${url}`);
  }
};

export default customInstance;
