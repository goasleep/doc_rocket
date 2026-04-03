import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface PublishConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  targetName: string
  isLoading: boolean
}

export function PublishConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  targetName,
  isLoading,
}: PublishConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            确认发布到公众号
          </DialogTitle>
          <DialogDescription className="space-y-2 pt-2">
            <p>您即将发布以下内容：</p>
            <div className="rounded bg-muted p-3 text-sm">
              <p className="font-medium">{title || "无标题"}</p>
            </div>
            <p className="text-sm">
              目标公众号：<span className="font-medium">{targetName}</span>
            </p>
            <p className="text-sm text-yellow-600">
              发布后将无法撤回，请确认内容无误。
            </p>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            取消
          </Button>
          <Button onClick={onConfirm} disabled={isLoading}>
            {isLoading ? "发布中..." : "确认发布"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
