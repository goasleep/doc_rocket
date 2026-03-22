import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Bot, Clock, ExternalLink } from "lucide-react"
import { useState } from "react"

import { TaskRunsService, type TaskRunPublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export const Route = createFileRoute("/_layout/tasks")({
  component: TasksPage,
  head: () => ({
    meta: [{ title: "任务中心 - 内容引擎" }],
  }),
})

function TriggeredByBadge({ triggeredBy, label }: { triggeredBy: string; label?: string | null }) {
  if (triggeredBy === "scheduler") {
    return (
      <Badge variant="outline" className="gap-1">
        <Clock className="h-3 w-3" />
        定时
      </Badge>
    )
  }
  if (triggeredBy === "agent") {
    return (
      <Badge variant="outline" className="gap-1 border-blue-400 text-blue-600">
        <Bot className="h-3 w-3" />
        Agent{label ? ` · ${label}` : ""}
      </Badge>
    )
  }
  return <Badge variant="secondary">手动</Badge>
}

function StatusBadgeTask({ status, errorMessage }: { status: string; errorMessage?: string | null }) {
  const badge = (() => {
    switch (status) {
      case "done":
        return <Badge className="bg-green-500 hover:bg-green-600">完成</Badge>
      case "running":
        return <Badge className="bg-blue-500 hover:bg-blue-600 animate-pulse">运行中</Badge>
      case "failed":
        return <Badge variant="destructive">失败</Badge>
      default:
        return <Badge variant="secondary">待处理</Badge>
    }
  })()

  if (status === "failed" && errorMessage) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{badge}</TooltipTrigger>
          <TooltipContent className="max-w-xs break-words">
            <p className="text-xs">{errorMessage}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }
  return badge
}

function TaskTypeBadge({ taskType }: { taskType: string }) {
  const labels: Record<string, string> = {
    analyze: "分析",
    fetch: "抓取",
    workflow: "仿写",
  }
  return <Badge variant="outline">{labels[taskType] ?? taskType}</Badge>
}

function formatDuration(startedAt?: string | null, endedAt?: string | null) {
  if (!startedAt || !endedAt) return "—"
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime()
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m${Math.floor((ms % 60000) / 1000)}s`
}

function EntityCell({ run }: { run: TaskRunPublic }) {
  if (run.entity_id) {
    if (run.entity_type === "article") {
      return (
        <Link
          to="/articles/$id"
          params={{ id: run.entity_id }}
          className="text-sm hover:underline text-primary"
        >
          {run.entity_name ?? run.entity_id}
        </Link>
      )
    }
    return <span className="text-sm">{run.entity_name ?? run.entity_id}</span>
  }
  if (run.entity_name) {
    return <span className="text-sm text-muted-foreground">{run.entity_name}</span>
  }
  return <span className="text-sm text-muted-foreground">—</span>
}

function TasksPage() {
  const [taskType, setTaskType] = useState<string>("all")
  const [status, setStatus] = useState<string>("all")
  const [triggeredBy, setTriggeredBy] = useState<string>("all")

  const { data, isLoading } = useQuery({
    queryKey: ["task-runs", taskType, status, triggeredBy],
    queryFn: () =>
      TaskRunsService.listTaskRuns({
        taskType: taskType !== "all" ? (taskType as "analyze" | "fetch" | "workflow") : undefined,
        status: status !== "all" ? (status as "pending" | "running" | "done" | "failed") : undefined,
        triggeredBy: triggeredBy !== "all" ? (triggeredBy as "manual" | "scheduler" | "agent") : undefined,
        limit: 100,
      }),
    refetchInterval: (query) => {
      const items = query.state.data?.data ?? []
      const hasActive = items.some((r) => r.status === "running" || r.status === "pending")
      return hasActive ? 5000 : false
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">任务中心</h1>
        <p className="text-sm text-muted-foreground">所有分析、抓取、仿写任务的执行记录</p>
      </div>

      {/* Filter Bar */}
      <div className="flex gap-3 flex-wrap">
        <Select value={taskType} onValueChange={setTaskType}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="任务类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="analyze">分析</SelectItem>
            <SelectItem value="fetch">抓取</SelectItem>
            <SelectItem value="workflow">仿写</SelectItem>
          </SelectContent>
        </Select>

        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="pending">待处理</SelectItem>
            <SelectItem value="running">运行中</SelectItem>
            <SelectItem value="done">完成</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
          </SelectContent>
        </Select>

        <Select value={triggeredBy} onValueChange={setTriggeredBy}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="触发来源" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部来源</SelectItem>
            <SelectItem value="manual">手动</SelectItem>
            <SelectItem value="scheduler">定时</SelectItem>
            <SelectItem value="agent">Agent</SelectItem>
          </SelectContent>
        </Select>

        {data && (
          <span className="text-sm text-muted-foreground self-center">
            共 {data.count} 条记录
          </span>
        )}
      </div>

      {/* Tasks Table */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">加载中...</div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">类型</TableHead>
                <TableHead>关联实体</TableHead>
                <TableHead className="w-32">来源</TableHead>
                <TableHead className="w-24">状态</TableHead>
                <TableHead className="w-24">耗时</TableHead>
                <TableHead className="w-40">创建时间</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    暂无任务记录
                  </TableCell>
                </TableRow>
              )}
              {data?.data.map((run) => (
                <TableRow key={run.id}>
                  <TableCell>
                    <TaskTypeBadge taskType={run.task_type} />
                  </TableCell>
                  <TableCell>
                    <EntityCell run={run} />
                  </TableCell>
                  <TableCell>
                    <TriggeredByBadge triggeredBy={run.triggered_by} label={run.triggered_by_label} />
                  </TableCell>
                  <TableCell>
                    <StatusBadgeTask status={run.status} errorMessage={run.error_message} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDuration(run.started_at, run.ended_at)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(run.created_at).toLocaleString("zh-CN")}
                  </TableCell>
                  <TableCell>
                    {run.task_type === "workflow" && run.workflow_run_id && (
                      <Link
                        to="/workflow"
                        search={{ run_id: run.workflow_run_id }}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Link>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
