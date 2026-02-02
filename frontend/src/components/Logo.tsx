"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  showText?: boolean;
  size?: "sm" | "md" | "lg";
}

export function Logo({ className, showText = false, size = "md" }: LogoProps) {
  const sizeClasses = {
    sm: "w-6 h-6",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };

  const textSizeClasses = {
    sm: "text-lg",
    md: "text-xl",
    lg: "text-2xl",
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className={cn(sizeClasses[size], "relative flex-shrink-0")}>
        <Image
          src="/logo.svg"
          alt="Paris Sportif"
          fill
          className="object-contain"
          priority
        />
      </div>
      {showText && (
        <span className={cn(
          "font-bold text-gray-900 dark:text-white",
          textSizeClasses[size]
        )}>
          Paris Sportif
        </span>
      )}
    </div>
  );
}
