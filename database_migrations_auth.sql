-- ============================================================================
-- Paris Sportif - Authentication System Database Migrations
-- ============================================================================
-- Description: SQL migrations for Supabase authentication system
-- Created: 2026-02-02
-- Related Epic: Système d'Authentification
-- ============================================================================

-- ============================================================================
-- Migration 001: Create user_profiles table
-- ============================================================================
-- Ticket: [feat] Page profil utilisateur avec upload avatar et gestion compte
-- Purpose: Store additional user profile information beyond auth.users

BEGIN;

-- Create user_profiles table
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    favorite_team TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Add comments for documentation
COMMENT ON TABLE public.user_profiles IS 'User profile information complementing auth.users';
COMMENT ON COLUMN public.user_profiles.id IS 'References auth.users.id';
COMMENT ON COLUMN public.user_profiles.username IS 'Unique username chosen by user';
COMMENT ON COLUMN public.user_profiles.full_name IS 'Full display name';
COMMENT ON COLUMN public.user_profiles.avatar_url IS 'URL to avatar in Supabase Storage';
COMMENT ON COLUMN public.user_profiles.bio IS 'User biography (max 500 chars)';
COMMENT ON COLUMN public.user_profiles.favorite_team IS 'Favorite football team';

-- Add constraints
ALTER TABLE public.user_profiles
    ADD CONSTRAINT username_min_length CHECK (char_length(username) >= 3),
    ADD CONSTRAINT username_max_length CHECK (char_length(username) <= 30),
    ADD CONSTRAINT bio_max_length CHECK (char_length(bio) <= 500);

-- Create indexes for performance
CREATE INDEX idx_user_profiles_username ON public.user_profiles(username);
CREATE INDEX idx_user_profiles_created_at ON public.user_profiles(created_at DESC);

COMMIT;

-- ============================================================================
-- Migration 002: Enable Row Level Security (RLS)
-- ============================================================================
-- Ticket: [feat] Page profil utilisateur avec upload avatar et gestion compte
-- Purpose: Ensure users can only access/modify their own profile

BEGIN;

-- Enable RLS on user_profiles
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own profile
CREATE POLICY "Users can view their own profile"
    ON public.user_profiles
    FOR SELECT
    USING (auth.uid() = id);

-- Policy: Users can insert their own profile
CREATE POLICY "Users can insert their own profile"
    ON public.user_profiles
    FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Policy: Users can update their own profile
CREATE POLICY "Users can update their own profile"
    ON public.user_profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Policy: Users can delete their own profile (soft delete recommended)
CREATE POLICY "Users can delete their own profile"
    ON public.user_profiles
    FOR DELETE
    USING (auth.uid() = id);

-- Optional: Public profiles (view-only for other users)
-- Uncomment if you want profiles to be publicly viewable
-- CREATE POLICY "Profiles are publicly viewable"
--     ON public.user_profiles
--     FOR SELECT
--     USING (true);

COMMIT;

-- ============================================================================
-- Migration 003: Auto-create profile on user signup
-- ============================================================================
-- Ticket: [feat] Page profil utilisateur avec upload avatar et gestion compte
-- Purpose: Automatically create user_profiles entry when new user signs up

BEGIN;

-- Function to handle new user creation
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.user_profiles (id, username, full_name, avatar_url)
    VALUES (
        new.id,
        -- Use email prefix as default username (before @)
        split_part(new.email, '@', 1),
        -- Get full_name from metadata if provided during signup
        COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        -- Get avatar_url from OAuth provider if available
        COALESCE(new.raw_user_meta_data->>'avatar_url', null)
    );
    RETURN new;
END;
$$;

-- Trigger to auto-create profile
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Add comment
COMMENT ON FUNCTION public.handle_new_user() IS 'Auto-creates user_profiles entry when new user signs up';

COMMIT;

-- ============================================================================
-- Migration 004: Update updated_at timestamp automatically
-- ============================================================================
-- Ticket: [feat] Page profil utilisateur avec upload avatar et gestion compte
-- Purpose: Auto-update updated_at column when profile is modified

BEGIN;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Trigger to update timestamp on profile updates
DROP TRIGGER IF EXISTS on_user_profile_updated ON public.user_profiles;
CREATE TRIGGER on_user_profile_updated
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

COMMIT;

-- ============================================================================
-- Migration 005: Create Storage bucket for avatars
-- ============================================================================
-- Ticket: [feat] Page profil utilisateur avec upload avatar et gestion compte
-- Purpose: Setup Supabase Storage bucket for user avatars

BEGIN;

-- Insert bucket (Supabase Storage)
-- Note: This must be run in Supabase Dashboard SQL Editor or via Supabase CLI
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true)
ON CONFLICT (id) DO NOTHING;

COMMIT;

-- ============================================================================
-- Migration 006: Storage policies for avatars
-- ============================================================================
-- Ticket: [feat] Page profil utilisateur avec upload avatar et gestion compte
-- Purpose: Allow users to upload/update/delete their own avatars

BEGIN;

-- Policy: Anyone can view avatars (public bucket)
CREATE POLICY "Avatars are publicly accessible"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'avatars');

-- Policy: Users can upload their own avatar
CREATE POLICY "Users can upload their own avatar"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'avatars' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Policy: Users can update their own avatar
CREATE POLICY "Users can update their own avatar"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'avatars' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Policy: Users can delete their own avatar
CREATE POLICY "Users can delete their own avatar"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'avatars' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

COMMIT;

-- ============================================================================
-- Migration 007: Create helper functions
-- ============================================================================
-- Ticket: [feat] Page profil utilisateur avec upload avatar et gestion compte
-- Purpose: Utility functions for profile management

BEGIN;

-- Function to get profile by user ID
CREATE OR REPLACE FUNCTION public.get_profile(user_id UUID)
RETURNS TABLE (
    id UUID,
    username TEXT,
    full_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    favorite_team TEXT,
    email TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT
        p.id,
        p.username,
        p.full_name,
        p.avatar_url,
        p.bio,
        p.favorite_team,
        u.email,
        p.created_at,
        p.updated_at
    FROM public.user_profiles p
    JOIN auth.users u ON u.id = p.id
    WHERE p.id = user_id;
$$;

-- Function to check if username is available
CREATE OR REPLACE FUNCTION public.is_username_available(check_username TEXT)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT NOT EXISTS (
        SELECT 1 FROM public.user_profiles
        WHERE username = check_username
    );
$$;

COMMIT;

-- ============================================================================
-- Migration 008: Create user_sessions table (optional - for advanced tracking)
-- ============================================================================
-- Ticket: [feat] Backend FastAPI Auth
-- Purpose: Track user sessions for audit logs and security

BEGIN;

CREATE TABLE IF NOT EXISTS public.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    login_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    logout_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true NOT NULL
);

-- Indexes
CREATE INDEX idx_user_sessions_user_id ON public.user_sessions(user_id);
CREATE INDEX idx_user_sessions_login_at ON public.user_sessions(login_at DESC);
CREATE INDEX idx_user_sessions_is_active ON public.user_sessions(is_active) WHERE is_active = true;

-- RLS
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own sessions"
    ON public.user_sessions
    FOR SELECT
    USING (auth.uid() = user_id);

COMMIT;

-- ============================================================================
-- Migration 009: Add OAuth provider tracking
-- ============================================================================
-- Ticket: [feat] OAuth Google/GitHub
-- Purpose: Track which OAuth provider user signed up with

BEGIN;

-- Add column to user_profiles
ALTER TABLE public.user_profiles
    ADD COLUMN IF NOT EXISTS auth_provider TEXT DEFAULT 'email',
    ADD COLUMN IF NOT EXISTS oauth_provider_id TEXT;

-- Add check constraint
ALTER TABLE public.user_profiles
    ADD CONSTRAINT valid_auth_provider
    CHECK (auth_provider IN ('email', 'google', 'github', 'apple', 'microsoft'));

-- Update existing users to 'email' provider
UPDATE public.user_profiles
SET auth_provider = 'email'
WHERE auth_provider IS NULL;

-- Update handle_new_user function to capture OAuth provider
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    provider TEXT;
BEGIN
    -- Determine auth provider from Supabase metadata
    provider := COALESCE(
        new.raw_app_meta_data->>'provider',
        'email'
    );

    INSERT INTO public.user_profiles (
        id,
        username,
        full_name,
        avatar_url,
        auth_provider,
        oauth_provider_id
    )
    VALUES (
        new.id,
        split_part(new.email, '@', 1),
        COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        COALESCE(new.raw_user_meta_data->>'avatar_url', null),
        provider,
        CASE
            WHEN provider != 'email' THEN new.raw_user_meta_data->>'provider_id'
            ELSE NULL
        END
    );
    RETURN new;
END;
$$;

COMMIT;

-- ============================================================================
-- Migration 010: Sample data for testing (DEV ONLY)
-- ============================================================================
-- WARNING: Only run this in development/staging environments!
-- DO NOT run in production

-- Uncomment to create test users
/*
BEGIN;

-- Insert test user profiles (requires users to exist in auth.users first)
INSERT INTO public.user_profiles (id, username, full_name, bio, favorite_team)
VALUES
    ('00000000-0000-0000-0000-000000000001'::uuid, 'john_doe', 'John Doe', 'Football enthusiast', 'Manchester United'),
    ('00000000-0000-0000-0000-000000000002'::uuid, 'jane_smith', 'Jane Smith', 'Stats lover', 'FC Barcelona')
ON CONFLICT (id) DO NOTHING;

COMMIT;
*/

-- ============================================================================
-- Rollback Scripts (use in case of issues)
-- ============================================================================

-- Rollback Migration 001-009
/*
BEGIN;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS on_user_profile_updated ON public.user_profiles;
DROP FUNCTION IF EXISTS public.handle_new_user();
DROP FUNCTION IF EXISTS public.handle_updated_at();
DROP FUNCTION IF EXISTS public.get_profile(UUID);
DROP FUNCTION IF EXISTS public.is_username_available(TEXT);

DROP TABLE IF EXISTS public.user_sessions CASCADE;
DROP TABLE IF EXISTS public.user_profiles CASCADE;

-- Note: Storage bucket and policies must be deleted via Supabase Dashboard

COMMIT;
*/

-- ============================================================================
-- Verification Queries (run after migrations)
-- ============================================================================

-- Check if user_profiles table exists and has correct columns
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'user_profiles'
ORDER BY ordinal_position;

-- Check RLS policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename = 'user_profiles';

-- Check triggers
SELECT
    trigger_name,
    event_manipulation,
    event_object_table,
    action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'public'
  AND event_object_table IN ('user_profiles')
ORDER BY event_object_table, trigger_name;

-- Check storage bucket
SELECT * FROM storage.buckets WHERE id = 'avatars';

-- Check storage policies
SELECT
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects';

-- ============================================================================
-- Performance Optimization (run after initial setup)
-- ============================================================================

-- Analyze tables for query planner
ANALYZE public.user_profiles;
ANALYZE public.user_sessions;

-- Vacuum tables to reclaim space
VACUUM ANALYZE public.user_profiles;

-- ============================================================================
-- Security Checklist
-- ============================================================================
-- [ ] RLS enabled on all tables
-- [ ] Policies prevent users from accessing other users' data
-- [ ] Functions use SECURITY DEFINER only when necessary
-- [ ] Storage policies restrict access to user's own files
-- [ ] No sensitive data (passwords) stored in user_profiles
-- [ ] Indexes created for frequently queried columns
-- [ ] Triggers tested with sample data
-- [ ] Migration tested in staging before production

-- ============================================================================
-- End of migrations
-- ============================================================================

-- For questions or issues, contact: [Tech Lead]
-- Documentation: /docs/AUTHENTICATION.md
