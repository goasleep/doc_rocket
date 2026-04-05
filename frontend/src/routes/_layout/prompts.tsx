import { createFileRoute } from "@tanstack/react-router"
import { useSuspenseQuery } from "@tanstack/react-query"
import { FileCode } from "lucide-react"
import { Suspense } from "react"

import { type AgentConfigPublic, AgentsService } from "@/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/_layout/prompts")({
  component: Prompts,
  head: () => ({
    meta: [{ title: "Prompt 模板 - 内容引擎" }],
  }),
})

const ROLE_LABEL: Record<string, string> = {
  writer: "Writer",
  editor: "Editor",
  reviewer: "Reviewer",
  custom: "Custom",
}

const ROLE_COLOR: Record<string, string> = {
  writer: "bg-blue-100 text-blue-700",
  editor: "bg-green-100 text-green-700",
  reviewer: "bg-orange-100 text-orange-700",
  custom: "bg-gray-100 text-gray-700",
}

function PromptCard({ agent }: { agent: AgentConfigPublic }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">{agent.name}</CardTitle>
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_COLOR[agent.role] ?? ROLE_COLOR.custom}`}
            >
              {ROLE_LABEL[agent.role] ?? agent.role}
            </span>
          </div>
        </div>
        {agent.responsibilities && (
          <p className="text-xs text-muted-foreground mt-1">
            {agent.responsibilities}
          </p>
        )}
      </CardHeader>
      <CardContent>
        <textarea
          readOnly
          className="flex min-h-[220px] w-full rounded-md border border-input bg-muted px-3 py-2 text-sm font-mono ring-offset-background resize-y"
          value={agent.system_prompt}
        />
      </CardContent>
    </Card>
  )
}

function PromptsContent() {
  const { data } = useSuspenseQuery({
    queryKey: ["agents"],
    queryFn: () => AgentsService.listAgents(),
  })

  if (data.count === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <FileCode className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">暂无 Agent 配置</h3>
        <p className="text-muted-foreground">
          系统启动后会自动初始化 Agent 配置
        </p>
      </div>
    )
  }

  // Sort by role: writer -> editor -> reviewer -> others
  const roleOrder: Record<string, number> = {
    writer: 0,
    editor: 1,
    reviewer: 2,
  }
  const sorted = [...data.data].sort((a, b) => {
    const orderA = roleOrder[a.role] ?? 999
    const orderB = roleOrder[b.role] ?? 999
    return orderA - orderB
  })

  return (
    <div className="flex flex-col gap-4">
      {sorted.map((agent) => (
        <PromptCard key={agent.id} agent={agent} />
      ))}
    </div>
  )
}

function Prompts() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Prompt 模板</h1>
        <p className="text-muted-foreground">
          查看各 Agent 的 System Prompt（由代码统一管理，不可编辑）
        </p>
      </div>
      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">
            加载中...
          </div>
        }
      >
        <PromptsContent />
      </Suspense>
    </div>
  )
}
