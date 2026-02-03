/**
 * Type definitions for recharts to address incomplete type support.
 * See: https://github.com/recharts/recharts/issues/3615
 */

/**
 * Radius tuple for Bar component corners.
 * Format: [top-left, top-right, bottom-right, bottom-left]
 */
export type BarRadius = [number, number, number, number];

/**
 * Type assertion helper for Bar radius prop.
 * Use this instead of `as any` for type-safe radius arrays.
 *
 * @example
 * <Bar dataKey="value" radius={barRadius([8, 8, 0, 0])} />
 */
export function barRadius(radius: BarRadius): number | BarRadius {
  return radius;
}

/**
 * Rounded top corners preset (common for vertical bars)
 */
export const ROUNDED_TOP: BarRadius = [8, 8, 0, 0];

/**
 * Rounded right corners preset (common for horizontal bars)
 */
export const ROUNDED_RIGHT: BarRadius = [0, 8, 8, 0];

/**
 * Fully rounded corners preset
 */
export const ROUNDED_ALL: BarRadius = [8, 8, 8, 8];
