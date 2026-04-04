import { useMutation, useQuery } from "@tanstack/react-query"
import { ImageIcon, Upload, X } from "lucide-react"
import { useState } from "react"

import { DraftsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"

interface PublishConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: (theme: string) => void
  title: string
  targetName: string
  isLoading: boolean
  draftId: string
  coverImageUrl?: string | null
  onCoverUploaded: (url: string) => void
}

export function PublishConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  targetName,
  isLoading,
  draftId,
  coverImageUrl,
  onCoverUploaded,
}: PublishConfirmDialogProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [dragOver, setDragOver] = useState(false)
  const [selectedTheme, setSelectedTheme] = useState("qing-mo")

  // Fetch available themes
  const { data: themes } = useQuery({
    queryKey: ["draft-themes"],
    queryFn: () => DraftsService.getThemes(),
    enabled: open,
  })

  const uploadCoverMutation = useMutation({
    mutationFn: async (file: File) => {
      return DraftsService.uploadCoverImage({
        id: draftId,
        formData: { file },
      })
    },
    onSuccess: (data) => {
      showSuccessToast("封面上传成功")
      onCoverUploaded(data.cover_image_url)
    },
    onError: (error: any) => {
      showErrorToast(error.body?.detail || "封面上传失败")
    },
  })

  const handleFileSelect = (file: File) => {
    if (!file.type.startsWith("image/")) {
      showErrorToast("请选择图片文件")
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      showErrorToast("图片大小不能超过 10MB")
      return
    }
    uploadCoverMutation.mutate(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelect(file)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => {
    setDragOver(false)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFileSelect(file)
  }

  const hasCover = !!coverImageUrl
  const canPublish = hasCover && !isLoading && !uploadCoverMutation.isPending

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>发布到微信公众号</DialogTitle>
          <DialogDescription>
            确认发布文章到 <strong>{targetName}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Article title */}
          <div className="text-sm">
            <span className="text-muted-foreground">文章标题：</span>
            <span className="font-medium">{title || "（未设置标题）"}</span>
          </div>

          {/* Theme selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">排版主题</label>
            <Select value={selectedTheme} onValueChange={setSelectedTheme}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="选择主题" />
              </SelectTrigger>
              <SelectContent>
                {themes &&
                  Object.entries(themes).map(([key, description]) => (
                    <SelectItem key={key} value={key}>
                      {description as string}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              选择不同的排版主题，预览效果可在发布前查看
            </p>
          </div>

          {/* Cover image upload */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              封面图片 <span className="text-red-500">*</span>
            </label>
            <p className="text-xs text-muted-foreground">
              推荐尺寸 900×500 像素，支持 JPG、PNG、GIF 格式
            </p>

            {hasCover ? (
              <div className="relative w-full aspect-[9/5] rounded-lg overflow-hidden border">
                <img
                  src={coverImageUrl}
                  alt="封面预览"
                  className="w-full h-full object-cover"
                />
                <button
                  type="button"
                  onClick={() => onCoverUploaded("")}
                  className="absolute top-2 right-2 p-1 bg-black/50 hover:bg-black/70 text-white rounded-full"
                  disabled={uploadCoverMutation.isPending || isLoading}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <div
                role="button"
                tabIndex={0}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    document.getElementById("cover-upload")?.click()
                  }
                }}
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors duration-200
                  ${
                    dragOver
                      ? "border-primary bg-primary/5"
                      : "border-muted-foreground/25 hover:border-muted-foreground/50"
                  }
                  ${uploadCoverMutation.isPending ? "opacity-50 pointer-events-none" : ""}
                `}
              >
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleInputChange}
                  className="hidden"
                  id="cover-upload"
                  disabled={uploadCoverMutation.isPending}
                />
                <label htmlFor="cover-upload" className="cursor-pointer">
                  <div className="flex flex-col items-center gap-2">
                    {uploadCoverMutation.isPending ? (
                      <>
                        <div className="h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        <span className="text-sm text-muted-foreground">
                          上传中...
                        </span>
                      </>
                    ) : (
                      <>
                        <ImageIcon className="h-10 w-10 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          点击或拖拽上传封面图片
                        </span>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="mt-2"
                          onClick={(e) => {
                            e.preventDefault()
                            document.getElementById("cover-upload")?.click()
                          }}
                        >
                          <Upload className="h-4 w-4 mr-1" />
                          选择图片
                        </Button>
                      </>
                    )}
                  </div>
                </label>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            取消
          </Button>
          <Button
            onClick={() => onConfirm(selectedTheme)}
            disabled={!canPublish}
            className={!hasCover ? "opacity-50 cursor-not-allowed" : ""}
          >
            {isLoading ? "发布中..." : "确认发布"}
          </Button>
        </DialogFooter>

        {!hasCover && (
          <p className="text-xs text-red-500 text-right">请先上传封面图片</p>
        )}
      </DialogContent>
    </Dialog>
  )
}
