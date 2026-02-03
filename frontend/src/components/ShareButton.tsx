"use client";

import { useState, useCallback } from "react";
import { Share2, Twitter, Facebook, Link2, Check, AlertCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

interface ShareButtonProps {
  matchId: number;
  homeTeam: string;
  awayTeam: string;
  prediction: string;
  confidence: number;
  size?: "sm" | "md";
  className?: string;
}

export function ShareButton({
  matchId,
  homeTeam,
  awayTeam,
  prediction,
  confidence,
  size = "sm",
  className,
}: ShareButtonProps) {
  const t = useTranslations("common");
  const [copied, setCopied] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);

  const shareUrl = typeof window !== "undefined"
    ? `${window.location.origin}/match/${matchId}`
    : "";

  const shareText = `🎯 Prediction: ${homeTeam} vs ${awayTeam}\n📊 ${prediction} (${Math.round(confidence * 100)}% confiance)\n\nVia WinRate AI`;

  const clearError = useCallback(() => {
    if (shareError) {
      setTimeout(() => setShareError(null), 3000);
    }
  }, [shareError]);

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `${homeTeam} vs ${awayTeam} - Prediction`,
          text: shareText,
          url: shareUrl,
        });
        trackShare("native");
      } catch (err) {
        // AbortError means user cancelled - not an error
        if (err instanceof Error && err.name !== "AbortError") {
          setShareError(t("errorShare"));
          clearError();
        }
      }
    }
  };

  const handleTwitterShare = () => {
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`;
    window.open(twitterUrl, "_blank", "noopener,noreferrer,width=600,height=400");
    trackShare("twitter");
  };

  const handleFacebookShare = () => {
    const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}&quote=${encodeURIComponent(shareText)}`;
    window.open(facebookUrl, "_blank", "noopener,noreferrer,width=600,height=400");
    trackShare("facebook");
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      trackShare("copy");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      try {
        const textArea = document.createElement("textarea");
        textArea.value = shareUrl;
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.select();
        const success = document.execCommand("copy");
        document.body.removeChild(textArea);
        if (success) {
          setCopied(true);
          trackShare("copy");
          setTimeout(() => setCopied(false), 2000);
        } else {
          setShareError(t("errorCopy"));
          clearError();
        }
      } catch {
        setShareError(t("errorCopy"));
        clearError();
      }
    }
  };

  const trackShare = (platform: string) => {
    // Google Analytics 4 event
    if (typeof window !== "undefined" && typeof window.gtag === "function") {
      window.gtag("event", "share", {
        method: platform,
        content_type: "prediction",
        item_id: matchId.toString(),
      });
    }
  };

  const iconSize = size === "sm" ? "w-4 h-4" : "w-5 h-5";
  const buttonSize = size === "sm" ? "h-8 w-8" : "h-10 w-10";

  // Check if native share is available
  const hasNativeShare = typeof navigator !== "undefined" && !!navigator.share;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            buttonSize,
            "rounded-full text-slate-500 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-500/10 dark:hover:text-primary-400 transition-smooth",
            className
          )}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
        >
          <Share2 className={iconSize} />
          <span className="sr-only">Partager</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-48"
        onClick={(e) => e.stopPropagation()}
      >
        {hasNativeShare && (
          <DropdownMenuItem onClick={handleNativeShare} className="cursor-pointer">
            <Share2 className="w-4 h-4 mr-2" />
            Partager...
          </DropdownMenuItem>
        )}
        <DropdownMenuItem onClick={handleTwitterShare} className="cursor-pointer">
          <Twitter className="w-4 h-4 mr-2" />
          Twitter / X
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleFacebookShare} className="cursor-pointer">
          <Facebook className="w-4 h-4 mr-2" />
          Facebook
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleCopyLink} className="cursor-pointer">
          {copied ? (
            <>
              <Check className="w-4 h-4 mr-2 text-green-500" />
              <span className="text-green-600 dark:text-green-400">Copié !</span>
            </>
          ) : (
            <>
              <Link2 className="w-4 h-4 mr-2" />
              Copier le lien
            </>
          )}
        </DropdownMenuItem>
        {shareError && (
          <div className="px-2 py-1.5 text-xs text-red-600 dark:text-red-400 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {shareError}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

