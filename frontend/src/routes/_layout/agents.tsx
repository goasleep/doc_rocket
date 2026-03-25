import { zodResolver } from "@hookform/resolvers/zod"
import {
  useMutation,
  useQuery,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Bot, Edit2, Plus, Search, Trash2 } from "lucide-react"
import { Suspense, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type AgentConfigPublic,
  AgentsService,
  LlmModelConfigsService,
  SkillsService,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { StatusBadge } from "@/components/ui/StatusBadge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/agents")({
  component: Agents,
  head: () => ({
    meta: [{ title: "Agent 配置 - 内容引擎" }],
  }),
})

const agentSchema = z.object({
  name: z.string().min(1, "名称不能为空"),
  role: z.enum(["writer", "editor", "reviewer", "orchestrator", "custom"]),
  responsibilities: z.string().min(1, "职责描述不能为空"),
  system_prompt: z.string().min(10, "System Prompt 至少 10 个字符"),
  model_config_name: z.string(),
  workflow_order: z.number().min(0),
  skills: z.array(z.string()),
})

type AgentFormValues = z.infer<typeof agentSchema>

function AgentFormSheet({
  open,
  onOpenChange,
  initialData,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  initialData?: AgentConfigPublic
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const isEdit = !!initialData
  const [skillSearch, setSkillSearch] = useState("")

  const form = useForm<AgentFormValues>({
    resolver: zodResolver(agentSchema),
    defaultValues: initialData
      ? {
          name: initialData.name,
          role: initialData.role as AgentFormValues["role"],
          responsibilities: initialData.responsibilities,
          system_prompt: initialData.system_prompt,
          model_config_name: initialData.model_config_name ?? "",
          workflow_order: initialData.workflow_order,
          skills: initialData.skills ?? [],
        }
      : {
          role: "writer",
          model_config_name: "",
          workflow_order: 0,
          skills: [],
        },
  })

  const selectedSkills = form.watch("skills")

  const { data: skillsData } = useQuery({
    queryKey: ["skills"],
    queryFn: () => SkillsService.listSkills(),
  })

  const { data: modelConfigsData } = useQuery({
    queryKey: ["llm-model-configs"],
    queryFn: () => LlmModelConfigsService.listLlmModelConfigs(),
  })

  const filteredSkills =
    skillsData?.data.filter(
      (s) =>
        s.name.toLowerCase().includes(skillSearch.toLowerCase()) ||
        (s.description ?? "").toLowerCase().includes(skillSearch.toLowerCase()),
    ) ?? []

  const createMutation = useMutation({
    mutationFn: (data: AgentFormValues) =>
      AgentsService.createAgent({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] })
      showSuccessToast("Agent 已创建")
      onOpenChange(false)
    },
    onError: () => showErrorToast("创建失败"),
  })

  const updateMutation = useMutation({
    mutationFn: (data: AgentFormValues) =>
      AgentsService.updateAgent({ id: initialData!.id, requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] })
      showSuccessToast("Agent 已更新")
      onOpenChange(false)
    },
    onError: () => showErrorToast("更新失败"),
  })

  function onSubmit(values: AgentFormValues) {
    if (isEdit) updateMutation.mutate(values)
    else createMutation.mutate(values)
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle>{isEdit ? "编辑 Agent" : "新建 Agent"}</SheetTitle>
        </SheetHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit as any)}
            className="space-y-4 mt-6 pb-6"
          >
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control as any}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>名称</FormLabel>
                    <FormControl>
                      <Input placeholder="Writer Agent" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control as any}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>角色</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="writer">Writer（写作者）</SelectItem>
                        <SelectItem value="editor">Editor（编辑者）</SelectItem>
                        <SelectItem value="reviewer">
                          Reviewer（审核者）
                        </SelectItem>
                        <SelectItem value="orchestrator">
                          Orchestrator（协调者）
                        </SelectItem>
                        <SelectItem value="custom">Custom（自定义）</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control as any}
              name="responsibilities"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>职责描述</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="负责根据素材进行仿写创作..."
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control as any}
              name="system_prompt"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>System Prompt</FormLabel>
                  <FormControl>
                    <textarea
                      className="flex min-h-[160px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-y"
                      placeholder="你是一名专业的内容创作者..."
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control as any}
                name="model_config_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>模型配置</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="选择模型配置..." />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {modelConfigsData?.data
                          .filter((c) => c.is_active && c.api_key_masked)
                          .map((c) => (
                            <SelectItem key={c.id} value={c.name}>
                              {c.name}
                              <span className="text-xs text-muted-foreground ml-1">
                                ({c.model_id})
                              </span>
                            </SelectItem>
                          ))}
                        {(!modelConfigsData ||
                          modelConfigsData.count === 0) && (
                          <SelectItem value="" disabled>
                            请先在"模型配置"页面添加配置
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control as any}
                name="workflow_order"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>执行顺序</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        {...field}
                        onChange={(e) => field.onChange(e.target.valueAsNumber)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Skills selector with search */}
            {skillsData && skillsData.count > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">关联技能</p>
                  {selectedSkills.length > 0 && (
                    <span className="text-xs text-muted-foreground">
                      已选 {selectedSkills.length} 个
                    </span>
                  )}
                </div>
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="搜索技能..."
                    value={skillSearch}
                    onChange={(e) => setSkillSearch(e.target.value)}
                    className="pl-8 h-8 text-sm"
                  />
                </div>
                <div className="rounded-md border max-h-48 overflow-y-auto">
                  {filteredSkills.length === 0 ? (
                    <p className="text-xs text-muted-foreground p-3 text-center">
                      无匹配技能
                    </p>
                  ) : (
                    filteredSkills.map((skill) => (
                      <label
                        key={skill.name}
                        className="flex items-start gap-2.5 px-3 py-2 hover:bg-muted cursor-pointer border-b last:border-b-0"
                      >
                        <Checkbox
                          className="mt-0.5"
                          checked={selectedSkills.includes(skill.name)}
                          onCheckedChange={(checked) => {
                            const current = form.getValues("skills")
                            if (checked) {
                              form.setValue("skills", [...current, skill.name])
                            } else {
                              form.setValue(
                                "skills",
                                current.filter((s) => s !== skill.name),
                              )
                            }
                          }}
                        />
                        <div className="min-w-0">
                          <p className="text-sm font-medium leading-tight">
                            {skill.name}
                          </p>
                          {skill.description && (
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                              {skill.description}
                            </p>
                          )}
                        </div>
                      </label>
                    ))
                  )}
                </div>
              </div>
            )}

            <SheetFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                取消
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? "保存中..." : "保存"}
              </Button>
            </SheetFooter>
          </form>
        </Form>
      </SheetContent>
    </Sheet>
  )
}

function AgentCard({ agent }: { agent: AgentConfigPublic }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [editOpen, setEditOpen] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: () => AgentsService.deleteAgent({ id: agent.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] })
      showSuccessToast("Agent 已删除")
    },
    onError: (err: any) => {
      const detail = err?.body?.detail ?? "删除失败"
      showErrorToast(detail)
    },
  })

  const ROLE_LABEL: Record<string, string> = {
    writer: "Writer",
    editor: "Editor",
    reviewer: "Reviewer",
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
                #{agent.workflow_order} · {ROLE_LABEL[agent.role] ?? agent.role}
                {agent.model_config_name && (
                  <>
                    {" "}
                    ·{" "}
                    <span className="font-mono">{agent.model_config_name}</span>
                  </>
                )}
              </div>
            </div>
            <div className="flex gap-1">
              <Button
                size="icon"
                variant="ghost"
                onClick={() => setEditOpen(true)}
              >
                <Edit2 className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => {
                  if (confirm("确认删除此 Agent？")) deleteMutation.mutate()
                }}
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
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
      <AgentFormSheet
        open={editOpen}
        onOpenChange={setEditOpen}
        initialData={agent}
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
        <p className="text-muted-foreground">创建 Agent 来配置写作流水线</p>
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
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agent 配置</h1>
          <p className="text-muted-foreground">
            配置写作流水线中的 AI Agent 角色
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          新建 Agent
        </Button>
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
      <AgentFormSheet open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
