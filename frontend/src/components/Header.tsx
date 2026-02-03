"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Goal, BarChart3, Calendar, Trophy, Heart, History } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./ThemeToggle";
import { AuthButton } from "./AuthButton";
import { Logo } from "./Logo";

const navItemsConfig = [
  { href: "/", labelKey: "home", icon: Goal },
  { href: "/picks", labelKey: "picks", icon: BarChart3 },
  { href: "/history", labelKey: "history", icon: History },
  { href: "/matches", labelKey: "matches", icon: Calendar },
  { href: "/standings", labelKey: "standings", icon: Trophy },
  { href: "/favorites", labelKey: "favorites", icon: Heart },
];

export function Header() {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const tHeader = useTranslations("components.header");

  const navItems = navItemsConfig.map(item => ({
    ...item,
    label: t(item.labelKey),
  }));

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-dark-900/80 backdrop-blur-lg border-b border-gray-200 dark:border-dark-700">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-14 sm:h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 flex-shrink-0">
            <Logo size="md" showText />
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
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

          {/* Status Badge, Theme Toggle & Auth */}
          <div className="flex items-center gap-2 sm:gap-3">
            <ThemeToggle />
            <div className="hidden sm:flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-gray-100 dark:bg-dark-800 rounded-full flex-shrink-0">
              <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 bg-primary-500 rounded-full animate-pulse" />
              <span className="text-xs text-gray-600 dark:text-dark-300">{tHeader("live")}</span>
            </div>
            <AuthButton />
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      <nav className="md:hidden flex items-center justify-around py-2 border-t border-gray-200 dark:border-dark-700">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
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
