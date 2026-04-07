import {
  useMutation,
  useQuery,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import MDEditor from "@uiw/react-md-editor"
import {
  Check,
  CheckCircle,
  ChevronDown,
  Clock,
  Download,
  RotateCcw,
  X,
} from "lucide-react"
import { marked } from "marked"
import { Suspense, useCallback, useEffect, useRef, useState } from "react"

import {
  DraftsService,
  type EditHistoryEntry,
  SystemConfigService,
} from "@/client"
import { PublishConfirmDialog } from "@/components/DraftEditor/PublishConfirmDialog"
import { WeChatPreviewModal } from "@/components/DraftEditor/WeChatPreviewModal"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/StatusBadge"
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
            <p className="text-xs font-medium text-muted-foreground mb-2">
              原文
            </p>
            <div className="text-sm whitespace-pre-wrap bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 rounded p-3">
              {original}
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              改写后
            </p>
            <div className="text-sm whitespace-pre-wrap bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900 rounded p-3">
              {rewritten}
            </div>
          </div>
        </div>
        <div className="flex gap-2 justify-end p-4 border-t">
          <Button variant="outline" onClick={onCancel}>
            取消
          </Button>
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

  const { data: systemConfig } = useQuery({
    queryKey: ["system-config"],
    queryFn: () => SystemConfigService.getSystemConfig(),
  })

  const [title, setTitle] = useState(draft.title)
  const [content, setContent] = useState(draft.content)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [selectedText, setSelectedText] = useState("")
  const [rewriteResult, setRewriteResult] = useState<string | null>(null)
  const [contextMenuPos, setContextMenuPos] = useState<{
    x: number
    y: number
  } | null>(null)
  const [pendingSelection, setPendingSelection] = useState("")
  const [exportMenuOpen, setExportMenuOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewData, setPreviewData] = useState<{
    title: string
    html_content: string
  } | null>(null)
  const [publishOpen, setPublishOpen] = useState(false)
  const [isPublishing, setIsPublishing] = useState(false)
  const [coverImageUrl, setCoverImageUrl] = useState(
    draft.cover_image_url || "",
  )
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const contextMenuRef = useRef<HTMLDivElement | null>(null)
  const exportMenuRef = useRef<HTMLDivElement | null>(null)

  // Sync cover image when draft data changes
  useEffect(() => {
    setCoverImageUrl(draft.cover_image_url || "")
  }, [draft.cover_image_url])

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
    onMutate: () => {
      // Loading state is handled by button disabled state
    },
    onSuccess: (result) => {
      setRewriteResult(result.rewritten_text)
      showSuccessToast("改写完成，请查看右侧结果")
    },
    onError: () => showErrorToast("改写失败，请重试"),
  })

  const uploadImageMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      const response = await fetch("/api/v1/uploads/image", {
        method: "POST",
        body: formData,
      })
      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: "上传失败" }))
        throw new Error(errorData.detail || "上传失败")
      }
      return response.json() as Promise<{ url: string }>
    },
    onError: () => showErrorToast("图片上传失败"),
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
    [saveMutation.mutate],
  )

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  // Close context menu on outside click
  useEffect(() => {
    if (!contextMenuPos) return
    const handler = (e: MouseEvent) => {
      if (
        contextMenuRef.current &&
        !contextMenuRef.current.contains(e.target as Node)
      ) {
        setContextMenuPos(null)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [contextMenuPos])

  // Close export menu on outside click
  useEffect(() => {
    if (!exportMenuOpen) return
    const handler = (e: MouseEvent) => {
      if (
        exportMenuRef.current &&
        !exportMenuRef.current.contains(e.target as Node)
      ) {
        setExportMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [exportMenuOpen])

  const handleTitleChange = (t: string) => {
    setTitle(t)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      saveMutation.mutate({ title: t })
    }, 1000)
  }

  const insertImageToMarkdown = (url: string) => {
    const imageMarkdown = `\n![图片](${url})\n`
    const newContent = content + imageMarkdown
    setContent(newContent)
    saveMutation.mutate({ content: newContent })
  }

  const handleImageUpload = async (file: File) => {
    if (!file.type.startsWith("image/")) return
    try {
      const result = await uploadImageMutation.mutateAsync(file)
      insertImageToMarkdown(result.url)
      showSuccessToast("图片上传成功")
    } catch {
      // error handled by mutation onError
    }
  }

  const handlePaste = (event: React.ClipboardEvent) => {
    const files = Array.from(event.clipboardData.files)
    const imageFile = files.find((f) => f.type.startsWith("image/"))
    if (imageFile) {
      event.preventDefault()
      handleImageUpload(imageFile)
    }
  }

  const handleDrop = (event: React.DragEvent) => {
    const files = Array.from(event.dataTransfer.files)
    const imageFile = files.find((f) => f.type.startsWith("image/"))
    if (imageFile) {
      event.preventDefault()
      handleImageUpload(imageFile)
    }
  }

  const handleExportMd = () => {
    const blob = new Blob([`# ${title}\n\n${content}`], {
      type: "text/markdown",
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${title || "draft"}.md`
    a.click()
    URL.revokeObjectURL(url)
    setExportMenuOpen(false)
  }

  const handleExportPdf = async () => {
    setExportMenuOpen(false)
    const htmlBody = await marked.parse(content)
    const fullHtml = `<!DOCTYPE html><html><head><meta charset="utf-8">
<title>${title}</title>
<style>
body{font-family:sans-serif;max-width:800px;margin:40px auto;line-height:1.6;color:#222}
h1,h2,h3,h4{margin-top:1.5em}
pre{background:#f5f5f5;padding:1em;overflow:auto;border-radius:4px}
code{background:#f5f5f5;padding:.2em .4em;border-radius:2px}
blockquote{border-left:4px solid #ddd;padding-left:1em;color:#666;margin-left:0}
img{max-width:100%}
</style></head><body>${htmlBody}</body></html>`
    const iframe = document.createElement("iframe")
    iframe.style.cssText =
      "position:fixed;top:-9999px;left:-9999px;width:800px;height:600px"
    document.body.appendChild(iframe)
    iframe.contentDocument!.write(fullHtml)
    iframe.contentDocument!.close()
    iframe.contentWindow!.focus()
    iframe.contentWindow!.print()
    setTimeout(() => document.body.removeChild(iframe), 2000)
  }

  const handleContextMenu = (e: React.MouseEvent) => {
    const sel = window.getSelection()?.toString().trim()
    if (!sel) return
    e.preventDefault()
    setPendingSelection(sel)
    setContextMenuPos({ x: e.clientX, y: e.clientY })
  }

  const handleContextRewrite = () => {
    if (!pendingSelection) return
    setSelectedText(pendingSelection)
    rewriteMutation.mutate(pendingSelection)
    setContextMenuPos(null)
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

  const handlePreview = async () => {
    if (!draft) return
    try {
      const response = await DraftsService.previewDraft({ id })
      setPreviewData(response)
      setPreviewOpen(true)
    } catch (_error) {
      showErrorToast("预览生成失败")
    }
  }

  const handlePublishClick = () => {
    if (!systemConfig?.wechat_mp?.enabled) {
      showErrorToast("请先配置微信公众号")
      return
    }
    setPublishOpen(true)
  }

  const handlePublish = async (theme: string = "qing-mo") => {
    if (!draft) return
    setIsPublishing(true)
    try {
      const response = await DraftsService.publishDraft({
        id,
        requestBody: { confirmed: true, theme },
      })
      showSuccessToast(response.message || "发布成功")
      setPublishOpen(false)
    } catch (error: any) {
      showErrorToast(error.body?.detail || "发布失败")
    } finally {
      setIsPublishing(false)
    }
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
        <div className="relative" ref={exportMenuRef}>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setExportMenuOpen((v) => !v)}
          >
            <Download className="h-4 w-4 mr-1" />
            导出
            <ChevronDown className="h-3 w-3 ml-1" />
          </Button>
          {exportMenuOpen && (
            <div className="absolute right-0 top-full mt-1 z-50 bg-background border rounded shadow-md min-w-[140px]">
              <button
                type="button"
                className="w-full text-left px-3 py-2 text-sm hover:bg-muted"
                onClick={handleExportMd}
              >
                导出 Markdown
              </button>
              <button
                type="button"
                className="w-full text-left px-3 py-2 text-sm hover:bg-muted"
                onClick={handleExportPdf}
              >
                导出 PDF
              </button>
            </div>
          )}
        </div>
        {draft.status !== "approved" && (
          <Button
            size="sm"
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending}
          >
            <CheckCircle className="h-4 w-4 mr-1" />
            标记为已发布
          </Button>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={handlePreview}
          disabled={!draft?.content}
        >
          预览
        </Button>
        <Button
          variant="default"
          size="sm"
          onClick={handlePublishClick}
          disabled={!draft?.content || draft?.status !== "approved"}
        >
          发布到公众号
        </Button>
        {draft.edit_history.length > 0 && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setHistoryOpen((v) => !v)}
          >
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
        {/* biome-ignore lint/a11y/noStaticElementInteractions: context menu on editor wrapper */}
        <div
          className="flex-1 min-w-0"
          data-color-mode="auto"
          onContextMenu={handleContextMenu}
          onPaste={handlePaste}
          onDrop={handleDrop}
        >
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
                      <div className="text-xs italic text-muted-foreground">
                        {entry.note}
                      </div>
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

      {/* Right-click context menu */}
      {contextMenuPos && (
        <div
          ref={contextMenuRef}
          className="fixed z-50 bg-background border rounded shadow-lg py-1 min-w-[140px]"
          style={{ top: contextMenuPos.y, left: contextMenuPos.x }}
        >
          <button
            type="button"
            className="w-full text-left px-3 py-2 text-sm hover:bg-muted flex items-center gap-2"
            onClick={handleContextRewrite}
            disabled={rewriteMutation.isPending}
          >
            {rewriteMutation.isPending ? "改写中..." : "✨ 去AI味改写"}
          </button>
          <button
            type="button"
            className="w-full text-left px-3 py-2 text-sm hover:bg-muted text-muted-foreground"
            onClick={() => setContextMenuPos(null)}
          >
            取消
          </button>
        </div>
      )}

      {/* WeChat Preview Modal */}
      {previewData && (
        <WeChatPreviewModal
          open={previewOpen}
          onClose={() => setPreviewOpen(false)}
          title={previewData.title}
          htmlContent={previewData.html_content}
        />
      )}

      {/* Publish Confirm Dialog */}
      <PublishConfirmDialog
        open={publishOpen}
        onClose={() => setPublishOpen(false)}
        onConfirm={handlePublish}
        title={draft?.title || ""}
        targetName={systemConfig?.wechat_mp?.app_id || "微信公众号"}
        isLoading={isPublishing}
        draftId={id}
        coverImageUrl={coverImageUrl}
        onCoverUploaded={setCoverImageUrl}
      />
    </div>
  )
}

function DraftEditorPage() {
  return (
    <ErrorBoundary>
      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">
            加载中...
          </div>
        }
      >
        <DraftEditorContent />
      </Suspense>
    </ErrorBoundary>
  )
}
