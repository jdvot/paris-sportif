"use client";

import { Star, Quote, ExternalLink } from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { cn } from "@/lib/utils";

interface Testimonial {
  id: string;
  name: string;
  avatar?: string;
  rating: number;
  text: string;
  date: string;
  verified?: boolean;
}

// No default testimonials - component shows nothing or message when no real data provided

interface TestimonialsProps {
  testimonials?: Testimonial[];
  variant?: "grid" | "carousel" | "compact";
  showTrustpilot?: boolean;
  className?: string;
}

export function Testimonials({
  testimonials = [],
  variant = "grid",
  showTrustpilot = true,
  className,
}: TestimonialsProps) {
  const t = useTranslations("testimonials");
  const tCommon = useTranslations("common");

  // Return nothing if no real testimonials provided
  if (testimonials.length === 0) {
    return null;
  }

  const averageRating = testimonials.reduce((sum, t) => sum + t.rating, 0) / testimonials.length;

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header with Trustpilot-style rating */}
      {showTrustpilot && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl">
          <div className="flex items-center gap-4">
            <div className="text-center">
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {averageRating.toFixed(1)}
              </p>
              <div className="flex gap-0.5 justify-center">
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star
                    key={star}
                    className={cn(
                      "w-4 h-4",
                      star <= Math.round(averageRating)
                        ? "text-green-500 fill-green-500"
                        : "text-gray-300 dark:text-dark-600"
                    )}
                  />
                ))}
              </div>
            </div>
            <div>
              <p className="font-semibold text-gray-900 dark:text-white">{t("excellent")}</p>
              <p className="text-sm text-gray-600 dark:text-dark-400">
                {t("basedOn", { count: testimonials.length })}
              </p>
            </div>
          </div>
          <a
            href="https://www.trustpilot.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-green-500 text-white text-sm font-semibold rounded-lg hover:bg-green-600 transition-colors"
          >
            <Star className="w-4 h-4 fill-white" />
            {tCommon("viewOnTrustpilot")}
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      )}

      {/* Testimonials Grid */}
      {variant === "grid" && (
        <div className="grid sm:grid-cols-2 gap-4">
          {testimonials.map((testimonial) => (
            <TestimonialCard key={testimonial.id} testimonial={testimonial} />
          ))}
        </div>
      )}

      {/* Compact List */}
      {variant === "compact" && (
        <div className="space-y-3">
          {testimonials.slice(0, 3).map((testimonial) => (
            <div
              key={testimonial.id}
              className="flex items-start gap-3 p-3 bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-lg"
            >
              <Quote className="w-5 h-5 text-primary-400 flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-sm text-gray-700 dark:text-dark-300 line-clamp-2">
                  &ldquo;{testimonial.text}&rdquo;
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs font-medium text-gray-900 dark:text-white">
                    {testimonial.name}
                  </span>
                  <div className="flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={cn(
                          "w-3 h-3",
                          star <= testimonial.rating
                            ? "text-yellow-400 fill-yellow-400"
                            : "text-gray-300"
                        )}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TestimonialCard({ testimonial }: { testimonial: Testimonial }) {
  const locale = useLocale();

  return (
    <div className="bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-xl p-4 sm:p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold">
            {testimonial.name.charAt(0)}
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-white flex items-center gap-1">
              {testimonial.name}
              {testimonial.verified && (
                <span className="text-green-500 text-xs">✓</span>
              )}
            </p>
            <p className="text-xs text-gray-500 dark:text-dark-400">
              {new Date(testimonial.date).toLocaleDateString(locale === "fr" ? "fr-FR" : "en-US")}
            </p>
          </div>
        </div>
        <div className="flex gap-0.5">
          {[1, 2, 3, 4, 5].map((star) => (
            <Star
              key={star}
              className={cn(
                "w-4 h-4",
                star <= testimonial.rating
                  ? "text-yellow-400 fill-yellow-400"
                  : "text-gray-300 dark:text-dark-600"
              )}
            />
          ))}
        </div>
      </div>
      <p className="text-sm text-gray-700 dark:text-dark-300 leading-relaxed">
        &ldquo;{testimonial.text}&rdquo;
      </p>
    </div>
  );
}

// Widget for homepage - requires real rating data
export function TrustpilotWidget({
  className,
  rating
}: {
  className?: string;
  rating?: number;
}) {
  const t = useTranslations("testimonials");

  // Don't render if no real rating data
  if (rating === undefined) {
    return null;
  }

  const filledStars = Math.round(rating);

  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3 bg-white dark:bg-dark-800/50 border border-gray-200 dark:border-dark-700 rounded-lg",
        className
      )}
    >
      <div className="flex items-center gap-1.5">
        <div className="flex gap-0.5">
          {[1, 2, 3, 4, 5].map((star) => (
            <Star
              key={star}
              className={cn(
                "w-4 h-4",
                star <= filledStars
                  ? "text-green-500 fill-green-500"
                  : "text-gray-300 dark:text-dark-600"
              )}
            />
          ))}
        </div>
        <span className="text-sm font-bold text-gray-900 dark:text-white">{rating.toFixed(1)}</span>
      </div>
      <div className="h-4 w-px bg-gray-300 dark:bg-dark-600" />
      <span className="text-xs text-gray-600 dark:text-dark-400">
        {t("excellentOnTrustpilot")}
      </span>
    </div>
  );
}
