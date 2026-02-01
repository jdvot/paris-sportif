"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";

export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();

  // Avoid hydration mismatch by waiting for client-side mount
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Return a placeholder with the same dimensions to prevent layout shift
    return (
      <button
        className="p-2 rounded-lg bg-gray-100 dark:bg-dark-800 border border-gray-300 dark:border-dark-600"
        aria-label="Toggle theme"
        disabled
      >
        <div className="w-4 h-4 sm:w-5 sm:h-5" />
      </button>
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={cn(
        "p-2 rounded-lg transition-all duration-300",
        "bg-gray-100 hover:bg-gray-200 dark:bg-dark-800 dark:hover:bg-dark-700",
        "border border-gray-300 dark:border-dark-600",
        "text-gray-700 hover:text-gray-900 dark:text-dark-300 dark:hover:text-white",
        "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
        "focus:ring-offset-white dark:focus:ring-offset-dark-900"
      )}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {isDark ? (
        <Sun className="w-4 h-4 sm:w-5 sm:h-5 transition-transform hover:rotate-45" />
      ) : (
        <Moon className="w-4 h-4 sm:w-5 sm:h-5 transition-transform hover:-rotate-12" />
      )}
    </button>
  );
}
