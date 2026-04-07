import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ExternalLink, RefreshCw, Search, Trash2 } from "lucide-react"
import { Suspense, useState } from "react"

import {
  type ExternalReferencePublic,
  ExternalReferencesService,
} from "@/client"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/external-references/")({
  component: ExternalReferences,
})

function ExternalReferencesTableContent() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [search, setSearch] = useState("")

  const { data } = useSuspenseQuery({
    queryKey: ["external-references", search],
    queryFn: () =>
      ExternalReferencesService.listExternalReferences({
        skip: 0,
        limit: 100,
        search: search || undefined,
      }),
  })

  const refetchMutation = useMutation({
    mutationFn: (id: string) =>
      ExternalReferencesService.refetchExternalReference({ refId: id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["external-references"] })
      showSuccessToast("重新抓取已触发")
    },
    onError: () => showErrorToast("操作失败"),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      ExternalReferencesService.deleteExternalReference({ refId: id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["external-references"] })
      showSuccessToast("外部参考已删除")
    },
    onError: (error: any) => {
      showErrorToast(error?.body?.detail || "删除失败")
    },
  })

  const refs = data?.data ?? []

  if (refs.length === 0 && !search) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <ExternalLink className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">暂无外部参考</h3>
        <p className="text-muted-foreground">
          外部参考将在文章分析过程中自动收集
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索标题或URL..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        {search && (
          <span className="text-xs text-muted-foreground">
            共 {refs.length} 条
          </span>
        )}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="min-w-0">标题</TableHead>
            <TableHead className="w-24 shrink-0">来源</TableHead>
            <TableHead className="w-32 shrink-0">抓取时间</TableHead>
            <TableHead className="w-16 shrink-0 text-center">引用数</TableHead>
            <TableHead className="w-24 shrink-0">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {refs.length === 0 ? (
            <TableRow>
              <td
                colSpan={5}
                className="text-center py-8 text-sm text-muted-foreground"
              >
                无匹配结果
              </td>
            </TableRow>
          ) : (
            refs.map((ref: ExternalReferencePublic) => (
              <TableRow key={ref.id}>
                <TableCell className="min-w-0">
                  <Link
                    to="/external-references/$id"
                    params={{ id: ref.id }}
                    className="font-medium hover:underline block truncate max-w-[300px]"
                    title={ref.title}
                  >
                    {ref.title}
                  </Link>
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-muted-foreground hover:underline truncate max-w-[300px] block"
                    title={ref.url}
                  >
                    {ref.url}
                  </a>
                </TableCell>
                <TableCell>
                  <span className="text-xs text-muted-foreground">
                    {ref.source || "—"}
                  </span>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                  {ref.fetched_at
                    ? new Date(ref.fetched_at).toLocaleString("zh-CN", {
                        year: "numeric",
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "—"}
                </TableCell>
                <TableCell className="text-center">
                  <span className="text-sm font-medium">
                    {ref.referencer_article_ids?.length || 0}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      title="重新抓取"
                      onClick={() => refetchMutation.mutate(ref.id)}
                      disabled={refetchMutation.isPending}
                    >
                      <RefreshCw className="h-4 w-4 text-muted-foreground" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => {
                        if (confirm("确认删除此外部参考？"))
                          deleteMutation.mutate(ref.id)
                      }}
                      disabled={
                        deleteMutation.isPending ||
                        (ref.referencer_article_ids?.length || 0) > 0
                      }
                      title={
                        (ref.referencer_article_ids?.length || 0) > 0
                          ? "被引用的参考无法删除"
                          : "删除"
                      }
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

function ExternalReferences() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">外部参考</h1>
        <p className="text-muted-foreground">
          文章分析过程中收集的外部参考文章
        </p>
      </div>
      <ErrorBoundary>
        <Suspense
          fallback={
            <div className="flex justify-center py-12 text-muted-foreground">
              加载中...
            </div>
          }
        >
          <ExternalReferencesTableContent />
        </Suspense>
      </ErrorBoundary>
    </div>
  )
}
