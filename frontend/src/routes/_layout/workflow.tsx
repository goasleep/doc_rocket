import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import {
  CheckCircle2,
  ChevronDown,
  ChevronsUpDown,
  ChevronUp,
  Clock,
  Loader2,
  RefreshCw,
  Search,
  Settings2,
  X,
  XCircle,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { z } from "zod"

import {
  type AgentStep,
  ArticlesService,
  type WorkflowRunPublic,
  WorkflowsService,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Switch } from "@/components/ui/switch"
import { StatusBadge } from "@/components/ui/StatusBadge"
import useCustomToast from "@/hooks/useCustomToast"
import { useSSE } from "@/hooks/useSSE"
import { useWorkflowPolling } from "@/hooks/useWorkflowPolling"

// ─── Searchable Multi-Select ───────────────────────────────────────────────────

type ArticleOption = {
  id: string
  title: string
  quality_score?: number | null
}

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
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const filtered = search.trim()
    ? options.filter((o) =>
        o.title.toLowerCase().includes(search.trim().toLowerCase()),
      )
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
            <button
              type="button"
              onClick={clearAll}
              className="rounded-sm hover:bg-muted p-0.5"
            >
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
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
                <button
                  type="button"
                  onClick={() => toggle(id)}
                  className="shrink-0 hover:opacity-70"
                >
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
              type="text"
              placeholder="搜索文章..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 text-sm bg-transparent outline-none placeholder:text-muted-foreground"
            />
          </div>
          <div className="max-h-52 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                无匹配文章
              </p>
            ) : (
              filtered.map((opt) => (
                <div
                  key={opt.id}
                  role="option"
                  aria-selected={selectedIds.has(opt.id)}
                  className="flex items-center gap-2.5 px-3 py-1.5 text-sm cursor-pointer hover:bg-muted"
                  onClick={() => toggle(opt.id)}
                  onKeyDown={(e) => e.key === "Enter" && toggle(opt.id)}
                  tabIndex={0}
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
                </div>
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
          <p className="text-xs text-muted-foreground italic">
            {step.thinking}
          </p>
        )}
        {expanded && step.output && (
          <div className="text-sm whitespace-pre-wrap max-h-96 overflow-y-auto border rounded p-2 bg-muted/50 mt-2">
            {step.output}
          </div>
        )}
        {step.title_candidates &&
          step.title_candidates.length > 0 &&
          !expanded && (
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

  // Find title candidates from editor step or orchestrator step
  const editorStep = run.steps.find((s) => s.role === "editor")
  const orchestratorStep = run.steps.find((s) => s.role === "orchestrator")
  const titleCandidates = editorStep?.title_candidates ?? orchestratorStep?.title_candidates ?? []

  const approveMutation = useMutation({
    mutationFn: () =>
      WorkflowsService.approveWorkflow({
        id: run.id,
        requestBody: {
          selected_title:
            customTitle || selectedTitle || titleCandidates[0] || "未命名",
        },
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
            <p className="text-xs font-medium text-muted-foreground mb-1">
              最终草稿预览
            </p>
            <div className="max-h-48 overflow-y-auto text-sm whitespace-pre-wrap bg-background border rounded p-2">
              {run.final_output.slice(0, 800)}
              {run.final_output.length > 800 && "\n...（截断）"}
            </div>
          </div>
        )}

        {/* Title candidates */}
        {titleCandidates.length > 0 ? (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              选择标题
            </p>
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
        ) : (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              输入标题
            </p>
            <input
              type="text"
              placeholder="请输入文章标题..."
              className="w-full text-sm rounded border border-input bg-background px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-ring"
              value={customTitle}
              onChange={(e) => {
                setCustomTitle(e.target.value)
              }}
            />
          </div>
        )}

        {/* Reviewer checklist */}
        {reviewerData && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              审核清单
            </p>
            {["fact_check_flags", "legal_notes", "format_issues"].map((key) => {
              const items = reviewerData[key] ?? []
              if (!items.length) return null
              return (
                <div key={key} className="mb-2">
                  <p className="text-xs uppercase font-mono text-muted-foreground">
                    {key}
                  </p>
                  <ul className="text-xs space-y-0.5 mt-1">
                    {items.map((item: any, i: number) => (
                      <li key={i} className="flex items-start gap-1">
                        <Badge
                          variant={
                            item.severity === "error"
                              ? "destructive"
                              : "secondary"
                          }
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
              disabled={
                approveMutation.isPending ||
                (!selectedTitle && !customTitle && !titleCandidates.length)
              }
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
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [sseActive, setSseActive] = useState(true)
  // Initial fetch
  const { data: run, isLoading } = useQuery({
    queryKey: ["workflow", runId],
    queryFn: () => WorkflowsService.getWorkflow({ id: runId }),
  })

  const retryMutation = useMutation({
    mutationFn: () => WorkflowsService.retryWorkflow({ id: runId }),
    onSuccess: (newRun) => {
      showSuccessToast("已创建重试工作流")
      navigate({ to: "/workflow", search: { run_id: newRun.id } })
      queryClient.invalidateQueries({ queryKey: ["workflows"] })
    },
    onError: (err: any) => {
      const detail = err?.body?.detail ?? "重试失败"
      showErrorToast(detail)
    },
  })

  const isTerminal =
    run?.status === "done" ||
    run?.status === "failed" ||
    run?.status === "waiting_human"

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
    },
  )

  // Polling fallback
  useWorkflowPolling(sseActive ? null : runId)

  if (isLoading) {
    return (
      <div className="flex justify-center py-12 text-muted-foreground">
        加载中...
      </div>
    )
  }

  if (!run) {
    return (
      <div className="text-center py-12 text-destructive">工作流不存在</div>
    )
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
          <Badge variant="outline" className="text-xs">
            修订版
          </Badge>
        )}
      </div>

      <div className="space-y-3">
        {displaySteps.map((step, i) => (
          <StepBubble key={step.id ?? i} step={step} />
        ))}
        {(run.status === "pending" || run.status === "running") &&
          displaySteps.length === 0 && (
            <div className="flex items-center gap-2 text-muted-foreground py-4">
              <Loader2 className="h-4 w-4 animate-spin" />
              工作流排队中...
            </div>
          )}
      </div>

      {run.status === "waiting_human" && <HumanReviewPanel run={run} />}

      {/* Failed workflow - show error and retry */}
      {run.status === "failed" && (
        <Card className="border-destructive bg-destructive/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-base text-destructive flex items-center gap-2">
              <XCircle className="h-5 w-5" />
              工作流失败
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {run.error_message && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">
                  错误原因
                </p>
                <div className="text-sm bg-background border rounded p-2 text-destructive">
                  {run.error_message}
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                {retryMutation.isPending ? "重试中..." : "重新执行"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => navigate({ to: "/workflow" })}
              >
                新建工作流
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ─── New Workflow Trigger ──────────────────────────────────────────────────────

const STYLE_OPTIONS = [
  { value: "story", label: "故事化叙述", desc: "用故事带动内容" },
  { value: "data", label: "数据驱动", desc: "用数据论证观点" },
  { value: "sharp", label: "犀利点评", desc: "观点鲜明、点评直接" },
  { value: "casual", label: "口语化", desc: "轻松自然的表达" },
  { value: "suspense", label: "悬念开头", desc: "用悬念吸引读者" },
  { value: "contrast", label: "对比结构", desc: "通过对比突出观点" },
  { value: "emotional", label: "情绪共鸣", desc: "引发情感共鸣" },
  { value: "practical", label: "实用干货", desc: "注重实用性" },
]

function StyleHintTags({
  selected,
  onChange,
}: {
  selected: string[]
  onChange: (values: string[]) => void
}) {
  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value))
    } else {
      onChange([...selected, value])
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {STYLE_OPTIONS.map((opt) => {
        const isSelected = selected.includes(opt.value)
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => toggle(opt.value)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors ${
              isSelected
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80 text-muted-foreground"
            }`}
            title={opt.desc}
          >
            {opt.label}
            {isSelected && <CheckCircle2 className="h-3.5 w-3.5" />}
          </button>
        )
      })}
    </div>
  )
}

function NewWorkflowPanel() {
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [topic, setTopic] = useState("")
  const [styleHints, setStyleHints] = useState<string[]>([])
  const [autoMatchStyles, setAutoMatchStyles] = useState(true)
  const [useOrchestrator, setUseOrchestrator] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)

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
          topic: topic.trim(),
          style_hints: styleHints,
          article_ids: Array.from(selectedIds),
          auto_match_styles: autoMatchStyles,
          use_orchestrator: useOrchestrator,
        },
      }),
    onSuccess: (run) => {
      showSuccessToast("工作流已触发")
      navigate({ to: "/workflow", search: { run_id: run.id } })
    },
    onError: () => showErrorToast("触发失败"),
  })

  const analyzed = articles?.data.filter((a) => a.status === "analyzed") ?? []

  const canSubmit = topic.trim().length > 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">触发仿写工作流</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Topic - Required */}
        <div>
          <label className="text-sm font-medium mb-1.5 flex items-center gap-1">
            写作主题
            <span className="text-destructive">*</span>
          </label>
          <input
            type="text"
            placeholder="例如：AI 会取代程序员吗？"
            className="w-full text-sm rounded border border-input bg-background px-3 py-2 focus:outline-none focus:ring-2 focus:ring-ring"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
          <p className="text-xs text-muted-foreground mt-1">
            告诉 AI 你想写什么内容，AI 会自动生成大纲
          </p>
        </div>

        {/* Style Hints - Optional */}
        <div>
          <label className="text-sm font-medium mb-2 block">风格偏好（可选）</label>
          <StyleHintTags selected={styleHints} onChange={setStyleHints} />
          <p className="text-xs text-muted-foreground mt-2">
            选择风格偏好帮助 AI 更精准匹配参考文章
          </p>
        </div>

        {/* Orchestrator Mode */}
        <div className="flex items-center justify-between rounded-lg border p-3">
          <div className="space-y-0.5">
            <p className="text-sm font-medium">使用 Orchestrator 模式</p>
            <p className="text-xs text-muted-foreground">
              启用后由 Orchestrator 智能协调多 Agent 协作，而非线性流水线
            </p>
          </div>
          <Switch
            checked={useOrchestrator}
            onCheckedChange={setUseOrchestrator}
          />
        </div>

        {/* Advanced: Manual Article Selection */}
        <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Settings2 className="h-4 w-4" />
              高级：指定参考文章
              {advancedOpen ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-3 space-y-3">
            {/* Auto-match toggle */}
            <div className="flex items-start gap-3 rounded-lg border p-3">
              <Checkbox
                id="auto-match"
                checked={autoMatchStyles}
                onCheckedChange={(v) => setAutoMatchStyles(v as boolean)}
              />
              <div className="space-y-1">
                <label
                  htmlFor="auto-match"
                  className="text-sm font-medium cursor-pointer"
                >
                  同时自动匹配风格文章
                </label>
                <p className="text-xs text-muted-foreground">
                  开启后，AI 会在你指定的文章基础上，自动从文章库匹配更多风格参考
                </p>
              </div>
            </div>

            {/* Manual article selection */}
            <div>
              <label className="text-sm font-medium mb-2 block">
                指定参考文章（可选）
              </label>
              {analyzed.length === 0 ? (
                <p className="text-sm text-muted-foreground border rounded px-3 py-2">
                  暂无已分析文章，请先分析文章
                </p>
              ) : (
                <ArticleMultiSelect
                  options={analyzed}
                  selectedIds={selectedIds}
                  onChange={setSelectedIds}
                />
              )}
              <p className="text-xs text-muted-foreground mt-2">
                指定的文章将作为主要风格参考，优先级高于自动匹配的文章
              </p>
            </div>
          </CollapsibleContent>
        </Collapsible>

        <Button
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending || !canSubmit}
          className="w-full"
        >
          {triggerMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              触发中...
            </>
          ) : (
            "开始仿写"
          )}
        </Button>
      </CardContent>
    </Card>
  )
}

// ─── Workflow List ─────────────────────────────────────────────────────────────

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  const mm = String(d.getMonth() + 1).padStart(2, "0")
  const dd = String(d.getDate()).padStart(2, "0")
  const hh = String(d.getHours()).padStart(2, "0")
  const min = String(d.getMinutes()).padStart(2, "0")
  return `${mm}-${dd} ${hh}:${min}`
}

function workflowLabel(run: WorkflowRunPublic): string {
  if (run.input.topic) return run.input.topic
  const count = run.input.article_ids?.length ?? 0
  if (count > 0) return `${count} 篇参考文章`
  return "无素材"
}

function WorkflowList({ currentRunId }: { currentRunId?: string }) {
  const navigate = useNavigate()
  const [searchTopic, setSearchTopic] = useState("")
  const [filterStatus, setFilterStatus] = useState("all")

  const { data } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => WorkflowsService.listWorkflows({ skip: 0, limit: 100 }),
  })

  const filtered = (data?.data ?? []).filter((run: WorkflowRunPublic) => {
    if (filterStatus !== "all" && run.status !== filterStatus) return false
    if (searchTopic.trim()) {
      const q = searchTopic.toLowerCase()
      if (!workflowLabel(run).toLowerCase().includes(q)) return false
    }
    return true
  })

  return (
    <div className="space-y-3">
      {/* Filter bar */}
      <div className="flex gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="搜索主题..."
            className="pl-8 pr-3 py-1.5 text-sm rounded border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring w-44"
            value={searchTopic}
            onChange={(e) => setSearchTopic(e.target.value)}
          />
        </div>
        <select
          className="text-sm rounded border border-input bg-background px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-ring"
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
        >
          <option value="all">全部状态</option>
          <option value="pending">待处理</option>
          <option value="running">运行中</option>
          <option value="waiting_human">等待审核</option>
          <option value="done">完成</option>
          <option value="failed">失败</option>
        </select>
        <span className="text-xs text-muted-foreground self-center">
          {filtered.length} 条
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          暂无工作流记录
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((run: WorkflowRunPublic) => (
            <button
              key={run.id}
              type="button"
              className={`w-full text-left rounded-lg border px-4 py-3 flex items-center gap-3 transition-colors ${
                run.id === currentRunId
                  ? "border-primary bg-muted"
                  : "border-border hover:bg-muted/50"
              } ${run.parent_run_id ? "ml-4 border-dashed" : ""}`}
              onClick={() =>
                navigate({ to: "/workflow", search: { run_id: run.id } })
              }
            >
              <StatusBadge status={run.status} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">
                  {workflowLabel(run)}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatDate(run.created_at)}
                </div>
              </div>
              {run.parent_run_id && (
                <span className="text-xs text-muted-foreground shrink-0">
                  修订版
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

function WorkflowPage() {
  const { run_id } = useSearch({ from: "/_layout/workflow" })
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">工作流</h1>
          <p className="text-muted-foreground">
            AI 多 Agent 协作仿写，实时追踪进度
          </p>
        </div>
        {run_id && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate({ to: "/workflow" })}
          >
            + 新建工作流
          </Button>
        )}
      </div>

      {run_id ? (
        <div className="space-y-6">
          <WorkflowRunView runId={run_id} />
          <div>
            <h2 className="text-sm font-medium text-muted-foreground mb-3">
              历史工作流
            </h2>
            <WorkflowList currentRunId={run_id} />
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <NewWorkflowPanel />
          <div>
            <h2 className="text-sm font-medium text-muted-foreground mb-3">
              历史工作流
            </h2>
            <WorkflowList />
          </div>
        </div>
      )}
    </div>
  )
}
