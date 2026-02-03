"use client";

import { useState, useTransition, useRef, useEffect } from "react";
import { useLocale } from "next-intl";
import { Globe, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { locales, localeNames, localeFlags, type Locale } from "@/i18n/config";

export function LanguageSwitcher() {
  const locale = useLocale() as Locale;
  const [isPending, startTransition] = useTransition();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLocaleChange = (newLocale: Locale) => {
    if (newLocale === locale) {
      setIsOpen(false);
      return;
    }

    startTransition(() => {
      // Set cookie for locale preference
      document.cookie = `NEXT_LOCALE=${newLocale};path=/;max-age=31536000`;
      // Reload page to apply new locale
      window.location.reload();
    });
  };

  return (
    <div className="relative" ref={menuRef}>
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9"
        disabled={isPending}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Change language"
      >
        <Globe className="h-4 w-4" />
      </Button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 min-w-32 rounded-md border border-slate-700 bg-slate-900 py-1 shadow-lg">
          {locales.map((loc) => (
            <button
              key={loc}
              onClick={() => handleLocaleChange(loc)}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-800 ${
                locale === loc ? "bg-slate-800 text-white" : "text-slate-300"
              }`}
            >
              <span>{localeFlags[loc]}</span>
              <span className="flex-1">{localeNames[loc]}</span>
              {locale === loc && <Check className="h-4 w-4 text-blue-500" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
