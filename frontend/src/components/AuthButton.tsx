"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  User,
  LogOut,
  Settings,
  Crown,
  ChevronDown,
  Shield,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export function AuthButton() {
  const { user, profile, role, loading, signOut, isAuthenticated, isPremium, isAdmin } = useAuth();
  const t = useTranslations("nav");
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    await signOut();
    setIsOpen(false);
    // signOut() handles redirect to /auth/login
  };

  // Loading state
  if (loading) {
    return (
      <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-slate-700 animate-pulse" />
    );
  }

  // Not authenticated - show login button
  if (!isAuthenticated) {
    return (
      <Link
        href="/auth/login"
        className="flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 bg-gradient-to-r from-primary-500 to-emerald-500 hover:from-primary-600 hover:to-emerald-600 text-gray-900 dark:text-white text-sm font-medium rounded-lg transition-all"
      >
        <User className="w-4 h-4" />
        <span className="hidden sm:inline">{t("login")}</span>
      </Link>
    );
  }

  // Authenticated - show user menu
  const displayName = profile?.full_name || user?.email?.split("@")[0] || "User";
  const avatarUrl = profile?.avatar_url;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 px-2 sm:px-3 py-1.5 rounded-lg transition-colors",
          "bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 border border-gray-300 dark:border-slate-600"
        )}
      >
        {/* Avatar */}
        <div className="relative">
          {avatarUrl ? (
            <Image
              src={avatarUrl}
              alt={displayName}
              width={28}
              height={28}
              className="w-7 h-7 rounded-full object-cover"
            />
          ) : (
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary-500 to-emerald-500 flex items-center justify-center">
              <span className="text-gray-900 dark:text-white text-sm font-medium">
                {displayName[0]?.toUpperCase()}
              </span>
            </div>
          )}
          {/* Role badge */}
          {isPremium && (
            <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-gray-100 dark:bg-slate-800 flex items-center justify-center">
              {isAdmin ? (
                <Shield className="w-2.5 h-2.5 text-red-400" />
              ) : (
                <Crown className="w-2.5 h-2.5 text-yellow-400" />
              )}
            </div>
          )}
        </div>

        {/* Name (desktop only) */}
        <span className="hidden sm:block text-sm font-medium text-gray-900 dark:text-white max-w-[100px] truncate">
          {displayName}
        </span>

        <ChevronDown
          className={cn(
            "w-4 h-4 text-gray-600 dark:text-slate-400 transition-transform",
            isOpen && "rotate-180"
          )}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-xl shadow-xl overflow-hidden z-50">
          {/* User Info */}
          <div className="px-4 py-3 border-b border-gray-300 dark:border-slate-600">
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{displayName}</p>
            <p className="text-xs text-gray-600 dark:text-slate-400 truncate">{user?.email}</p>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={cn(
                  "text-xs font-medium px-2 py-0.5 rounded-full",
                  role === "admin"
                    ? "bg-red-500/20 text-red-400"
                    : role === "premium"
                    ? "bg-yellow-500/20 text-yellow-400"
                    : "bg-dark-600 text-gray-700 dark:text-slate-300"
                )}
              >
                {role === "admin" ? "Admin" : role === "premium" ? "Premium" : "Free"}
              </span>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-1">
            <Link
              href="/profile"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors"
            >
              <User className="w-4 h-4" />
              {t("profile")}
            </Link>

            {!isPremium && (
              <Link
                href="/upgrade"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 px-4 py-2.5 text-sm text-yellow-400 hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors"
              >
                <Crown className="w-4 h-4" />
                {t("upgrade")}
              </Link>
            )}

            {isAdmin && (
              <Link
                href="/admin"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors"
              >
                <Shield className="w-4 h-4" />
                {t("admin")}
              </Link>
            )}

            <Link
              href="/settings"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors"
            >
              <Settings className="w-4 h-4" />
              {t("settings")}
            </Link>
          </div>

          {/* Sign Out */}
          <div className="border-t border-gray-300 dark:border-slate-600 py-1">
            <button
              onClick={handleSignOut}
              className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-400 hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              {t("logout")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
