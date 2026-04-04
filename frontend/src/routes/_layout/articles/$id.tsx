import {
  useMutation,
  useQuery,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import MDEditor from "@uiw/react-md-editor"
import {
  BarChart3,
  BookOpen,
  Bot,
  Check,
  CheckCircle2,
  Clock,
  Coins,
  FileText,
  History,
  Pen,
  Pencil,
  RefreshCw,
  X,
  XCircle,
} from "lucide-react"
import { Suspense, useState } from "react"

import {
  AnalysesService,
  type AnalysisTraceStep,
  type ArticleAnalysisPublic,
  ArticlesService,
  type TaskRunPublic,
  TaskRunsService,
  WorkflowsService,
} from "@/client"
import {
  AnalysisSummarySection,
  AnalysisTraceTimeline,
  ComparisonReferenceCard,
  QualityScoreDetailCard,
} from "@/components/Analysis"
import {
  TokenDistributionChart,
  TokenUsageBreakdown,
  TokenUsageBreakdownSkeleton,
} from "@/components/token-usage"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useCustomToast from "@/hooks/useCustomToast"
import { useArticleTokenUsage } from "@/hooks/useTokenUsage"

export const Route = createFileRoute("/_layout/articles/$id")({
  component: ArticleDetailPage,
  head: () => ({
    meta: [{ title: "文章详情 - 内容引擎" }],
  }),
})

function QualityScoreCard({ analysis }: { analysis: ArticleAnalysisPublic }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          质量评分
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-4xl font-bold">
          {analysis.quality_score.toFixed(0)}
        </div>
        <div className="text-xs text-muted-foreground mt-1">
          深度 {analysis.quality_breakdown?.content_depth?.toFixed(0) ?? "—"} ·
          可读 {analysis.quality_breakdown?.readability?.toFixed(0) ?? "—"} ·
          原创 {analysis.quality_breakdown?.originality?.toFixed(0) ?? "—"} ·
          传播{" "}
          {analysis.quality_breakdown?.virality_potential?.toFixed(0) ?? "—"}
        </div>
        {analysis.rubric_version && (
          <div className="text-xs text-muted-foreground mt-1">
            评分标准: {analysis.rubric_version}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function HookFrameworkCard({ analysis }: { analysis: ArticleAnalysisPublic }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          钩子 & 框架
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <div>
          <span className="text-xs text-muted-foreground">钩子类型：</span>
          {analysis.hook_type}
        </div>
        <div>
          <span className="text-xs text-muted-foreground">写作框架：</span>
          {analysis.framework}
        </div>
        <div>
          <span className="text-xs text-muted-foreground">目标受众：</span>
          {analysis.target_audience}
        </div>
      </CardContent>
    </Card>
  )
}

function EmotionalTriggersCard({
  analysis,
}: {
  analysis: ArticleAnalysisPublic
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          情绪触发词
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-1">
          {analysis.emotional_triggers.map((t) => (
            <Badge key={t} variant="secondary">
              {t}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function KeywordsCard({ analysis }: { analysis: ArticleAnalysisPublic }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          关键词 & 金句
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex flex-wrap gap-1">
          {analysis.keywords.map((k) => (
            <Badge key={k} variant="outline" className="text-xs">
              {k}
            </Badge>
          ))}
        </div>
        <ul className="space-y-1 mt-1">
          {analysis.key_phrases.map((phrase, i) => (
            <li key={i} className="text-xs text-muted-foreground italic">
              "{phrase}"
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

function StructureCard({ analysis }: { analysis: ArticleAnalysisPublic }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          文章结构
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm space-y-1">
        <div>
          <span className="text-xs text-muted-foreground">开头：</span>
          {analysis.structure?.intro}
        </div>
        <div>
          <span className="text-xs text-muted-foreground">段落数：</span>
          {analysis.structure?.body_sections?.length ?? 0}
        </div>
        <div>
          <span className="text-xs text-muted-foreground">结尾：</span>
          {analysis.structure?.cta}
        </div>
      </CardContent>
    </Card>
  )
}

function StyleCard({ analysis }: { analysis: ArticleAnalysisPublic }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          写作风格
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm space-y-1">
        <div>
          <span className="text-xs text-muted-foreground">语气：</span>
          {analysis.style?.tone}
        </div>
        <div>
          <span className="text-xs text-muted-foreground">正式程度：</span>
          {analysis.style?.formality}
        </div>
        <div>
          <span className="text-xs text-muted-foreground">平均句长：</span>
          {analysis.style?.avg_sentence_length}
        </div>
      </CardContent>
    </Card>
  )
}

function AnalysisCards({ analysis }: { analysis: ArticleAnalysisPublic }) {
  return (
    <div className="space-y-6">
      {/* Basic Analysis Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <QualityScoreCard analysis={analysis} />
        <HookFrameworkCard analysis={analysis} />
        <EmotionalTriggersCard analysis={analysis} />
        <KeywordsCard analysis={analysis} />
        <StructureCard analysis={analysis} />
        <StyleCard analysis={analysis} />
      </div>

      {/* Quality Score Details */}
      {analysis.quality_score_details &&
        analysis.quality_score_details.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">维度评分详情</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {analysis.quality_score_details.map((detail, idx) => (
                <QualityScoreDetailCard key={idx} detail={detail} />
              ))}
            </div>
          </div>
        )}

      {/* Comparison References */}
      {analysis.comparison_references &&
        analysis.comparison_references.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold">对比参考</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {analysis.comparison_references.map((ref, idx) => (
                <ComparisonReferenceCard key={idx} reference={ref} />
              ))}
            </div>
          </div>
        )}

      {/* Analysis Summary */}
      {analysis.analysis_summary && (
        <AnalysisSummarySection
          summary={analysis.analysis_summary}
          improvementSuggestions={analysis.improvement_suggestions || []}
          rubricVersion={analysis.rubric_version}
          analysisDurationMs={analysis.analysis_duration_ms}
        />
      )}
    </div>
  )
}

function TriggeredByBadge({
  triggeredBy,
  label,
}: {
  triggeredBy: string
  label?: string | null
}) {
  if (triggeredBy === "scheduler") {
    return (
      <Badge variant="outline" className="gap-1 text-xs">
        <Clock className="h-3 w-3" />
        定时
      </Badge>
    )
  }
  if (triggeredBy === "agent") {
    return (
      <Badge
        variant="outline"
        className="gap-1 text-xs border-blue-400 text-blue-600"
      >
        <Bot className="h-3 w-3" />
        Agent{label ? ` · ${label}` : ""}
      </Badge>
    )
  }
  return (
    <Badge variant="secondary" className="text-xs">
      手动
    </Badge>
  )
}

function formatDuration(startedAt?: string | null, endedAt?: string | null) {
  if (!startedAt || !endedAt) return null
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime()
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m${Math.floor((ms % 60000) / 1000)}s`
}

function TimelineNode({ run }: { run: TaskRunPublic }) {
  const typeLabels: Record<string, string> = {
    analyze: "分析",
    fetch: "抓取",
    refine: "精修",
    workflow: "仿写",
  }
  const duration = formatDuration(run.started_at, run.ended_at)

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="mt-1">
          {run.status === "done" ? (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          ) : run.status === "failed" ? (
            <XCircle className="h-4 w-4 text-destructive" />
          ) : (
            <div className="h-4 w-4 rounded-full border-2 border-muted-foreground" />
          )}
        </div>
        <div className="w-px flex-1 bg-border mt-1" />
      </div>
      <div className="pb-4 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm">
            {typeLabels[run.task_type] ?? run.task_type}任务
          </span>
          <TriggeredByBadge
            triggeredBy={run.triggered_by}
            label={run.triggered_by_label}
          />
          {run.status === "done" && (
            <Badge className="bg-green-500 hover:bg-green-600 text-xs">
              完成
            </Badge>
          )}
          {run.status === "failed" && (
            <Badge variant="destructive" className="text-xs">
              失败
            </Badge>
          )}
          {run.status === "running" && (
            <Badge className="bg-blue-500 hover:bg-blue-600 text-xs animate-pulse">
              运行中
            </Badge>
          )}
          {run.status === "pending" && (
            <Badge variant="secondary" className="text-xs">
              待处理
            </Badge>
          )}
          {duration && (
            <span className="text-xs text-muted-foreground">{duration}</span>
          )}
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {new Date(run.created_at).toLocaleString("zh-CN")}
        </div>
        {run.status === "failed" && run.error_message && (
          <div className="mt-1 text-xs text-destructive bg-destructive/10 rounded p-2 font-mono">
            {run.error_message}
          </div>
        )}
        {run.task_type === "workflow" && run.workflow_run_id && (
          <Link
            to="/workflow"
            search={{ run_id: run.workflow_run_id }}
            className="text-xs text-primary hover:underline mt-1 inline-flex items-center gap-1"
          >
            查看仿写详情 ↗
          </Link>
        )}
      </div>
    </div>
  )
}

function TaskHistoryTab({
  articleId,
  createdAt,
  inputType,
}: {
  articleId: string
  createdAt: string
  inputType: string
}) {
  const { data } = useQuery({
    queryKey: ["task-runs", "article", articleId],
    queryFn: () =>
      TaskRunsService.listTaskRuns({ entityId: articleId, limit: 100 }),
  })

  const taskRuns = [...(data?.data ?? [])].sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  )

  return (
    <div className="space-y-0 mt-2">
      {/* Entry node */}
      <div className="flex gap-3">
        <div className="flex flex-col items-center">
          <div className="mt-1">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </div>
          {taskRuns.length > 0 && (
            <div className="w-px flex-1 bg-border mt-1" />
          )}
        </div>
        <div className="pb-4 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">入库</span>
            <Badge variant="outline" className="text-xs">
              {inputType}
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {new Date(createdAt).toLocaleString("zh-CN")}
          </div>
        </div>
      </div>

      {taskRuns.map((run, idx) => (
        <div
          key={run.id}
          className={
            idx === taskRuns.length - 1
              ? "[&>div>div:first-child>div:last-child]:hidden"
              : ""
          }
        >
          <TimelineNode run={run} />
        </div>
      ))}

      {taskRuns.length === 0 && (
        <div className="text-sm text-muted-foreground py-4">暂无任务记录</div>
      )}
    </div>
  )
}

function AnalysisTraceSection({ trace }: { trace: AnalysisTraceStep[] }) {
  if (!trace || trace.length === 0) return null

  return (
    <div className="mt-6">
      <AnalysisTraceTimeline trace={trace} />
    </div>
  )
}

function TokenUsageTab({ articleId }: { articleId: string }) {
  const { data, isLoading } = useArticleTokenUsage(articleId)

  if (isLoading) {
    return <TokenUsageBreakdownSkeleton />
  }

  if (!data || data.operation_count === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Token Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Coins className="h-12 w-12 text-muted-foreground mb-4" />
            <div className="text-muted-foreground">
              No token usage recorded for this article
            </div>
            <div className="text-sm text-muted-foreground">
              Token usage will appear here after processing operations like
              refine or analyze
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Prepare distribution data for pie chart - group by operation
  const operationMap = new Map<string, number>()
  for (const op of data.operations) {
    const current = operationMap.get(op.operation) || 0
    operationMap.set(op.operation, current + op.total_tokens)
  }
  const distributionData = Array.from(operationMap.entries()).map(
    ([name, value]) => ({
      name,
      value,
    }),
  )

  // Prepare model distribution data
  const modelMap = new Map<string, number>()
  for (const op of data.operations) {
    const current = modelMap.get(op.model_name) || 0
    modelMap.set(op.model_name, current + op.total_tokens)
  }
  const modelDistributionData = Array.from(modelMap.entries()).map(
    ([name, value]) => ({
      name,
      value,
    }),
  )

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <TokenDistributionChart
          data={distributionData}
          title="Tokens by Operation"
        />
        <TokenDistributionChart
          data={modelDistributionData}
          title="Tokens by Model"
        />
      </div>
      <TokenUsageBreakdown
        operations={data.operations}
        totalTokens={data.total_tokens}
        totalPromptTokens={data.total_prompt_tokens}
        totalCompletionTokens={data.total_completion_tokens}
        operationCount={data.operation_count}
      />
    </div>
  )
}

function ArticleDetailContent() {
  const { id } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: article } = useSuspenseQuery({
    queryKey: ["article", id],
    queryFn: () => ArticlesService.getArticle({ id }),
  })

  const reAnalyzeMutation = useMutation({
    mutationFn: () =>
      AnalysesService.triggerAnalysis({ requestBody: { article_id: id } }),
    onSuccess: () => {
      showSuccessToast("重新分析已触发")
      queryClient.invalidateQueries({ queryKey: ["article", id] })
    },
    onError: () => showErrorToast("触发失败"),
  })

  const refetchMutation = useMutation({
    mutationFn: () => ArticlesService.refetchArticle({ id }),
    onSuccess: () => {
      showSuccessToast("重新抓取已触发")
      queryClient.invalidateQueries({ queryKey: ["article", id] })
      queryClient.invalidateQueries({ queryKey: ["task-runs", "article", id] })
    },
    onError: () => showErrorToast("触发失败"),
  })

  const triggerWorkflowMutation = useMutation({
    mutationFn: () =>
      WorkflowsService.triggerWorkflow({
        requestBody: {
          type: "writing",
          topic: article?.title || "基于参考素材仿写",
          article_ids: [id],
        },
      }),
    onSuccess: (run) => {
      showSuccessToast("仿写工作流已触发")
      navigate({ to: "/workflow", search: { run_id: run.id } })
    },
    onError: () => showErrorToast("触发失败"),
  })

  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [titleInput, setTitleInput] = useState("")

  const updateTitleMutation = useMutation({
    mutationFn: (title: string) =>
      ArticlesService.updateArticleTitle({ id, requestBody: { title } }),
    onSuccess: () => {
      showSuccessToast("标题已更新")
      queryClient.invalidateQueries({ queryKey: ["article", id] })
      setIsEditingTitle(false)
    },
    onError: () => showErrorToast("更新失败"),
  })

  const analysis = article.analysis as ArticleAnalysisPublic | null | undefined

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={article.status} />
            <span className="text-xs text-muted-foreground uppercase font-mono">
              {article.input_type}
            </span>
          </div>
          {isEditingTitle ? (
            <div className="flex items-center gap-2">
              <input
                className="text-2xl font-bold bg-transparent border-b-2 border-primary outline-none flex-1"
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") updateTitleMutation.mutate(titleInput)
                  if (e.key === "Escape") setIsEditingTitle(false)
                }}
              />
              <button
                type="button"
                onClick={() => updateTitleMutation.mutate(titleInput)}
                disabled={updateTitleMutation.isPending}
                className="text-green-600 hover:text-green-700"
              >
                <Check className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => setIsEditingTitle(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 group">
              <h1 className="text-2xl font-bold">{article.title}</h1>
              <button
                type="button"
                onClick={() => {
                  setTitleInput(article.title)
                  setIsEditingTitle(true)
                }}
                className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground transition-opacity"
              >
                <Pencil className="h-4 w-4" />
              </button>
            </div>
          )}
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-muted-foreground hover:underline"
            >
              {article.url}
            </a>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          {article.url && article.status !== "analyzing" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchMutation.mutate()}
              disabled={refetchMutation.isPending}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              重新抓取
            </Button>
          )}
          {article.status === "analyzed" && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => reAnalyzeMutation.mutate()}
                disabled={reAnalyzeMutation.isPending}
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                重新分析
              </Button>
              <Button
                size="sm"
                onClick={() => triggerWorkflowMutation.mutate()}
                disabled={triggerWorkflowMutation.isPending}
              >
                <Pen className="h-4 w-4 mr-1" />
                触发仿写
              </Button>
            </>
          )}
          {article.status === "analyzing" && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
              <BarChart3 className="h-4 w-4" />
              分析中...
            </div>
          )}
          {article.status === "raw" && (
            <Button
              size="sm"
              onClick={() => reAnalyzeMutation.mutate()}
              disabled={reAnalyzeMutation.isPending}
            >
              <BarChart3 className="h-4 w-4 mr-1" />
              开始分析
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="analysis">
        <TabsList>
          <TabsTrigger value="analysis">
            <BarChart3 className="h-4 w-4 mr-1" />
            分析结果
          </TabsTrigger>
          <TabsTrigger value="token-usage">
            <Coins className="h-4 w-4 mr-1" />
            Token 消耗
          </TabsTrigger>
          <TabsTrigger value="history">
            <History className="h-4 w-4 mr-1" />
            任务历史
          </TabsTrigger>
        </TabsList>

        <TabsContent value="analysis" className="mt-4 space-y-6">
          {/* 分析卡片 — 直接展示 */}
          {analysis && <AnalysisCards analysis={analysis} />}
          {!analysis && article.status === "analyzed" && (
            <div className="text-center py-8 text-muted-foreground">
              分析数据加载中...
            </div>
          )}
          {!analysis && article.status !== "analyzed" && (
            <div className="text-center py-8 text-muted-foreground">
              尚未分析
            </div>
          )}
          <AnalysisTraceSection trace={analysis?.trace ?? []} />

          {/* 精修版 / 原文内容 sub-tabs */}
          <Tabs defaultValue="refined">
            <TabsList className="mb-4">
              <TabsTrigger value="refined">
                <FileText className="h-4 w-4 mr-1" />
                精修版
              </TabsTrigger>
              <TabsTrigger value="raw-content">
                <BookOpen className="h-4 w-4 mr-1" />
                原文内容
              </TabsTrigger>
            </TabsList>

            <TabsContent value="refined">
              {article.content_md ? (
                <div data-color-mode="auto">
                  <MDEditor.Markdown source={article.content_md} />
                </div>
              ) : article.refine_status === "failed" ? (
                <div className="text-center py-8 text-muted-foreground">
                  精修失败，分析已降级使用原文内容
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground animate-pulse">
                  {article.refine_status === "refining"
                    ? "正在精修中..."
                    : "等待精修..."}
                </div>
              )}
            </TabsContent>

            <TabsContent value="raw-content">
              {article.raw_html ? (
                <Card>
                  <CardContent className="pt-4">
                    <iframe
                      srcDoc={article.raw_html}
                      className="w-full h-[600px] border-0"
                      sandbox="allow-same-origin"
                      title="Original Content"
                    />
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground py-8 text-center">
                      暂无原始HTML内容（可能是旧数据或未通过URL抓取）
                    </div>
                    <div
                      className="text-sm leading-relaxed max-h-[600px] overflow-y-auto prose prose-sm max-w-none dark:prose-invert"
                      dangerouslySetInnerHTML={{ __html: article.content ?? "" }}
                    />
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <TaskHistoryTab
            articleId={id}
            createdAt={article.created_at}
            inputType={article.input_type}
          />
        </TabsContent>

        <TabsContent value="token-usage" className="mt-4">
          <TokenUsageTab articleId={id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function ArticleDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-12 text-muted-foreground">
          加载中...
        </div>
      }
    >
      <ArticleDetailContent />
    </Suspense>
  )
}
