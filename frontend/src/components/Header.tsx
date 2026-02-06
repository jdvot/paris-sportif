"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Goal, BarChart3, Calendar, Trophy, Wallet, Target } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { AuthButton } from "./AuthButton";
import { Logo } from "./Logo";
import { useUserPreferences } from "@/lib/hooks/useUserPreferences";

const navItemsConfig = [
  { href: "/", labelKey: "home", icon: Goal },
  { href: "/picks", labelKey: "picks", icon: BarChart3 },
  { href: "/bets", labelKey: "bets", icon: Wallet },
  { href: "/calibration", labelKey: "calibration", icon: Target },
  { href: "/matches", labelKey: "matches", icon: Calendar },
  { href: "/standings", labelKey: "standings", icon: Trophy },
];

export function Header() {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const tHeader = useTranslations("components.header");
  const { data: preferences } = useUserPreferences({ enabled: true });
  const favoriteTeam = preferences?.favorite_team;

  const navItems = navItemsConfig.map(item => ({
    ...item,
    label: t(item.labelKey),
  }));

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-dark-900/80 backdrop-blur-lg border-b border-gray-200 dark:border-dark-700">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-14 sm:h-16">
          {/* Logo - Show favorite team logo + site name, or default logo */}
          <Link href="/" className="flex items-center gap-2 flex-shrink-0">
            {favoriteTeam?.logo_url ? (
              <div className="flex items-center gap-2">
                <Image
                  src={favoriteTeam.logo_url}
                  alt={favoriteTeam.name}
                  width={32}
                  height={32}
                  className="w-8 h-8 object-contain"
                />
                <span className="font-bold text-xl text-gray-900 dark:text-white hidden sm:inline">
                  WinRate AI
                </span>
              </div>
            ) : (
              <Logo size="md" showText />
            )}
          </Link>

          {/* Navigation */}
          <nav aria-label="Navigation" className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg transition-colors text-sm",
                    isActive
                      ? "bg-primary-500/20 text-primary-600 dark:text-primary-400"
                      : "text-gray-600 dark:text-dark-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-800"
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Status Badge, Theme Toggle, Language & Auth */}
          <div className="flex items-center gap-2 sm:gap-3">
            <ThemeToggle />
            <LanguageSwitcher />
            <div className="hidden sm:flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-gray-100 dark:bg-dark-800 rounded-full flex-shrink-0">
              <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 bg-primary-500 rounded-full animate-pulse" />
              <span className="text-xs text-gray-600 dark:text-dark-300">{tHeader("live")}</span>
            </div>
            <AuthButton />
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      <nav aria-label="Navigation principale" className="md:hidden flex items-center justify-around py-2 border-t border-gray-200 dark:border-dark-700">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex flex-col items-center gap-0.5 sm:gap-1 px-3 sm:px-4 py-1 flex-1",
                isActive ? "text-primary-600 dark:text-primary-400" : "text-gray-500 dark:text-dark-400"
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
