import { Activity, Minus, TrendingDown, TrendingUp } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { calculatePercentChange, formatNumber } from "./utils"

interface TokenUsageCardProps {
  title: string
  totalTokens: number
  promptTokens: number
  completionTokens: number
  callCount: number
  previousTotalTokens?: number
  isLoading?: boolean
}

export function TokenUsageCard({
  title,
  totalTokens,
  promptTokens,
  completionTokens,
  callCount,
  previousTotalTokens,
  isLoading = false,
}: TokenUsageCardProps) {
  if (isLoading) {
    return <TokenUsageCardSkeleton title={title} />
  }

  const percentChange =
    previousTotalTokens !== undefined
      ? calculatePercentChange(totalTokens, previousTotalTokens)
      : null

  const TrendIcon =
    percentChange === null
      ? Minus
      : percentChange > 0
        ? TrendingUp
        : percentChange < 0
          ? TrendingDown
          : Minus

  const trendColor =
    percentChange === null
      ? "text-muted-foreground"
      : percentChange > 0
        ? "text-green-500"
        : percentChange < 0
          ? "text-red-500"
          : "text-muted-foreground"

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Activity className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold">{formatNumber(totalTokens)}</div>
          {percentChange !== null && (
            <div className={`flex items-center text-xs ${trendColor}`}>
              <TrendIcon className="mr-1 h-3 w-3" />
              {Math.abs(percentChange)}%
            </div>
          )}
        </div>
        <p className="text-xs text-muted-foreground">Total tokens consumed</p>

        <div className="mt-4 grid grid-cols-3 gap-4 text-xs">
          <div>
            <div className="font-medium text-muted-foreground">Prompt</div>
            <div className="font-semibold">{formatNumber(promptTokens)}</div>
          </div>
          <div>
            <div className="font-medium text-muted-foreground">Completion</div>
            <div className="font-semibold">
              {formatNumber(completionTokens)}
            </div>
          </div>
          <div>
            <div className="font-medium text-muted-foreground">Calls</div>
            <div className="font-semibold">{formatNumber(callCount)}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function TokenUsageCardSkeleton({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Activity className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="h-8 w-32 animate-pulse rounded bg-muted" />
        <p className="text-xs text-muted-foreground">Total tokens consumed</p>
        <div className="mt-4 grid grid-cols-3 gap-4">
          <div>
            <div className="h-3 w-12 animate-pulse rounded bg-muted" />
            <div className="mt-1 h-4 w-16 animate-pulse rounded bg-muted" />
          </div>
          <div>
            <div className="h-3 w-14 animate-pulse rounded bg-muted" />
            <div className="mt-1 h-4 w-16 animate-pulse rounded bg-muted" />
          </div>
          <div>
            <div className="h-3 w-8 animate-pulse rounded bg-muted" />
            <div className="mt-1 h-4 w-12 animate-pulse rounded bg-muted" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
