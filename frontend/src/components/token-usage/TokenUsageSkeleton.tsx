import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

/**
 * Skeleton loader for token usage cards
 */
export function TokenUsageCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="mt-1 h-3 w-32" />
        <div className="mt-4 grid grid-cols-3 gap-4">
          <div>
            <Skeleton className="h-3 w-12" />
            <Skeleton className="mt-1 h-4 w-16" />
          </div>
          <div>
            <Skeleton className="h-3 w-14" />
            <Skeleton className="mt-1 h-4 w-16" />
          </div>
          <div>
            <Skeleton className="h-3 w-8" />
            <Skeleton className="mt-1 h-4 w-12" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Skeleton loader for trend charts
 */
export function TokenTrendChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-8 w-32" />
        </div>
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[250px] w-full" />
      </CardContent>
    </Card>
  )
}

/**
 * Skeleton loader for distribution charts
 */
export function TokenDistributionChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent>
        <Skeleton className="mx-auto h-[200px] w-[200px] rounded-full" />
        <div className="mt-4 flex justify-center gap-4">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-20" />
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Skeleton loader for agent comparison charts
 */
export function AgentComparisonChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-36" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[250px] w-full" />
      </CardContent>
    </Card>
  )
}

/**
 * Skeleton loader for token usage breakdown
 */
export function TokenUsageBreakdownSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent>
        <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-lg bg-muted p-3">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="mt-1 h-6 w-16" />
            </div>
          ))}
        </div>
        <div className="rounded-md border">
          <Skeleton className="h-10 w-full" />
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-12 w-full border-t" />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Combined skeleton for the full token usage section on agents page
 */
export function TokenUsageSectionSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <TokenUsageCardSkeleton />
        <TokenUsageCardSkeleton />
      </div>
      <TokenTrendChartSkeleton />
      <AgentComparisonChartSkeleton />
    </div>
  )
}
