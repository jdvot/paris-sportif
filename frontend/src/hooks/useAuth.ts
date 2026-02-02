"use client";

import { useEffect, useState, useCallback } from "react";
import { User } from "@supabase/supabase-js";
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
    async (userId: string) => {
      const { data, error } = await supabase
        .from("user_profiles")
        .select("*")
        .eq("id", userId)
        .single();

      if (error) {
        console.error("Error fetching profile:", error);
        return null;
      }
      return data as UserProfile;
    },
    [supabase]
  );

  useEffect(() => {
    const initAuth = async () => {
      try {
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (user) {
          const profile = await fetchProfile(user.id);
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
      } catch (err) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: "Failed to initialize auth",
        }));
      }
    };

    initAuth();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === "SIGNED_IN" && session?.user) {
        const profile = await fetchProfile(session.user.id);
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
      }
    });

    return () => {
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

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    return { error };
  };

  const signInWithGithub = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
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

  return {
    ...state,
    signIn,
    signUp,
    signOut,
    signInWithGoogle,
    signInWithGithub,
    resetPassword,
    isAuthenticated: !!state.user,
    isPremium: state.role === "premium" || state.role === "admin",
    isAdmin: state.role === "admin",
  };
}
