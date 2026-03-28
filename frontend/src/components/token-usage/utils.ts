import type { TrendDataPoint } from "@/client"

/**
 * Format a number with thousand separators
 */
export function formatNumber(num: number): string {
  return num.toLocaleString("en-US")
}

/**
 * Format a number with compact notation (e.g., 1.2K, 3.4M)
 */
export function formatCompactNumber(num: number): string {
  if (num < 1000) return num.toString()
  if (num < 1000000) return `${(num / 1000).toFixed(1)}K`
  return `${(num / 1000000).toFixed(1)}M`
}

/**
 * Format a date string for display
 */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

/**
 * Calculate percentage change between two values
 */
export function calculatePercentChange(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0
  return Math.round(((current - previous) / previous) * 100)
}

/**
 * Get trend data for chart with filled gaps
 */
export function fillTrendGaps(
  data: TrendDataPoint[],
  days: number,
): TrendDataPoint[] {
  const result: TrendDataPoint[] = []
  const endDate = new Date()
  const dateMap = new Map(
    data.map((item) => {
      const dateStr = typeof item.date === "string" ? item.date : new Date(item.date).toISOString().split("T")[0]
      return [dateStr, item]
    }),
  )

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(endDate)
    date.setDate(date.getDate() - i)
    const dateStr = date.toISOString().split("T")[0]

    const existing = dateMap.get(dateStr)
    if (existing) {
      result.push(existing)
    } else {
      result.push({
        date: dateStr,
        total_tokens: 0,
        total_calls: 0,
      })
    }
  }

  return result
}

/**
 * Tailwind color palette for charts
 */
export const chartColors = {
  primary: "#3b82f6", // blue-500
  secondary: "#8b5cf6", // violet-500
  success: "#22c55e", // green-500
  warning: "#f59e0b", // amber-500
  danger: "#ef4444", // red-500
  info: "#06b6d4", // cyan-500
  muted: "#6b7280", // gray-500
  // Extended palette
  colors: [
    "#3b82f6", // blue-500
    "#8b5cf6", // violet-500
    "#22c55e", // green-500
    "#f59e0b", // amber-500
    "#ef4444", // red-500
    "#06b6d4", // cyan-500
    "#ec4899", // pink-500
    "#f97316", // orange-500
    "#14b8a6", // teal-500
    "#6366f1", // indigo-500
  ],
}

/**
 * Get color by index from the palette
 */
export function getChartColor(index: number): string {
  return chartColors.colors[index % chartColors.colors.length]
}
