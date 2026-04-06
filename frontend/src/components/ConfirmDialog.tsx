import { useCallback, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export interface ConfirmDialogOptions {
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: "default" | "destructive"
}

export function useConfirmDialog() {
  const [isOpen, setIsOpen] = useState(false)
  const [options, setOptions] = useState<ConfirmDialogOptions>({})
  const [resolveRef, setResolveRef] = useState<{
    resolve: (value: boolean) => void
  } | null>(null)

  const confirm = useCallback(
    (opts: ConfirmDialogOptions = {}) =>
      new Promise<boolean>((resolve) => {
        setOptions(opts)
        setResolveRef({ resolve })
        setIsOpen(true)
      }),
    [],
  )

  const handleClose = useCallback(
    (value: boolean) => {
      setIsOpen(false)
      resolveRef?.resolve(value)
      setResolveRef(null)
    },
    [resolveRef],
  )

  const ConfirmDialog = useCallback(
    () => (
      <Dialog
        open={isOpen}
        onOpenChange={(open) => !open && handleClose(false)}
      >
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>{options.title ?? "确认操作"}</DialogTitle>
            {options.description && (
              <DialogDescription>{options.description}</DialogDescription>
            )}
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleClose(false)}
            >
              {options.cancelText ?? "取消"}
            </Button>
            <Button
              type="button"
              variant={
                options.variant === "destructive" ? "destructive" : "default"
              }
              onClick={() => handleClose(true)}
            >
              {options.confirmText ?? "确认"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    ),
    [handleClose, isOpen, options],
  )

  return { confirm, ConfirmDialog }
}
