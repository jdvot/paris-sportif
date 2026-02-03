/**
 * Custom fetch instance for Orval-generated API hooks
 * Handles API requests with proper base URL, error handling, and authentication
 */

import { getSupabaseToken } from "./auth-helper";

/**
 * Custom API Error class with HTTP status code
 * Used for detecting auth errors in React Query global error handler
 */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// In browser: use relative URLs to leverage Next.js rewrites
// On server: use full API URL for direct access
const API_BASE_URL = typeof window !== 'undefined'
  ? ''
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

/**
 * Custom instance for Orval - handles fetch requests
 */
export const customInstance = async <T>(
  url: string,
  options?: RequestInit & { params?: Record<string, unknown>; data?: unknown },
): Promise<T> => {
  let fullUrl = `${API_BASE_URL}${url}`;

  // Build query parameters
  if (options?.params) {
    const searchParams = new URLSearchParams();
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      fullUrl += (fullUrl.includes('?') ? '&' : '?') + queryString;
    }
  }

  // Get auth token from Supabase
  const token = await getSupabaseToken();

  // Debug: log auth status for API requests
  if (typeof window !== 'undefined') {
    console.log('[API]', url, 'token:', token ? 'present' : 'MISSING');
  }

  let response: Response;
  try {
    response = await fetch(fullUrl, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options?.headers,
      },
      body: options?.data ? JSON.stringify(options.data) : options?.body,
    });
  } catch (error) {
    // Re-throw AbortError as-is (React Query uses this for cancellation)
    if (error instanceof Error && error.name === 'AbortError') {
      throw error;
    }
    // Network error
    throw new ApiError("Erreur réseau. Vérifiez votre connexion.", 0);
  }

  if (!response.ok) {
    if (response.status === 401) {
      throw new ApiError("Authentification requise. Veuillez vous connecter.", 401);
    }
    if (response.status === 403) {
      throw new ApiError("Accès refusé. Abonnement premium requis.", 403);
    }

    let errorMessage = `API Error: ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      // Use default
    }
    throw new ApiError(errorMessage, response.status);
  }

  const text = await response.text();
  if (!text) {
    return { data: {}, status: response.status } as T;
  }

  try {
    const jsonData = JSON.parse(text);
    return { data: jsonData, status: response.status } as T;
  } catch {
    throw new Error(`Invalid JSON response from ${url}`);
  }
};

export default customInstance;
