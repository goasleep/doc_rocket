import { useMutation, useQuery, useQueryClient, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { Suspense } from "react"
import { BarChart3, BookOpen, Bot, CheckCircle2, Clock, History, RefreshCw, Pen, XCircle } from "lucide-react"

import {
  ArticlesService,
  AnalysesService,
  TaskRunsService,
  WorkflowsService,
  type ArticleAnalysisPublic,
  type TaskRunPublic,
} from "@/client"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/articles/$id")({
  component: ArticleDetailPage,
  head: () => ({
    meta: [{ title: "文章详情 - 内容引擎" }],
  }),
})

function AnalysisCards({ analysis }: { analysis: ArticleAnalysisPublic }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">质量评分</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-4xl font-bold">{analysis.quality_score.toFixed(0)}</div>
          <div className="text-xs text-muted-foreground mt-1">
            深度 {analysis.quality_breakdown?.content_depth?.toFixed(0) ?? "—"} ·
            可读 {analysis.quality_breakdown?.readability?.toFixed(0) ?? "—"} ·
            原创 {analysis.quality_breakdown?.originality?.toFixed(0) ?? "—"} ·
            传播 {analysis.quality_breakdown?.virality_potential?.toFixed(0) ?? "—"}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">钩子 & 框架</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <div><span className="text-xs text-muted-foreground">钩子类型：</span>{analysis.hook_type}</div>
          <div><span className="text-xs text-muted-foreground">写作框架：</span>{analysis.framework}</div>
          <div><span className="text-xs text-muted-foreground">目标受众：</span>{analysis.target_audience}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">情绪触发词</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-1">
            {analysis.emotional_triggers.map((t) => (
              <Badge key={t} variant="secondary">{t}</Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">关键词 & 金句</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-1">
            {analysis.keywords.map((k) => (
              <Badge key={k} variant="outline" className="text-xs">{k}</Badge>
            ))}
          </div>
          <div className="text-xs text-muted-foreground italic">
            {analysis.key_phrases.slice(0, 2).join(" · ")}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">文章结构</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-1">
          <div><span className="text-xs text-muted-foreground">开头：</span>{analysis.structure?.intro}</div>
          <div><span className="text-xs text-muted-foreground">段落数：</span>{analysis.structure?.body_sections?.length ?? 0}</div>
          <div><span className="text-xs text-muted-foreground">结尾：</span>{analysis.structure?.cta}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">写作风格</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-1">
          <div><span className="text-xs text-muted-foreground">语气：</span>{analysis.style?.tone}</div>
          <div><span className="text-xs text-muted-foreground">正式程度：</span>{analysis.style?.formality}</div>
          <div><span className="text-xs text-muted-foreground">平均句长：</span>{analysis.style?.avg_sentence_length}</div>
        </CardContent>
      </Card>
    </div>
  )
}

function TriggeredByBadge({ triggeredBy, label }: { triggeredBy: string; label?: string | null }) {
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
      <Badge variant="outline" className="gap-1 text-xs border-blue-400 text-blue-600">
        <Bot className="h-3 w-3" />
        Agent{label ? ` · ${label}` : ""}
      </Badge>
    )
  }
  return <Badge variant="secondary" className="text-xs">手动</Badge>
}

function formatDuration(startedAt?: string | null, endedAt?: string | null) {
  if (!startedAt || !endedAt) return null
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime()
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m${Math.floor((ms % 60000) / 1000)}s`
}

function TimelineNode({ run }: { run: TaskRunPublic }) {
  const typeLabels: Record<string, string> = { analyze: "分析", fetch: "抓取", workflow: "仿写" }
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
          <span className="font-medium text-sm">{typeLabels[run.task_type] ?? run.task_type}任务</span>
          <TriggeredByBadge triggeredBy={run.triggered_by} label={run.triggered_by_label} />
          {run.status === "done" && <Badge className="bg-green-500 hover:bg-green-600 text-xs">完成</Badge>}
          {run.status === "failed" && <Badge variant="destructive" className="text-xs">失败</Badge>}
          {run.status === "running" && <Badge className="bg-blue-500 hover:bg-blue-600 text-xs animate-pulse">运行中</Badge>}
          {run.status === "pending" && <Badge variant="secondary" className="text-xs">待处理</Badge>}
          {duration && <span className="text-xs text-muted-foreground">{duration}</span>}
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

function TaskHistoryTab({ articleId, createdAt, inputType }: { articleId: string; createdAt: string; inputType: string }) {
  const { data } = useQuery({
    queryKey: ["task-runs", "article", articleId],
    queryFn: () => TaskRunsService.listTaskRuns({ entityId: articleId, limit: 100 }),
  })

  const taskRuns = [...(data?.data ?? [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )

  return (
    <div className="space-y-0 mt-2">
      {/* Entry node */}
      <div className="flex gap-3">
        <div className="flex flex-col items-center">
          <div className="mt-1">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </div>
          {taskRuns.length > 0 && <div className="w-px flex-1 bg-border mt-1" />}
        </div>
        <div className="pb-4 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">入库</span>
            <Badge variant="outline" className="text-xs">{inputType}</Badge>
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {new Date(createdAt).toLocaleString("zh-CN")}
          </div>
        </div>
      </div>

      {taskRuns.map((run, idx) => (
        <div key={run.id} className={idx === taskRuns.length - 1 ? "[&>div>div:first-child>div:last-child]:hidden" : ""}>
          <TimelineNode run={run} />
        </div>
      ))}

      {taskRuns.length === 0 && (
        <div className="text-sm text-muted-foreground py-4">暂无任务记录</div>
      )}
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
    mutationFn: () => AnalysesService.triggerAnalysis({ requestBody: { article_id: id } }),
    onSuccess: () => {
      showSuccessToast("重新分析已触发")
      queryClient.invalidateQueries({ queryKey: ["article", id] })
    },
    onError: () => showErrorToast("触发失败"),
  })

  const triggerWorkflowMutation = useMutation({
    mutationFn: () =>
      WorkflowsService.triggerWorkflow({
        requestBody: { type: "writing", article_ids: [id] },
      }),
    onSuccess: (run) => {
      showSuccessToast("仿写工作流已触发")
      navigate({ to: "/workflow", search: { run_id: run.id } })
    },
    onError: () => showErrorToast("触发失败"),
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
          <h1 className="text-2xl font-bold">{article.title}</h1>
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
          <TabsTrigger value="history">
            <History className="h-4 w-4 mr-1" />
            任务历史
          </TabsTrigger>
        </TabsList>

        <TabsContent value="analysis" className="mt-4">
          {analysis && <AnalysisCards analysis={analysis} />}
          {!analysis && article.status === "analyzed" && (
            <div className="text-center py-8 text-muted-foreground">分析数据加载中...</div>
          )}
          {!analysis && article.status !== "analyzed" && (
            <div className="text-center py-8 text-muted-foreground">尚未分析</div>
          )}

          {/* Article content */}
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BookOpen className="h-4 w-4" />
                原文内容
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="whitespace-pre-wrap text-sm leading-relaxed max-h-[600px] overflow-y-auto">
                {article.content}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <TaskHistoryTab
            articleId={id}
            createdAt={article.created_at}
            inputType={article.input_type}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function ArticleDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-12 text-muted-foreground">加载中...</div>
      }
    >
      <ArticleDetailContent />
    </Suspense>
  )
}
