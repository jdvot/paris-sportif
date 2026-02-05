"use client";

import { useEffect, useState, useCallback } from "react";
import { User, AuthChangeEvent, Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import type { UserProfile, UserRole } from "@/lib/supabase/types";

interface AuthState {
  user: User | null;
  profile: UserProfile | null;
  role: UserRole;
  loading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    profile: null,
    role: "free",
    loading: true,
    error: null,
  });

  const supabase = createClient();

  const fetchProfile = useCallback(
    async (userId: string): Promise<UserProfile | null> => {
      try {
        // Add timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        const { data, error } = await supabase
          .from("user_profiles")
          .select("*")
          .eq("id", userId)
          .single()
          .abortSignal(controller.signal);

        clearTimeout(timeoutId);

        if (error) {
          // Don't log AbortError as it's expected on timeout
          if (error.message && !error.message.includes('AbortError')) {
            console.error("Error fetching profile:", error);
          }
          return null;
        }
        return data as UserProfile;
      } catch (err) {
        // Silently handle AbortError
        const error = err as { name?: string };
        if (error?.name !== 'AbortError') {
          console.error("Error fetching profile:", err);
        }
        return null;
      }
    },
    [supabase]
  );

  useEffect(() => {
    let isMounted = true;

    // Parse session from cookies (fallback when getSession hangs)
    const parseSessionFromCookies = (): { user: User } | null => {
      if (typeof document === 'undefined') return null;

      try {
        const cookies = document.cookie.split(';').reduce((acc, cookie) => {
          const [name, value] = cookie.trim().split('=');
          if (name) acc[name] = value;
          return acc;
        }, {} as Record<string, string>);

        // Find Supabase auth token chunks
        const authTokenChunks: { index: number; value: string }[] = [];

        for (const [name, value] of Object.entries(cookies)) {
          const chunkMatch = name.match(/^sb-[^-]+-auth-token\.(\d+)$/);
          const singleMatch = name.match(/^sb-[^-]+-auth-token$/);

          if (chunkMatch) {
            authTokenChunks.push({ index: parseInt(chunkMatch[1], 10), value });
          } else if (singleMatch && !authTokenChunks.length) {
            authTokenChunks.push({ index: 0, value });
          }
        }

        if (authTokenChunks.length === 0) return null;

        authTokenChunks.sort((a, b) => a.index - b.index);
        const encodedSession = authTokenChunks.map(c => c.value).join('');

        let sessionJson: string;
        if (encodedSession.startsWith('base64-')) {
          const base64 = encodedSession.slice(7);
          const base64Standard = base64.replace(/-/g, '+').replace(/_/g, '/');
          sessionJson = atob(base64Standard);
        } else {
          sessionJson = decodeURIComponent(encodedSession);
        }

        const session = JSON.parse(sessionJson);
        if (!session.user) return null;

        console.log('[useAuth] Cookie fallback successful:', session.user?.email);
        return { user: session.user as User };
      } catch (err) {
        console.error('[useAuth] Cookie parse failed:', err);
        return null;
      }
    };

    const initAuth = async () => {
      try {
        // Use getSession first (faster, reads from cookies)
        const timeoutPromise = new Promise<{ data: { session: null }; timedOut: true }>((resolve) => {
          setTimeout(() => resolve({ data: { session: null }, timedOut: true }), 2000);
        });

        const sessionResult = await Promise.race([
          supabase.auth.getSession().then((r: { data: { session: Session | null } }) => ({ ...r, timedOut: false })),
          timeoutPromise,
        ]) as { data: { session: Session | null }; timedOut: boolean };

        if (!isMounted) return;

        let user: User | null = sessionResult.data.session?.user || null;

        // If getSession timed out or no session, try cookie fallback
        if (!user && sessionResult.timedOut) {
          console.log('[useAuth] getSession timed out, trying cookie fallback...');
          const cookieSession = parseSessionFromCookies();
          if (cookieSession) {
            user = cookieSession.user;
          }
        }

        if (user) {
          const profile = await fetchProfile(user.id);
          if (!isMounted) return;
          setState({
            user,
            profile,
            role: profile?.role || "free",
            loading: false,
            error: null,
          });
        } else {
          setState({
            user: null,
            profile: null,
            role: "free",
            loading: false,
            error: null,
          });
        }
      } catch {
        if (!isMounted) return;
        setState((prev) => ({
          ...prev,
          loading: false,
          error: "Failed to initialize auth",
        }));
      }
    };

    initAuth();

    // Listen for auth changes - only for profile updates
    // Token management is handled centrally by Providers
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event: AuthChangeEvent, session: Session | null) => {
      if (!isMounted) return;

      if (event === "SIGNED_IN" && session?.user) {
        // Fetch profile for the new user
        const profile = await fetchProfile(session.user.id);
        if (!isMounted) return;
        setState({
          user: session.user,
          profile,
          role: profile?.role || "free",
          loading: false,
          error: null,
        });
      } else if (event === "SIGNED_OUT") {
        setState({
          user: null,
          profile: null,
          role: "free",
          loading: false,
          error: null,
        });
      } else if (event === "TOKEN_REFRESHED" && session?.user) {
        // Token refreshed - update user object but profile likely unchanged
        setState((prev) => ({
          ...prev,
          user: session.user,
        }));
      }
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, [supabase, fetchProfile]);

  const signIn = async (email: string, password: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) {
      setState((prev) => ({ ...prev, loading: false, error: error.message }));
      return { error };
    }
    return { error: null };
  };

  const signUp = async (email: string, password: string, fullName?: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
        },
      },
    });
    if (error) {
      setState((prev) => ({ ...prev, loading: false, error: error.message }));
      return { error };
    }
    setState((prev) => ({ ...prev, loading: false }));
    return { error: null };
  };

  const signOut = async () => {
    setState((prev) => ({ ...prev, loading: true }));
    await supabase.auth.signOut();
    setState({
      user: null,
      profile: null,
      role: "free",
      loading: false,
      error: null,
    });
  };

  const signInWithGoogle = async (nextUrl?: string) => {
    // Get the ?next= param from URL or use default
    const next = nextUrl || new URLSearchParams(window.location.search).get("next") || "/picks";
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
      },
    });
    return { error };
  };

  const signInWithGithub = async (nextUrl?: string) => {
    const next = nextUrl || new URLSearchParams(window.location.search).get("next") || "/picks";
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
      },
    });
    return { error };
  };

  const resetPassword = async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`,
    });
    return { error };
  };

  const deleteAccount = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    // First, delete user profile data
    if (state.user?.id) {
      const { error: profileError } = await supabase
        .from("user_profiles")
        .delete()
        .eq("id", state.user.id);

      if (profileError) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: "Failed to delete profile data"
        }));
        return { error: profileError };
      }
    }

    // Sign out the user (actual account deletion requires admin API or edge function)
    // For now, we clear local data and sign out
    await supabase.auth.signOut();

    setState({
      user: null,
      profile: null,
      role: "free",
      loading: false,
      error: null,
    });

    return { error: null };
  };

  const refreshProfile = useCallback(async () => {
    if (!state.user?.id) return;

    const profile = await fetchProfile(state.user.id);
    setState((prev) => ({
      ...prev,
      profile,
      role: profile?.role || prev.role,
    }));
  }, [state.user?.id, fetchProfile]);

  return {
    ...state,
    signIn,
    signUp,
    signOut,
    signInWithGoogle,
    signInWithGithub,
    resetPassword,
    deleteAccount,
    refreshProfile,
    isAuthenticated: !!state.user,
    isPremium: state.role === "premium" || state.role === "admin",
    isAdmin: state.role === "admin",
  };
}
