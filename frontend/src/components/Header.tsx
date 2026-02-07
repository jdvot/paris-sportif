"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Goal,
  BarChart3,
  Calendar,
  Trophy,
  Wallet,
  Target,
  CircleDot,
  Dribbble,
  ChevronDown,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { AuthButton } from "./AuthButton";
import { Logo } from "./Logo";
import { SearchBar } from "./SearchBar";
import { MobileMenu } from "./MobileMenu";
import { useUserPreferences } from "@/lib/hooks/useUserPreferences";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const mainNavItems = [
  { href: "/", labelKey: "home", icon: Goal },
  { href: "/picks", labelKey: "picks", icon: BarChart3 },
  { href: "/bets", labelKey: "bets", icon: Wallet },
  { href: "/matches", labelKey: "matches", icon: Calendar },
  { href: "/calibration", labelKey: "calibration", icon: Target },
];

const sportsItems = [
  { href: "/standings", labelKey: "standings", icon: Trophy },
  { href: "/tennis", labelKey: "tennis", icon: CircleDot },
  { href: "/basketball", labelKey: "basketball", icon: Dribbble },
];

const mobileNavItems = [
  { href: "/", labelKey: "home", icon: Goal },
  { href: "/picks", labelKey: "picks", icon: BarChart3 },
  { href: "/matches", labelKey: "matches", icon: Calendar },
  { href: "/standings", labelKey: "standings", icon: Trophy },
];

export function Header() {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const { data: preferences } = useUserPreferences({ enabled: true });
  const favoriteTeam = preferences?.favorite_team;

  const isSportsActive = sportsItems.some((item) => pathname === item.href);

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-dark-900/80 backdrop-blur-lg border-b border-gray-200 dark:border-dark-700">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-14 sm:h-16">
          {/* Logo */}
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

          {/* Desktop Navigation */}
          <nav aria-label="Navigation" className="hidden md:flex items-center gap-1">
            {mainNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm",
                    isActive
                      ? "bg-primary-500/20 text-primary-600 dark:text-primary-400"
                      : "text-gray-600 dark:text-dark-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-800"
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{t(item.labelKey)}</span>
                </Link>
              );
            })}

            {/* Sports dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  aria-label={t("sports")}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors text-sm",
                    isSportsActive
                      ? "bg-primary-500/20 text-primary-600 dark:text-primary-400"
                      : "text-gray-600 dark:text-dark-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-800"
                  )}
                >
                  <Trophy className="w-4 h-4 flex-shrink-0" />
                  <span>{t("sports")}</span>
                  <ChevronDown className="w-3.5 h-3.5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="start"
                className="w-48 bg-white dark:bg-dark-800 border-gray-200 dark:border-dark-700"
              >
                {sportsItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;

                  return (
                    <DropdownMenuItem key={item.href} asChild>
                      <Link
                        href={item.href}
                        className={cn(
                          "flex items-center gap-2 cursor-pointer",
                          isActive && "text-primary-600 dark:text-primary-400 font-medium"
                        )}
                      >
                        <Icon className="w-4 h-4" />
                        <span>{t(item.labelKey)}</span>
                      </Link>
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          </nav>

          {/* Search, Theme Toggle, Language & Auth */}
          <div className="flex items-center gap-2 sm:gap-3">
            <SearchBar />
            <ThemeToggle />
            <LanguageSwitcher />
            <AuthButton />
          </div>
        </div>
      </div>

      {/* Mobile Bottom Navigation — 5 items */}
      <nav
        aria-label="Navigation principale"
        className="md:hidden flex items-center justify-around py-2 border-t border-gray-200 dark:border-dark-700"
      >
        {mobileNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex flex-col items-center gap-0.5 px-3 py-2 flex-1 min-h-[44px] min-w-[44px] justify-center",
                isActive
                  ? "text-primary-600 dark:text-primary-400"
                  : "text-gray-500 dark:text-dark-400"
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs">{t(item.labelKey)}</span>
            </Link>
          );
        })}

        {/* "More" button — opens Sheet */}
        <MobileMenu />
      </nav>
    </header>
  );
}
