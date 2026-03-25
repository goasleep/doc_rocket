import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Edit2, KeyRound, Plus, Trash2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type LLMModelConfigPublic, LlmModelConfigsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/llm-models")({
  component: LLMModels,
  head: () => ({
    meta: [{ title: "模型配置 - 内容引擎" }],
  }),
})

const modelSchema = z.object({
  name: z.string().min(1, "名称不能为空"),
  provider_type: z.enum(["openai_compatible", "kimi"]),
  base_url: z.string().optional(),
  api_key: z.string().optional(),
  model_id: z.string().min(1, "模型 ID 不能为空"),
  is_active: z.boolean(),
})

type ModelFormValues = z.infer<typeof modelSchema>

const PROVIDER_LABELS: Record<string, string> = {
  kimi: "Kimi (Moonshot)",
  openai_compatible: "OpenAI 兼容",
}

function ModelFormDialog({
  open,
  onOpenChange,
  initialData,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  initialData?: LLMModelConfigPublic
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const isEdit = !!initialData

  const form = useForm<ModelFormValues>({
    resolver: zodResolver(modelSchema),
    defaultValues: initialData
      ? {
          name: initialData.name,
          provider_type:
            initialData.provider_type as ModelFormValues["provider_type"],
          base_url: initialData.base_url ?? "",
          api_key: "",
          model_id: initialData.model_id,
          is_active: initialData.is_active,
        }
      : {
          provider_type: "kimi",
          base_url: "",
          api_key: "",
          model_id: "",
          is_active: true,
        },
  })

  const providerType = form.watch("provider_type")

  const createMutation = useMutation({
    mutationFn: (data: ModelFormValues) =>
      LlmModelConfigsService.createLlmModelConfig({
        requestBody: {
          name: data.name,
          provider_type: data.provider_type,
          base_url: data.base_url || null,
          api_key: data.api_key || null,
          model_id: data.model_id,
          is_active: data.is_active,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-model-configs"] })
      showSuccessToast("模型配置已创建")
      onOpenChange(false)
    },
    onError: (err: any) => {
      showErrorToast(err?.body?.detail ?? "创建失败")
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: ModelFormValues) =>
      LlmModelConfigsService.updateLlmModelConfig({
        id: initialData!.id,
        requestBody: {
          name: data.name,
          provider_type: data.provider_type,
          base_url: data.base_url || null,
          api_key: data.api_key || undefined,
          model_id: data.model_id,
          is_active: data.is_active,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-model-configs"] })
      showSuccessToast("模型配置已更新")
      onOpenChange(false)
    },
    onError: (err: any) => {
      showErrorToast(err?.body?.detail ?? "更新失败")
    },
  })

  function onSubmit(values: ModelFormValues) {
    if (isEdit) updateMutation.mutate(values)
    else createMutation.mutate(values)
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑模型配置" : "新建模型配置"}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit as any)}
            className="space-y-4"
          >
            <FormField
              control={form.control as any}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>配置名称</FormLabel>
                  <FormControl>
                    <Input placeholder="如：Moonshot-32k、GPT-4o" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control as any}
              name="provider_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>类型</FormLabel>
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
                      <SelectItem value="kimi">Kimi (Moonshot)</SelectItem>
                      <SelectItem value="openai_compatible">
                        OpenAI 兼容格式
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {providerType === "openai_compatible" && (
              <FormField
                control={form.control as any}
                name="base_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Base URL</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="https://api.openai.com/v1"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <FormField
              control={form.control as any}
              name="model_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>模型 ID</FormLabel>
                  <FormControl>
                    <Input
                      placeholder={
                        providerType === "kimi" ? "moonshot-v1-32k" : "gpt-4o"
                      }
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control as any}
              name="api_key"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    API Key
                    {isEdit && (
                      <span className="text-xs text-muted-foreground ml-2">
                        （留空保留原有 Key）
                      </span>
                    )}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      placeholder={
                        isEdit
                          ? (initialData?.api_key_masked ?? "输入新 Key 以替换")
                          : "sk-..."
                      }
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
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
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function LLMModels() {
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<LLMModelConfigPublic | null>(
    null,
  )
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { user } = useAuth()
  const isSuperuser = user?.is_superuser ?? false

  const { data, isLoading } = useQuery({
    queryKey: ["llm-model-configs"],
    queryFn: () => LlmModelConfigsService.listLlmModelConfigs(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      LlmModelConfigsService.deleteLlmModelConfig({ id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-model-configs"] })
      showSuccessToast("模型配置已删除")
    },
    onError: (err: any) => {
      showErrorToast(err?.body?.detail ?? "删除失败")
    },
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      Promise.all(
        ids.map((id) => LlmModelConfigsService.deleteLlmModelConfig({ id })),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-model-configs"] })
      showSuccessToast(`已删除 ${selected.size} 个配置`)
      setSelected(new Set())
    },
    onError: () => showErrorToast("批量删除失败"),
  })

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (!data) return
    if (selected.size === data.data.length) setSelected(new Set())
    else setSelected(new Set(data.data.map((c) => c.id)))
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">模型配置</h1>
          <p className="text-muted-foreground">
            管理 LLM API Key 和模型参数，Agent 通过配置名称引用
          </p>
        </div>
        {isSuperuser && (
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            新建配置
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="text-muted-foreground text-sm">加载中...</div>
      ) : !data || data.count === 0 ? (
        <div className="flex flex-col items-center justify-center text-center py-12">
          <div className="rounded-full bg-muted p-4 mb-4">
            <KeyRound className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">暂无模型配置</h3>
          <p className="text-muted-foreground">
            {isSuperuser
              ? "点击右上角「新建配置」添加第一个模型"
              : "请联系管理员添加模型配置"}
          </p>
        </div>
      ) : (
        <>
          {isSuperuser && selected.size > 0 && (
            <div className="flex items-center gap-3 p-3 bg-muted rounded-md">
              <span className="text-sm">已选 {selected.size} 个</span>
              <Button
                size="sm"
                variant="destructive"
                disabled={bulkDeleteMutation.isPending}
                onClick={() => {
                  if (confirm(`确认删除选中的 ${selected.size} 个配置？`))
                    bulkDeleteMutation.mutate(Array.from(selected))
                }}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                批量删除
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelected(new Set())}
              >
                取消选择
              </Button>
            </div>
          )}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  {isSuperuser && (
                    <TableHead className="w-10">
                      <Checkbox
                        checked={
                          data.data.length > 0 &&
                          selected.size === data.data.length
                        }
                        onCheckedChange={toggleAll}
                      />
                    </TableHead>
                  )}
                  <TableHead>配置名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>Base URL</TableHead>
                  <TableHead>模型 ID</TableHead>
                  <TableHead>API Key</TableHead>
                  <TableHead>状态</TableHead>
                  {isSuperuser && <TableHead className="w-20">操作</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.data.map((cfg) => (
                  <TableRow
                    key={cfg.id}
                    data-state={selected.has(cfg.id) ? "selected" : undefined}
                  >
                    {isSuperuser && (
                      <TableCell>
                        <Checkbox
                          checked={selected.has(cfg.id)}
                          onCheckedChange={() => toggleSelect(cfg.id)}
                        />
                      </TableCell>
                    )}
                    <TableCell className="font-medium">{cfg.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {PROVIDER_LABELS[cfg.provider_type] ??
                          cfg.provider_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground font-mono">
                      {cfg.provider_type === "kimi"
                        ? "https://api.moonshot.cn/v1"
                        : (cfg.base_url ?? "—")}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {cfg.model_id}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {cfg.api_key_masked ?? "未配置"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={cfg.is_active ? "default" : "secondary"}>
                        {cfg.is_active ? "启用" : "停用"}
                      </Badge>
                    </TableCell>
                    {isSuperuser && (
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setEditTarget(cfg)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            disabled={deleteMutation.isPending}
                            onClick={() => {
                              if (confirm(`确认删除配置 "${cfg.name}"？`))
                                deleteMutation.mutate(cfg.id)
                            }}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}

      {isSuperuser && (
        <>
          <ModelFormDialog open={createOpen} onOpenChange={setCreateOpen} />
          {editTarget && (
            <ModelFormDialog
              open={!!editTarget}
              onOpenChange={(v) => !v && setEditTarget(null)}
              initialData={editTarget}
            />
          )}
        </>
      )}
    </div>
  )
}
