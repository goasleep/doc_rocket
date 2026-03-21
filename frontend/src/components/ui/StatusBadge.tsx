import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type StatusVariant = "default" | "secondary" | "destructive" | "outline"

interface StatusConfig {
  label: string
  variant: StatusVariant
  className?: string
}

const STATUS_MAP: Record<string, StatusConfig> = {
  // Article statuses
  raw: { label: "待分析", variant: "secondary" },
  analyzing: { label: "分析中", variant: "default", className: "animate-pulse" },
  analyzed: { label: "已分析", variant: "outline", className: "border-green-500 text-green-600" },
  archived: { label: "已归档", variant: "secondary", className: "opacity-60" },

  // Workflow statuses
  pending: { label: "待处理", variant: "secondary" },
  running: { label: "运行中", variant: "default", className: "animate-pulse" },
  waiting_human: { label: "待审核", variant: "outline", className: "border-amber-500 text-amber-600" },
  done: { label: "完成", variant: "outline", className: "border-green-500 text-green-600" },
  failed: { label: "失败", variant: "destructive" },

  // Draft statuses
  draft: { label: "草稿", variant: "secondary" },
  editing: { label: "编辑中", variant: "default" },
  approved: { label: "已发布", variant: "outline", className: "border-green-500 text-green-600" },

  // Source active state
  active: { label: "活跃", variant: "outline", className: "border-green-500 text-green-600" },
  inactive: { label: "停用", variant: "secondary", className: "opacity-60" },
}

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_MAP[status] ?? { label: status, variant: "secondary" as StatusVariant }

  return (
    <Badge
      variant={config.variant}
      className={cn(config.className, className)}
    >
      {config.label}
    </Badge>
  )
}
