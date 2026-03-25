import {
  useMutation,
  useQuery,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { BookOpen, FlaskConical, Trash2 } from "lucide-react"
import { Suspense, useState } from "react"

import {
  AnalysesService,
  type ArticlePublic,
  ArticlesService,
  SourcesService,
  WorkflowsService,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { StatusBadge } from "@/components/ui/StatusBadge"
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
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/articles/")({
  component: Articles,
  head: () => ({
    meta: [{ title: "文章库 - 内容引擎" }],
  }),
})

function ArticlesTableContent() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [search, setSearch] = useState("")
  const [filterStatus, setFilterStatus] = useState<string>("all")
  const [filterSource, setFilterSource] = useState<string>("all")

  const { data } = useSuspenseQuery({
    queryKey: ["articles"],
    queryFn: () => ArticlesService.listArticles({ skip: 0, limit: 200 }),
  })

  const { data: sourcesData } = useQuery({
    queryKey: ["sources"],
    queryFn: () => SourcesService.listSources({ skip: 0, limit: 200 }),
  })

  const sourceMap = new Map(sourcesData?.data.map((s) => [s.id, s.name]) ?? [])

  const analyzeMutation = useMutation({
    mutationFn: (articleId: string) =>
      AnalysesService.triggerAnalysis({
        requestBody: { article_id: articleId },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] })
      showSuccessToast("分析任务已触发")
    },
    onError: () => showErrorToast("触发失败"),
  })

  const archiveMutation = useMutation({
    mutationFn: (id: string) => ArticlesService.archiveArticle({ id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles"] })
      showSuccessToast("文章已归档")
    },
    onError: () => showErrorToast("操作失败"),
  })

  const triggerWorkflowMutation = useMutation({
    mutationFn: (articleIds: string[]) =>
      WorkflowsService.triggerWorkflow({
        requestBody: { type: "writing", article_ids: articleIds },
      }),
    onSuccess: (run) => {
      showSuccessToast("仿写工作流已触发")
      navigate({ to: "/workflow", search: { run_id: run.id } })
    },
    onError: () => showErrorToast("触发失败"),
  })

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Filter articles
  const filtered = data.data.filter((a) => {
    if (
      search.trim() &&
      !a.title.toLowerCase().includes(search.trim().toLowerCase())
    )
      return false
    if (filterStatus !== "all" && a.status !== filterStatus) return false
    if (filterSource !== "all") {
      if (filterSource === "manual") {
        if (a.input_type !== "manual") return false
      } else {
        if (a.source_id !== filterSource) return false
      }
    }
    return true
  })

  const toggleAll = () => {
    if (selected.size === filtered.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(filtered.map((a) => a.id)))
    }
  }

  if (data.count === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <BookOpen className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">暂无文章</h3>
        <p className="text-muted-foreground">
          通过订阅源抓取或手动投稿添加文章
        </p>
      </div>
    )
  }

  // Build source options for filter
  const sourceOptions = sourcesData?.data ?? []

  return (
    <div className="space-y-3">
      {/* Search + filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="搜索标题..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 w-56"
        />
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="h-8 w-32">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="raw">待分析</SelectItem>
            <SelectItem value="analyzing">分析中</SelectItem>
            <SelectItem value="analyzed">已分析</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterSource} onValueChange={setFilterSource}>
          <SelectTrigger className="h-8 w-36">
            <SelectValue placeholder="来源" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部来源</SelectItem>
            <SelectItem value="manual">手动投稿</SelectItem>
            {sourceOptions.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {s.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {(search || filterStatus !== "all" || filterSource !== "all") && (
          <span className="text-xs text-muted-foreground">
            共 {filtered.length} 篇
          </span>
        )}
      </div>

      {selected.size > 0 && (
        <div className="flex items-center gap-3 p-3 bg-muted rounded-md">
          <span className="text-sm">已选 {selected.size} 篇</span>
          <Button
            size="sm"
            onClick={() => triggerWorkflowMutation.mutate(Array.from(selected))}
            disabled={triggerWorkflowMutation.isPending}
          >
            触发仿写
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSelected(new Set())}
          >
            取消选择
          </Button>
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">
              <Checkbox
                checked={
                  filtered.length > 0 && selected.size === filtered.length
                }
                onCheckedChange={toggleAll}
              />
            </TableHead>
            <TableHead className="min-w-0">标题</TableHead>
            <TableHead className="w-24 shrink-0">状态</TableHead>
            <TableHead className="w-16 shrink-0">质量分</TableHead>
            <TableHead className="w-28 shrink-0">来源</TableHead>
            <TableHead className="w-36 shrink-0">创建时间</TableHead>
            <TableHead className="w-16 shrink-0">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.length === 0 ? (
            <TableRow>
              <td
                colSpan={7}
                className="text-center py-8 text-sm text-muted-foreground"
              >
                无匹配文章
              </td>
            </TableRow>
          ) : (
            filtered.map((article: ArticlePublic) => (
              <TableRow key={article.id}>
                <TableCell>
                  <Checkbox
                    checked={selected.has(article.id)}
                    onCheckedChange={() => toggleSelect(article.id)}
                  />
                </TableCell>
                <TableCell className="min-w-0">
                  <Link
                    to="/articles/$id"
                    params={{ id: article.id }}
                    className="font-medium hover:underline block truncate max-w-[280px]"
                    title={article.title}
                  >
                    {article.title}
                  </Link>
                </TableCell>
                <TableCell>
                  <StatusBadge status={article.status} />
                </TableCell>
                <TableCell>
                  {article.quality_score != null ? (
                    <span className="font-mono font-semibold">
                      {article.quality_score.toFixed(0)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground text-sm">—</span>
                  )}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground max-w-[112px] truncate">
                  {article.source_id && sourceMap.has(article.source_id)
                    ? sourceMap.get(article.source_id)
                    : article.input_type === "manual"
                      ? "手动投稿"
                      : article.input_type}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                  {new Date(article.created_at).toLocaleString("zh-CN", {
                    year: "numeric",
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    {article.status === "raw" && (
                      <Button
                        size="icon"
                        variant="ghost"
                        title="分析"
                        onClick={() => analyzeMutation.mutate(article.id)}
                        disabled={analyzeMutation.isPending}
                      >
                        <FlaskConical className="h-4 w-4 text-amber-500" />
                      </Button>
                    )}
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => {
                        if (confirm("确认归档此文章？"))
                          archiveMutation.mutate(article.id)
                      }}
                      disabled={archiveMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}

function Articles() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">文章库</h1>
        <p className="text-muted-foreground">AI 分析素材库，按质量评分排序</p>
      </div>
      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">
            加载中...
          </div>
        }
      >
        <ArticlesTableContent />
      </Suspense>
    </div>
  )
}
