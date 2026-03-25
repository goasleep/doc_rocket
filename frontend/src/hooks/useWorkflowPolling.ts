import { useQuery } from "@tanstack/react-query"

import { WorkflowsService } from "@/client"

const TERMINAL_STATUSES = new Set(["done", "failed"])

/**
 * Poll GET /workflows/{id} every 3s as a fallback when SSE is unavailable.
 * Stops polling once the workflow reaches a terminal state.
 */
export function useWorkflowPolling(runId: string | null) {
  return useQuery({
    queryKey: ["workflow", runId],
    queryFn: () => WorkflowsService.getWorkflow({ id: runId! }),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status || TERMINAL_STATUSES.has(status)) return false
      return 3000
    },
  })
}
