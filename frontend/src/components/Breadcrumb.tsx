"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-dark-400"
    >
      {items.map((item, index) => (
        <span key={item.label} className="flex items-center gap-1.5">
          {index > 0 && (
            <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" />
          )}
          {item.href ? (
            <Link
              href={item.href}
              className="hover:text-gray-700 dark:hover:text-dark-200 transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-gray-700 dark:text-dark-200 font-medium truncate max-w-[200px] sm:max-w-none">
              {item.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
