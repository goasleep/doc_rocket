import { useQuery } from "@tanstack/react-query"
import {
  TokenUsageService,
  type TokenUsageGetTrendDataData,
  type TokenUsageGetAgentStatsData,
  type TokenUsageGetSingleAgentStatsData,
} from "@/client"

// Query keys for token usage data
export const tokenUsageKeys = {
  all: ["token-usage"] as const,
  today: () => [...tokenUsageKeys.all, "today"] as const,
  yesterday: () => [...tokenUsageKeys.all, "yesterday"] as const,
  trend: (params: TokenUsageGetTrendDataData) =>
    [...tokenUsageKeys.all, "trend", params] as const,
  agents: (params: TokenUsageGetAgentStatsData) =>
    [...tokenUsageKeys.all, "agents", params] as const,
  agent: (agentId: string, params: Omit<TokenUsageGetSingleAgentStatsData, "agentId">) =>
    [...tokenUsageKeys.all, "agent", agentId, params] as const,
  article: (articleId: string) =>
    [...tokenUsageKeys.all, "article", articleId] as const,
}

/**
 * Hook to fetch today's token usage statistics
 */
export function useTodayStats() {
  return useQuery({
    queryKey: tokenUsageKeys.today(),
    queryFn: () => TokenUsageService.getTodayStats(),
  })
}

/**
 * Hook to fetch yesterday's token usage statistics
 */
export function useYesterdayStats() {
  return useQuery({
    queryKey: tokenUsageKeys.yesterday(),
    queryFn: () => TokenUsageService.getYesterdayStats(),
  })
}

/**
 * Hook to fetch trend data for charting
 * @param params - Query parameters including days and optional agent filter
 */
export function useAgentTrendData(params: TokenUsageGetTrendDataData = {}) {
  return useQuery({
    queryKey: tokenUsageKeys.trend(params),
    queryFn: () => TokenUsageService.getTrendData(params),
  })
}

/**
 * Hook to fetch aggregated agent statistics
 * @param params - Query parameters including date range and optional agent filter
 */
export function useAgentTokenStats(params: TokenUsageGetAgentStatsData = {}) {
  return useQuery({
    queryKey: tokenUsageKeys.agents(params),
    queryFn: () => TokenUsageService.getAgentStats(params),
  })
}

/**
 * Hook to fetch statistics for a specific agent
 * @param agentId - The UUID of the agent
 * @param params - Query parameters including date range
 */
export function useSingleAgentStats(
  agentId: string,
  params: Omit<TokenUsageGetSingleAgentStatsData, "agentId"> = {}
) {
  return useQuery({
    queryKey: tokenUsageKeys.agent(agentId, params),
    queryFn: () => TokenUsageService.getSingleAgentStats({ agentId, ...params }),
    enabled: !!agentId,
  })
}

/**
 * Hook to fetch token usage breakdown for a specific article
 * @param articleId - The UUID of the article
 */
export function useArticleTokenUsage(articleId: string) {
  return useQuery({
    queryKey: tokenUsageKeys.article(articleId),
    queryFn: () => TokenUsageService.getArticleTokenUsage({ articleId }),
    enabled: !!articleId,
  })
}
