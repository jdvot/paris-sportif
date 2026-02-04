"use client";

import { useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Clock } from "lucide-react";

interface TickerItem {
  id: string;
  homeTeam: string;
  awayTeam: string;
  prediction: string;
  confidence: number;
  odds?: number;
  kickoff?: string;
  status?: "pending" | "won" | "lost";
}

interface TickerCarouselProps {
  items: TickerItem[];
  speed?: number;
  className?: string;
}

function TickerItemCard({ item }: { item: TickerItem }) {
  const statusColors = {
    pending: "bg-blue-500/10 border-blue-500/30",
    won: "bg-green-500/10 border-green-500/30",
    lost: "bg-red-500/10 border-red-500/30",
  };

  const statusIcons = {
    pending: <Clock className="w-3 h-3 text-blue-400" />,
    won: <TrendingUp className="w-3 h-3 text-green-400" />,
    lost: <TrendingDown className="w-3 h-3 text-red-400" />,
  };

  return (
    <div
      className={cn(
        "flex-shrink-0 flex items-center gap-3 px-4 py-2 rounded-lg border mx-2",
        statusColors[item.status || "pending"]
      )}
    >
      {statusIcons[item.status || "pending"]}

      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap">
          {item.homeTeam}
        </span>
        <span className="text-xs text-gray-400">vs</span>
        <span className="text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap">
          {item.awayTeam}
        </span>
      </div>

      <div className="h-4 w-px bg-gray-300 dark:bg-slate-600" />

      <span className="text-xs font-semibold text-primary-600 dark:text-primary-400 whitespace-nowrap">
        {item.prediction}
      </span>

      <span
        className={cn(
          "text-xs font-bold px-1.5 py-0.5 rounded",
          item.confidence >= 70
            ? "bg-green-500/20 text-green-600 dark:text-green-400"
            : item.confidence >= 55
            ? "bg-yellow-500/20 text-yellow-600 dark:text-yellow-400"
            : "bg-gray-500/20 text-gray-600 dark:text-gray-400"
        )}
      >
        {item.confidence}%
      </span>

      {item.odds && (
        <span className="text-xs text-gray-500 dark:text-slate-400">
          @{item.odds.toFixed(2)}
        </span>
      )}
    </div>
  );
}

export function TickerCarousel({
  items,
  speed = 30,
  className,
}: TickerCarouselProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);

  if (!items || items.length === 0) return null;

  // Duplicate items for seamless loop
  const duplicatedItems = [...items, ...items];

  return (
    <div
      className={cn(
        "relative overflow-hidden bg-gray-50 dark:bg-slate-900/50 border-y border-gray-200 dark:border-slate-800",
        className
      )}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Gradient masks */}
      <div className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-gray-50 dark:from-slate-900/50 to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-gray-50 dark:from-slate-900/50 to-transparent z-10 pointer-events-none" />

      {/* Scrolling container */}
      <div
        ref={containerRef}
        className="flex py-3"
        style={{
          animation: `ticker ${items.length * speed}s linear infinite`,
          animationPlayState: isPaused ? "paused" : "running",
        }}
      >
        {duplicatedItems.map((item, idx) => (
          <TickerItemCard key={`${item.id}-${idx}`} item={item} />
        ))}
      </div>

      {/* CSS Animation */}
      <style jsx>{`
        @keyframes ticker {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }
      `}</style>
    </div>
  );
}

// Demo component with sample data
export function TickerCarouselDemo() {
  const sampleItems: TickerItem[] = [
    { id: "1", homeTeam: "Arsenal", awayTeam: "Chelsea", prediction: "1", confidence: 72, odds: 1.85, status: "pending" },
    { id: "2", homeTeam: "Barcelona", awayTeam: "Real Madrid", prediction: "X", confidence: 58, odds: 3.40, status: "pending" },
    { id: "3", homeTeam: "Bayern", awayTeam: "Dortmund", prediction: "1", confidence: 68, odds: 1.65, status: "won" },
    { id: "4", homeTeam: "PSG", awayTeam: "Marseille", prediction: "1", confidence: 75, odds: 1.45, status: "won" },
    { id: "5", homeTeam: "Juventus", awayTeam: "Inter", prediction: "2", confidence: 55, odds: 2.80, status: "lost" },
    { id: "6", homeTeam: "Liverpool", awayTeam: "Man City", prediction: "BTTS", confidence: 82, odds: 1.72, status: "pending" },
  ];

  return <TickerCarousel items={sampleItems} />;
}
