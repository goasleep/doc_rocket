import { createFileRoute } from "@tanstack/react-router"
import { useSuspenseQuery } from "@tanstack/react-query"
import { Bot, Eye } from "lucide-react"
import { Suspense, useState } from "react"

import { type AgentConfigPublic, AgentsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { StatusBadge } from "@/components/ui/StatusBadge"
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

export const Route = createFileRoute("/_layout/agents")({
  component: Agents,
  head: () => ({
    meta: [{ title: "Agent 配置 - 内容引擎" }],
  }),
})

function AgentDetailSheet({
  open,
  onOpenChange,
  agent,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  agent?: AgentConfigPublic
}) {
  if (!agent) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle>{agent.name}</SheetTitle>
        </SheetHeader>
        <div className="space-y-4 mt-6 pb-6">
          <div>
            <p className="text-sm font-medium">角色</p>
            <p className="text-sm text-muted-foreground">{agent.role}</p>
          </div>
          <div>
            <p className="text-sm font-medium">职责描述</p>
            <p className="text-sm text-muted-foreground">{agent.responsibilities}</p>
          </div>
          <div>
            <p className="text-sm font-medium">模型配置</p>
            <p className="text-sm text-muted-foreground">
              {agent.model_config_name || "未配置"}
            </p>
          </div>
          {agent.skills && agent.skills.length > 0 && (
            <div>
              <p className="text-sm font-medium">关联技能</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {agent.skills.map((s) => (
                  <Badge key={s} variant="secondary" className="text-xs">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          <div>
            <p className="text-sm font-medium">System Prompt</p>
            <textarea
              readOnly
              className="flex min-h-[200px] w-full rounded-md border border-input bg-muted px-3 py-2 text-sm font-mono ring-offset-background resize-y mt-1"
              value={agent.system_prompt}
            />
          </div>
          <SheetFooter className="pt-2">
            <Button type="button" onClick={() => onOpenChange(false)}>
              关闭
            </Button>
          </SheetFooter>
        </div>
      </SheetContent>
    </Sheet>
  )
}

function AgentCard({ agent }: { agent: AgentConfigPublic }) {
  const [detailOpen, setDetailOpen] = useState(false)

  const ROLE_LABEL: Record<string, string> = {
    writer: "Writer",
    editor: "Editor",
    reviewer: "Reviewer",
    analyzer: "Analyzer",
    refiner: "Refiner",
    orchestrator: "Orchestrator",
    custom: "Custom",
  }

  return (
    <>
      <Card>
        <CardContent className="pt-4 space-y-3">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold">{agent.name}</span>
                <StatusBadge status={agent.is_active ? "active" : "inactive"} />
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                {ROLE_LABEL[agent.role] ?? agent.role}
                {agent.model_config_name && (
                  <>
                    {" "}
                    ·{" "}
                    <span className="font-mono">{agent.model_config_name}</span>
                  </>
                )}
              </div>
            </div>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setDetailOpen(true)}
            >
              <Eye className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">
            {agent.responsibilities}
          </p>
          {agent.skills && agent.skills.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {agent.skills.map((s) => (
                <Badge key={s} variant="secondary" className="text-xs">
                  {s}
                </Badge>
              ))}
            </div>
          )}
          <div className="text-xs bg-muted p-2 rounded font-mono truncate">
            {agent.system_prompt.slice(0, 100)}
            {agent.system_prompt.length > 100 && "..."}
          </div>
        </CardContent>
      </Card>
      <AgentDetailSheet
        open={detailOpen}
        onOpenChange={setDetailOpen}
        agent={agent}
      />
    </>
  )
}

function AgentsContent() {
  const { data } = useSuspenseQuery({
    queryKey: ["agents"],
    queryFn: () => AgentsService.listAgents(),
  })

  if (data.count === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Bot className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">暂无 Agent</h3>
        <p className="text-muted-foreground">系统启动后会自动初始化 Agent 配置</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {data.data.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  )
}

function Agents() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agent 配置</h1>
          <p className="text-muted-foreground">
            查看写作流水线中的 AI Agent 角色配置（提示词由代码统一管理）
          </p>
        </div>
      </div>

      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">
            加载中...
          </div>
        }
      >
        <AgentsContent />
      </Suspense>
    </div>
  )
}
