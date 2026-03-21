import { useState, useCallback, useEffect, useRef } from "react"
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"
import MDEditor from "@uiw/react-md-editor"
import { Download, CheckCircle, Clock, RotateCcw, X, Check } from "lucide-react"

import { DraftsService, type EditHistoryEntry } from "@/client"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/drafts/$id")({
  component: DraftEditorPage,
  head: () => ({
    meta: [{ title: "草稿编辑 - 内容引擎" }],
  }),
})

// ─── Rewrite Diff Dialog ───────────────────────────────────────────────────────

function RewriteDiffDialog({
  original,
  rewritten,
  onAccept,
  onCancel,
}: {
  original: string
  rewritten: string
  onAccept: (text: string) => void
  onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-background border rounded-lg w-full max-w-3xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">去AI味改写结果</h3>
          <Button size="icon" variant="ghost" onClick={onCancel}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">原文</p>
            <div className="text-sm whitespace-pre-wrap bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 rounded p-3">
              {original}
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">改写后</p>
            <div className="text-sm whitespace-pre-wrap bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900 rounded p-3">
              {rewritten}
            </div>
          </div>
        </div>
        <div className="flex gap-2 justify-end p-4 border-t">
          <Button variant="outline" onClick={onCancel}>取消</Button>
          <Button onClick={() => onAccept(rewritten)}>
            <Check className="h-4 w-4 mr-1" />
            接受改写
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Editor Content ────────────────────────────────────────────────────────────

function DraftEditorContent() {
  const { id } = Route.useParams()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: draft } = useSuspenseQuery({
    queryKey: ["draft", id],
    queryFn: () => DraftsService.getDraft({ id }),
  })

  const [title, setTitle] = useState(draft.title)
  const [content, setContent] = useState(draft.content)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [selectedText, setSelectedText] = useState("")
  const [rewriteResult, setRewriteResult] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const saveMutation = useMutation({
    mutationFn: (data: { title?: string; content?: string }) =>
      DraftsService.updateDraft({ id, requestBody: data }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["draft", id] }),
  })

  const approveMutation = useMutation({
    mutationFn: () => DraftsService.approveDraft({ id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["draft", id] })
      showSuccessToast("草稿已标记为已发布")
    },
    onError: () => showErrorToast("操作失败"),
  })

  const rewriteMutation = useMutation({
    mutationFn: (text: string) =>
      DraftsService.rewriteSection({
        id,
        requestBody: { selected_text: text, context: content.slice(0, 2000) },
      }),
    onSuccess: (result) => setRewriteResult(result.rewritten_text),
    onError: () => showErrorToast("改写失败"),
  })

  // Debounced auto-save (1s)
  const handleContentChange = useCallback(
    (value: string | undefined) => {
      const v = value ?? ""
      setContent(v)
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        saveMutation.mutate({ content: v })
      }, 1000)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [id]
  )

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const handleTitleChange = (t: string) => {
    setTitle(t)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      saveMutation.mutate({ title: t })
    }, 1000)
  }

  const handleExport = () => {
    const blob = new Blob([`# ${title}\n\n${content}`], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `draft_${id.slice(0, 8)}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleRewrite = () => {
    const sel = window.getSelection()?.toString().trim()
    if (!sel) {
      showErrorToast("请先选中要改写的文字")
      return
    }
    setSelectedText(sel)
    rewriteMutation.mutate(sel)
  }

  const handleAcceptRewrite = (text: string) => {
    const newContent = content.replace(selectedText, text)
    setContent(newContent)
    saveMutation.mutate({ content: newContent })
    setRewriteResult(null)
    setSelectedText("")
  }

  const handleRestoreHistory = (entry: EditHistoryEntry) => {
    const newContent = entry.content
    setContent(newContent)
    saveMutation.mutate({ content: newContent })
    setHistoryOpen(false)
    showSuccessToast("已恢复历史版本")
  }

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <input
            type="text"
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            className="text-2xl font-bold w-full bg-transparent border-none outline-none focus:ring-0"
          />
        </div>
        <StatusBadge status={draft.status} />
        <Button size="sm" variant="outline" onClick={handleRewrite} disabled={rewriteMutation.isPending}>
          {rewriteMutation.isPending ? "改写中..." : "✨ 去AI味"}
        </Button>
        <Button size="sm" variant="outline" onClick={handleExport}>
          <Download className="h-4 w-4 mr-1" />
          导出
        </Button>
        {draft.status !== "approved" && (
          <Button size="sm" onClick={() => approveMutation.mutate()} disabled={approveMutation.isPending}>
            <CheckCircle className="h-4 w-4 mr-1" />
            标记为已发布
          </Button>
        )}
        {draft.edit_history.length > 0 && (
          <Button size="sm" variant="outline" onClick={() => setHistoryOpen((v) => !v)}>
            <Clock className="h-4 w-4 mr-1" />
            历史 ({draft.edit_history.length})
          </Button>
        )}
      </div>

      {/* Title candidates */}
      {draft.title_candidates.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-xs text-muted-foreground">候选标题：</span>
          {draft.title_candidates.map((t) => (
            <Badge
              key={t}
              variant="outline"
              className="cursor-pointer hover:bg-muted text-xs"
              onClick={() => handleTitleChange(t)}
            >
              {t}
            </Badge>
          ))}
        </div>
      )}

      <div className="flex flex-1 gap-4 min-h-0">
        {/* Editor */}
        <div className="flex-1 min-w-0" data-color-mode="auto">
          <MDEditor
            value={content}
            onChange={handleContentChange}
            height="100%"
            preview="live"
          />
        </div>

        {/* History sidebar */}
        {historyOpen && (
          <div className="w-64 shrink-0">
            <Card className="h-full overflow-y-auto">
              <CardHeader className="py-3">
                <CardTitle className="text-sm">编辑历史</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 p-3">
                {[...draft.edit_history].reverse().map((entry, i) => (
                  <div key={i} className="border rounded p-2 space-y-1">
                    <div className="text-xs text-muted-foreground">
                      {entry.edited_at
                        ? new Date(entry.edited_at).toLocaleString("zh-CN")
                        : `版本 ${draft.edit_history.length - i}`}
                    </div>
                    {entry.note && (
                      <div className="text-xs italic text-muted-foreground">{entry.note}</div>
                    )}
                    <div className="text-xs text-muted-foreground truncate">
                      {entry.content.slice(0, 80)}...
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full h-6 text-xs"
                      onClick={() => handleRestoreHistory(entry)}
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      恢复
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Rewrite diff dialog */}
      {rewriteResult && (
        <RewriteDiffDialog
          original={selectedText}
          rewritten={rewriteResult}
          onAccept={handleAcceptRewrite}
          onCancel={() => {
            setRewriteResult(null)
            setSelectedText("")
          }}
        />
      )}
    </div>
  )
}

function DraftEditorPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-12 text-muted-foreground">加载中...</div>
      }
    >
      <DraftEditorContent />
    </Suspense>
  )
}
