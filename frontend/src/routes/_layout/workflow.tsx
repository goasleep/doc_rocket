import { useState, useRef, useEffect } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { z } from "zod"
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, Clock, Loader2, ChevronsUpDown, X, Search } from "lucide-react"

import {
  WorkflowsService,
  ArticlesService,
  type WorkflowRunPublic,
  type AgentStep,
} from "@/client"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { useSSE } from "@/hooks/useSSE"
import { useWorkflowPolling } from "@/hooks/useWorkflowPolling"
import useCustomToast from "@/hooks/useCustomToast"

// ─── Searchable Multi-Select ───────────────────────────────────────────────────

type ArticleOption = { id: string; title: string; quality_score?: number | null }

function ArticleMultiSelect({
  options,
  selectedIds,
  onChange,
}: {
  options: ArticleOption[]
  selectedIds: Set<string>
  onChange: (ids: Set<string>) => void
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const filtered = search.trim()
    ? options.filter((o) => o.title.toLowerCase().includes(search.trim().toLowerCase()))
    : options

  const toggle = (id: string) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onChange(next)
  }

  const clearAll = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(new Set())
  }

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm hover:bg-muted/50 transition-colors"
      >
        <span className="text-muted-foreground truncate">
          {selectedIds.size === 0
            ? "选择素材文章（可选，可搜索）"
            : `已选 ${selectedIds.size} 篇`}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          {selectedIds.size > 0 && (
            <span
              role="button"
              tabIndex={0}
              onClick={clearAll}
              onKeyDown={(e) => e.key === "Enter" && clearAll(e as any)}
              className="rounded-sm hover:bg-muted p-0.5"
            >
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </span>
          )}
          <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
        </div>
      </button>

      {/* Selected badges */}
      {selectedIds.size > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {Array.from(selectedIds).map((id) => {
            const opt = options.find((o) => o.id === id)
            if (!opt) return null
            return (
              <span
                key={id}
                className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary text-xs px-2 py-0.5 max-w-[200px]"
              >
                <span className="truncate">{opt.title}</span>
                <button type="button" onClick={() => toggle(id)} className="shrink-0 hover:opacity-70">
                  <X className="h-3 w-3" />
                </button>
              </span>
            )
          })}
        </div>
      )}

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-md">
          <div className="flex items-center gap-2 px-3 py-2 border-b">
            <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <input
              autoFocus
              type="text"
              placeholder="搜索文章..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 text-sm bg-transparent outline-none placeholder:text-muted-foreground"
            />
          </div>
          <div className="max-h-52 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">无匹配文章</p>
            ) : (
              filtered.map((opt) => (
                <label
                  key={opt.id}
                  className="flex items-center gap-2.5 px-3 py-1.5 text-sm cursor-pointer hover:bg-muted"
                >
                  <Checkbox
                    checked={selectedIds.has(opt.id)}
                    onCheckedChange={() => toggle(opt.id)}
                  />
                  <span className="flex-1 truncate">{opt.title}</span>
                  {opt.quality_score != null && (
                    <span className="text-xs text-muted-foreground shrink-0">
                      {opt.quality_score.toFixed(0)}分
                    </span>
                  )}
                </label>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const searchSchema = z.object({
  run_id: z.string().optional(),
})

export const Route = createFileRoute("/_layout/workflow")({
  validateSearch: searchSchema,
  component: WorkflowPage,
  head: () => ({
    meta: [{ title: "工作流 - 内容引擎" }],
  }),
})

// ─── Step Bubble ──────────────────────────────────────────────────────────────

function StepBubble({ step }: { step: AgentStep }) {
  const [expanded, setExpanded] = useState(false)
  const isDone = step.status === "done"
  const isRunning = step.status === "running"

  return (
    <div className="flex gap-3">
      <div className="mt-1 shrink-0">
        {isDone ? (
          <CheckCircle2 className="h-5 w-5 text-green-500" />
        ) : isRunning ? (
          <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
        ) : (
          <Clock className="h-5 w-5 text-muted-foreground" />
        )}
      </div>
      <div className="flex-1 rounded-lg border bg-card p-3 space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">{step.agent_name}</span>
            <Badge variant="outline" className="text-xs capitalize">
              {step.role}
            </Badge>
          </div>
          {step.output && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2"
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
            </Button>
          )}
        </div>
        {step.thinking && (
          <p className="text-xs text-muted-foreground italic">{step.thinking}</p>
        )}
        {expanded && step.output && (
          <div className="text-sm whitespace-pre-wrap max-h-96 overflow-y-auto border rounded p-2 bg-muted/50 mt-2">
            {step.output}
          </div>
        )}
        {step.title_candidates && step.title_candidates.length > 0 && !expanded && (
          <p className="text-xs text-muted-foreground">
            候选标题：{step.title_candidates.length} 个
          </p>
        )}
      </div>
    </div>
  )
}

// ─── Human Review Panel ────────────────────────────────────────────────────────

function HumanReviewPanel({ run }: { run: WorkflowRunPublic }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [selectedTitle, setSelectedTitle] = useState("")
  const [customTitle, setCustomTitle] = useState("")
  const [feedback, setFeedback] = useState("")

  // Find title candidates from editor step
  const editorStep = run.steps.find((s) => s.role === "editor")
  const titleCandidates = editorStep?.title_candidates ?? []

  const approveMutation = useMutation({
    mutationFn: () =>
      WorkflowsService.approveWorkflow({
        id: run.id,
        requestBody: { selected_title: customTitle || selectedTitle || titleCandidates[0] || "未命名" },
      }),
    onSuccess: () => {
      showSuccessToast("已批准，草稿已创建")
      queryClient.invalidateQueries({ queryKey: ["workflows"] })
      navigate({ to: "/drafts" })
    },
    onError: () => showErrorToast("批准失败"),
  })

  const rejectMutation = useMutation({
    mutationFn: () =>
      WorkflowsService.rejectWorkflow({
        id: run.id,
        requestBody: { feedback },
      }),
    onSuccess: (child) => {
      showSuccessToast("已驳回，正在修订...")
      navigate({ to: "/workflow", search: { run_id: child.id } })
    },
    onError: () => showErrorToast("驳回失败"),
  })

  const abortMutation = useMutation({
    mutationFn: () => WorkflowsService.abortWorkflow({ id: run.id }),
    onSuccess: () => {
      showSuccessToast("工作流已终止")
      queryClient.invalidateQueries({ queryKey: ["workflows"] })
    },
    onError: () => showErrorToast("操作失败"),
  })

  // Reviewer step results
  const reviewerStep = run.steps.find((s) => s.role === "reviewer")
  let reviewerData: any = null
  if (reviewerStep?.output) {
    try {
      reviewerData = JSON.parse(reviewerStep.output)
    } catch {
      // ignore
    }
  }

  return (
    <Card className="border-amber-300 bg-amber-50 dark:bg-amber-950/20">
      <CardHeader className="pb-3">
        <CardTitle className="text-base text-amber-700 dark:text-amber-400">
          ⏸ 等待人工审核
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Final draft preview */}
        {run.final_output && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">最终草稿预览</p>
            <div className="max-h-48 overflow-y-auto text-sm whitespace-pre-wrap bg-background border rounded p-2">
              {run.final_output.slice(0, 800)}
              {run.final_output.length > 800 && "\n...（截断）"}
            </div>
          </div>
        )}

        {/* Title candidates */}
        {titleCandidates.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">选择标题</p>
            <div className="space-y-1">
              {titleCandidates.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`w-full text-left text-sm px-3 py-2 rounded border transition-colors ${
                    selectedTitle === t
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                      : "border-border hover:bg-muted"
                  }`}
                  onClick={() => {
                    setSelectedTitle(t)
                    setCustomTitle("")
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <input
              type="text"
              placeholder="或输入自定义标题..."
              className="mt-2 w-full text-sm rounded border border-input bg-background px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-ring"
              value={customTitle}
              onChange={(e) => {
                setCustomTitle(e.target.value)
                setSelectedTitle("")
              }}
            />
          </div>
        )}

        {/* Reviewer checklist */}
        {reviewerData && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">审核清单</p>
            {["fact_check_flags", "legal_notes", "format_issues"].map((key) => {
              const items = reviewerData[key] ?? []
              if (!items.length) return null
              return (
                <div key={key} className="mb-2">
                  <p className="text-xs uppercase font-mono text-muted-foreground">{key}</p>
                  <ul className="text-xs space-y-0.5 mt-1">
                    {items.map((item: any, i: number) => (
                      <li key={i} className="flex items-start gap-1">
                        <Badge
                          variant={item.severity === "error" ? "destructive" : "secondary"}
                          className="text-[10px] shrink-0 mt-0.5"
                        >
                          {item.severity}
                        </Badge>
                        <span>{item.description}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        )}

        {/* Feedback + actions */}
        <div>
          <textarea
            className="w-full text-sm rounded border border-input bg-background px-3 py-2 min-h-[60px] focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            placeholder="驳回时请填写修改意见..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
          <div className="flex gap-2 mt-2">
            <Button
              size="sm"
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending || (!selectedTitle && !customTitle && !titleCandidates.length)}
            >
              <CheckCircle2 className="h-4 w-4 mr-1" />
              批准
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => rejectMutation.mutate()}
              disabled={rejectMutation.isPending || !feedback.trim()}
            >
              ✏️ 驳回
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => {
                if (confirm("确认终止工作流？")) abortMutation.mutate()
              }}
              disabled={abortMutation.isPending}
            >
              <XCircle className="h-4 w-4 mr-1" />
              终止
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Workflow Run View ─────────────────────────────────────────────────────────

function WorkflowRunView({ runId }: { runId: string }) {
  const queryClient = useQueryClient()
  const [sseActive, setSseActive] = useState(true)
  // Initial fetch
  const { data: run, isLoading } = useQuery({
    queryKey: ["workflow", runId],
    queryFn: () => WorkflowsService.getWorkflow({ id: runId }),
  })

  const isTerminal =
    run?.status === "done" || run?.status === "failed" || run?.status === "waiting_human"

  useSSE(
    sseActive && !isTerminal ? `/api/v1/workflows/${runId}/stream` : null,
    {
      onEvent: (type, _data: any) => {
        if (type === "agent_start" || type === "agent_output") {
          queryClient.invalidateQueries({ queryKey: ["workflow", runId] })
        }
        if (type === "workflow_paused" || type === "workflow_done") {
          queryClient.invalidateQueries({ queryKey: ["workflow", runId] })
          setSseActive(false)
        }
      },
      onError: () => setSseActive(false),
    }
  )

  // Polling fallback
  useWorkflowPolling(sseActive ? null : runId)

  if (isLoading) {
    return <div className="flex justify-center py-12 text-muted-foreground">加载中...</div>
  }

  if (!run) {
    return <div className="text-center py-12 text-destructive">工作流不存在</div>
  }

  const displaySteps = run.steps

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <StatusBadge status={run.status} />
        <span className="text-sm text-muted-foreground">
          工作流 {run.type} · {new Date(run.created_at).toLocaleString("zh-CN")}
        </span>
        {run.parent_run_id && (
          <Badge variant="outline" className="text-xs">修订版</Badge>
        )}
      </div>

      <div className="space-y-3">
        {displaySteps.map((step, i) => (
          <StepBubble key={step.id ?? i} step={step} />
        ))}
        {(run.status === "pending" || run.status === "running") && displaySteps.length === 0 && (
          <div className="flex items-center gap-2 text-muted-foreground py-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            工作流排队中...
          </div>
        )}
      </div>

      {run.status === "waiting_human" && <HumanReviewPanel run={run} />}
    </div>
  )
}

// ─── New Workflow Trigger ──────────────────────────────────────────────────────

function NewWorkflowPanel() {
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [topic, setTopic] = useState("")

  const { data: articles } = useQuery({
    queryKey: ["articles"],
    queryFn: () => ArticlesService.listArticles({ skip: 0, limit: 200 }),
  })

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const triggerMutation = useMutation({
    mutationFn: () =>
      WorkflowsService.triggerWorkflow({
        requestBody: {
          type: "writing",
          article_ids: Array.from(selectedIds),
          topic: topic || undefined,
        },
      }),
    onSuccess: (run) => {
      showSuccessToast("工作流已触发")
      navigate({ to: "/workflow", search: { run_id: run.id } })
    },
    onError: () => showErrorToast("触发失败"),
  })

  const analyzed = articles?.data.filter((a) => a.status === "analyzed") ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">触发仿写工作流</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">
            选择素材文章（可选）
          </p>
          {analyzed.length === 0 ? (
            <p className="text-sm text-muted-foreground border rounded px-3 py-2">
              暂无已分析文章
            </p>
          ) : (
            <ArticleMultiSelect
              options={analyzed}
              selectedIds={selectedIds}
              onChange={setSelectedIds}
            />
          )}
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">或输入主题</p>
          <input
            type="text"
            placeholder="例如：AI 未来趋势分析..."
            className="w-full text-sm rounded border border-input bg-background px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-ring"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </div>
        <Button
          onClick={() => triggerMutation.mutate()}
          disabled={
            triggerMutation.isPending ||
            (selectedIds.size === 0 && !topic.trim())
          }
        >
          {triggerMutation.isPending ? "触发中..." : "开始仿写"}
        </Button>
      </CardContent>
    </Card>
  )
}

// ─── History Sidebar ───────────────────────────────────────────────────────────

function WorkflowHistory({ currentRunId }: { currentRunId?: string }) {
  const navigate = useNavigate()
  const { data } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => WorkflowsService.listWorkflows({ skip: 0, limit: 30 }),
  })

  if (!data?.data.length) return null

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground mb-2">历史工作流</p>
      {data.data.map((run: WorkflowRunPublic) => (
        <button
          key={run.id}
          type="button"
          className={`w-full text-left text-xs px-2 py-1.5 rounded flex items-center gap-2 transition-colors ${
            run.id === currentRunId ? "bg-muted font-semibold" : "hover:bg-muted/50"
          } ${run.parent_run_id ? "ml-4" : ""}`}
          onClick={() => navigate({ to: "/workflow", search: { run_id: run.id } })}
        >
          <StatusBadge status={run.status} className="text-[10px] px-1 py-0" />
          <span className="truncate">{run.id.slice(0, 8)}</span>
          {run.parent_run_id && <span className="text-muted-foreground">(修订)</span>}
        </button>
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

function WorkflowPage() {
  const { run_id } = useSearch({ from: "/_layout/workflow" })

  return (
    <div className="flex gap-6">
      {/* Main content */}
      <div className="flex-1 min-w-0 space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">工作流</h1>
          <p className="text-muted-foreground">AI 多 Agent 协作仿写，实时追踪进度</p>
        </div>
        {run_id ? (
          <WorkflowRunView runId={run_id} />
        ) : (
          <NewWorkflowPanel />
        )}
      </div>

      {/* Sidebar */}
      <div className="w-56 shrink-0">
        <WorkflowHistory currentRunId={run_id} />
      </div>
    </div>
  )
}
