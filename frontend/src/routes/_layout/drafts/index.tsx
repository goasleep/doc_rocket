import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { FileText, Trash2 } from "lucide-react"
import { Suspense } from "react"

import { type DraftPublic, DraftsService } from "@/client"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/ui/StatusBadge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/drafts/")({
  component: Drafts,
  head: () => ({
    meta: [{ title: "仿写稿件 - 内容引擎" }],
  }),
})

function DraftsTableContent() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data } = useSuspenseQuery({
    queryKey: ["drafts"],
    queryFn: () => DraftsService.listDrafts({ skip: 0, limit: 100 }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => DraftsService.deleteDraft({ id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drafts"] })
      showSuccessToast("草稿已删除")
    },
    onError: () => showErrorToast("删除失败"),
  })

  if (data.count === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <FileText className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">暂无仿写稿件</h3>
        <p className="text-muted-foreground">
          完成工作流并批准后，稿件将出现在这里
        </p>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>标题</TableHead>
          <TableHead>状态</TableHead>
          <TableHead>创建时间</TableHead>
          <TableHead>编辑历史</TableHead>
          <TableHead>操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.data.map((draft: DraftPublic) => (
          <TableRow key={draft.id}>
            <TableCell>
              <Link
                to="/drafts/$id"
                params={{ id: draft.id }}
                className="font-medium hover:underline"
              >
                {draft.title}
              </Link>
            </TableCell>
            <TableCell>
              <StatusBadge status={draft.status} />
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {new Date(draft.created_at).toLocaleString("zh-CN")}
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {draft.edit_history.length} 次修改
            </TableCell>
            <TableCell>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => {
                  if (confirm("确认删除此草稿？"))
                    deleteMutation.mutate(draft.id)
                }}
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function Drafts() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">仿写稿件</h1>
        <p className="text-muted-foreground">查看和编辑 AI 生成的仿写稿件</p>
      </div>
      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">
            加载中...
          </div>
        }
      >
        <DraftsTableContent />
      </Suspense>
    </div>
  )
}
