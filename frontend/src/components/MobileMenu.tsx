"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Calendar,
  CircleDot,
  Dribbble,
  Goal,
  Menu,
  Target,
  Trophy,
  Wallet,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetDescription,
} from "@/components/ui/sheet";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { AuthButton } from "./AuthButton";
import { SearchBar } from "./SearchBar";
import { useState } from "react";

const menuItems = [
  { href: "/", labelKey: "home", icon: Goal },
  { href: "/picks", labelKey: "picks", icon: BarChart3 },
  { href: "/bets", labelKey: "bets", icon: Wallet },
  { href: "/matches", labelKey: "matches", icon: Calendar },
  { href: "/calibration", labelKey: "calibration", icon: Target },
  { href: "/standings", labelKey: "standings", icon: Trophy },
  { href: "/tennis", labelKey: "tennis", icon: CircleDot },
  { href: "/basketball", labelKey: "basketball", icon: Dribbble },
];

export function MobileMenu() {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          className="flex flex-col items-center gap-0.5 px-3 py-1 flex-1 text-gray-500 dark:text-dark-400"
          aria-label={t("more")}
        >
          <Menu className="w-5 h-5" />
          <span className="text-xs">{t("more")}</span>
        </button>
      </SheetTrigger>
      <SheetContent
        side="right"
        className="w-[300px] bg-white dark:bg-dark-900 border-gray-200 dark:border-dark-700 p-0 overflow-y-auto"
      >
        <SheetHeader className="px-6 pt-6 pb-4 border-b border-gray-200 dark:border-dark-700">
          <SheetTitle className="text-gray-900 dark:text-white">WinRate AI</SheetTitle>
          <SheetDescription className="sr-only">
            Navigation menu
          </SheetDescription>
        </SheetHeader>

        {/* Search (visible in mobile menu) */}
        <div className="px-4 py-3 border-b border-gray-200 dark:border-dark-700">
          <SearchBar variant="mobile" />
        </div>

        {/* Navigation links */}
        <nav className="py-2" aria-label="Mobile navigation">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-6 py-3 text-sm transition-colors",
                  isActive
                    ? "bg-primary-500/10 text-primary-600 dark:text-primary-400 font-medium"
                    : "text-gray-700 dark:text-dark-300 hover:bg-gray-100 dark:hover:bg-dark-800"
                )}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span>{t(item.labelKey)}</span>
              </Link>
            );
          })}
        </nav>

        {/* Settings section */}
        <div className="border-t border-gray-200 dark:border-dark-700 px-6 py-4">
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <LanguageSwitcher />
          </div>
        </div>

        {/* Auth section */}
        <div className="border-t border-gray-200 dark:border-dark-700 px-6 py-4">
          <AuthButton />
        </div>
      </SheetContent>
    </Sheet>
  );
}
