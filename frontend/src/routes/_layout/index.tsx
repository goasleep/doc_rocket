import { createFileRoute } from "@tanstack/react-router"
import { Suspense, useState } from "react"

import {
  TokenUsageCard,
  TokenTrendChart,
  AgentComparisonChart,
  TokenUsageSectionSkeleton,
} from "@/components/token-usage"
import {
  useTodayStats,
  useYesterdayStats,
  useAgentTrendData,
  useAgentTokenStats,
} from "@/hooks/useTokenUsage"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - FastAPI Template",
      },
    ],
  }),
})

function TokenUsageSection() {
  const [trendDays, setTrendDays] = useState(7)
  const { data: todayData, isLoading: isTodayLoading } = useTodayStats()
  const { data: yesterdayData, isLoading: isYesterdayLoading } =
    useYesterdayStats()
  const { data: trendData, isLoading: isTrendLoading } = useAgentTrendData({
    days: trendDays,
  })

  // Calculate date range for agent stats (last 7 days)
  const endDate = new Date().toISOString().split("T")[0]
  const startDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0]
  const { data: agentStats, isLoading: isAgentStatsLoading } =
    useAgentTokenStats({
      startDate,
      endDate,
    })

  const todayStats = todayData || {
    total_tokens: 0,
    total_prompt_tokens: 0,
    total_completion_tokens: 0,
    total_calls: 0,
    agent_breakdown: [],
  }

  const yesterdayStats = yesterdayData || {
    total_tokens: 0,
    total_prompt_tokens: 0,
    total_completion_tokens: 0,
    total_calls: 0,
    agent_breakdown: [],
  }

  const trendChartData = trendData || []

  const agentComparisonData =
    agentStats?.map((item) => ({
      name: item.agent_config_name || "Unknown",
      tokens: item.total_tokens,
      calls: item.call_count,
    })) || []

  if (isTodayLoading || isYesterdayLoading) {
    return <TokenUsageSectionSkeleton />
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <TokenUsageCard
          title="Today's Usage"
          totalTokens={todayStats.total_tokens}
          promptTokens={todayStats.total_prompt_tokens}
          completionTokens={todayStats.total_completion_tokens}
          callCount={todayStats.total_calls}
          previousTotalTokens={yesterdayStats.total_tokens}
        />
        <TokenUsageCard
          title="Yesterday's Usage"
          totalTokens={yesterdayStats.total_tokens}
          promptTokens={yesterdayStats.total_prompt_tokens}
          completionTokens={yesterdayStats.total_completion_tokens}
          callCount={yesterdayStats.total_calls}
        />
      </div>
      <TokenTrendChart
        data={trendChartData}
        days={trendDays}
        onDaysChange={setTrendDays}
        isLoading={isTrendLoading}
      />
      <AgentComparisonChart
        data={agentComparisonData}
        title="Agent Usage (Last 7 Days)"
        isLoading={isAgentStatsLoading}
      />
    </div>
  )
}

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl truncate max-w-sm">
          Hi, {currentUser?.full_name || currentUser?.email} 👋
        </h1>
        <p className="text-muted-foreground">
          Welcome back, nice to see you again!
        </p>
      </div>

      {/* Token Usage Section */}
      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">
            加载中...
          </div>
        }
      >
        <TokenUsageSection />
      </Suspense>
    </div>
  )
}
