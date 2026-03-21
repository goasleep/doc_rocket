import { useState } from "react"
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Rss, Plus, Trash2, RefreshCw, Edit2 } from "lucide-react"
import { Suspense } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"

import {
  SourcesService,
  type SourcePublic,
  type SourceCreate,
  type SourceUpdate,
} from "@/client"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
import useCustomToast from "@/hooks/useCustomToast"

const sourceSchema = z.object({
  name: z.string().min(1, "名称不能为空"),
  type: z.enum(["api", "rss"]),
  url: z.string().url("请输入有效的 URL"),
  api_key: z.string().optional(),
  fetch_interval_minutes: z.number().min(5).max(10080),
  max_items_per_fetch: z.number().min(1).max(100),
  // API config fields (only for type=api)
  items_path: z.string().optional(),
  title_field: z.string().optional(),
  content_field: z.string().optional(),
  url_field: z.string().optional(),
})

type SourceFormValues = z.infer<typeof sourceSchema>

export const Route = createFileRoute("/_layout/sources")({
  component: Sources,
  head: () => ({
    meta: [{ title: "订阅源 - 内容引擎" }],
  }),
})

function SourceFormDialog({
  open,
  onOpenChange,
  initialData,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  initialData?: SourcePublic
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const isEdit = !!initialData

  const form = useForm<SourceFormValues>({
    resolver: zodResolver(sourceSchema),
    defaultValues: initialData
      ? {
          name: initialData.name,
          type: initialData.type as "api" | "rss",
          url: initialData.url,
          fetch_interval_minutes: initialData.fetch_config.interval_minutes,
          max_items_per_fetch: initialData.fetch_config.max_items_per_fetch,
          items_path: initialData.api_config?.items_path ?? "",
          title_field: initialData.api_config?.title_field ?? "",
          content_field: initialData.api_config?.content_field ?? "",
          url_field: initialData.api_config?.url_field ?? "",
        }
      : { type: "api", fetch_interval_minutes: 60, max_items_per_fetch: 10 },
  })

  const type = form.watch("type")

  const createMutation = useMutation({
    mutationFn: (data: SourceCreate) =>
      SourcesService.createSource({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] })
      showSuccessToast("订阅源已创建")
      onOpenChange(false)
    },
    onError: () => showErrorToast("创建失败"),
  })

  const updateMutation = useMutation({
    mutationFn: (data: SourceUpdate) =>
      SourcesService.updateSource({ id: initialData!.id, requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] })
      showSuccessToast("订阅源已更新")
      onOpenChange(false)
    },
    onError: () => showErrorToast("更新失败"),
  })

  function onSubmit(values: SourceFormValues) {
    const payload = {
      name: values.name,
      type: values.type,
      url: values.url,
      api_key: values.api_key || undefined,
      fetch_config: {
        interval_minutes: values.fetch_interval_minutes,
        max_items_per_fetch: values.max_items_per_fetch,
      },
      api_config:
        values.type === "api"
          ? {
              items_path: values.items_path || "data",
              title_field: values.title_field || "title",
              content_field: values.content_field || "content",
              url_field: values.url_field || "url",
            }
          : undefined,
    }

    if (isEdit) {
      updateMutation.mutate(payload as SourceUpdate)
    } else {
      createMutation.mutate(payload as SourceCreate)
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑订阅源" : "新建订阅源"}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-4">
            <FormField
              control={form.control as any}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>名称</FormLabel>
                  <FormControl>
                    <Input placeholder="订阅源名称" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control as any}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>类型</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="api">API</SelectItem>
                      <SelectItem value="rss">RSS</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control as any}
              name="url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>URL</FormLabel>
                  <FormControl>
                    <Input placeholder="https://..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {type === "api" && (
              <>
                <FormField
                  control={form.control as any}
                  name="api_key"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>API Key（可选）</FormLabel>
                      <FormControl>
                        <Input type="password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="rounded-md border p-3 space-y-3">
                  <p className="text-sm font-medium text-muted-foreground">字段映射</p>
                  {(
                    [
                      { name: "items_path", label: "数据路径", placeholder: "data" },
                      { name: "title_field", label: "标题字段", placeholder: "title" },
                      { name: "content_field", label: "正文字段", placeholder: "content" },
                      { name: "url_field", label: "URL字段", placeholder: "url" },
                    ] as const
                  ).map((f) => (
                    <FormField
                      key={f.name}
                      control={form.control as any}
                      name={f.name}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-xs">{f.label}</FormLabel>
                          <FormControl>
                            <Input
                              placeholder={f.placeholder}
                              className="h-7 text-sm"
                              {...field}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  ))}
                </div>
              </>
            )}
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control as any}
                name="fetch_interval_minutes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>抓取间隔（分钟）</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} onChange={(e) => field.onChange(e.target.valueAsNumber)} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control as any}
                name="max_items_per_fetch"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>每次最多抓取</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} onChange={(e) => field.onChange(e.target.valueAsNumber)} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
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

function SourceRow({ source }: { source: SourcePublic }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [editOpen, setEditOpen] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: () => SourcesService.deleteSource({ id: source.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] })
      showSuccessToast("订阅源已删除")
    },
    onError: () => showErrorToast("删除失败"),
  })

  const fetchMutation = useMutation({
    mutationFn: () => SourcesService.triggerFetch({ id: source.id }),
    onSuccess: () => showSuccessToast("抓取任务已触发"),
    onError: () => showErrorToast("触发失败"),
  })

  return (
    <>
      <TableRow>
        <TableCell className="font-medium">{source.name}</TableCell>
        <TableCell>
          <span className="uppercase text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
            {source.type}
          </span>
        </TableCell>
        <TableCell className="text-muted-foreground text-xs max-w-48 truncate">
          {source.url}
        </TableCell>
        <TableCell>
          <StatusBadge status={source.is_active ? "active" : "inactive"} />
        </TableCell>
        <TableCell className="text-xs text-muted-foreground">
          {source.last_fetched_at
            ? new Date(source.last_fetched_at).toLocaleString("zh-CN")
            : "从未"}
        </TableCell>
        <TableCell>
          <div className="flex gap-1">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => fetchMutation.mutate()}
              disabled={fetchMutation.isPending}
              title="立即抓取"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
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
                if (confirm("确认删除此订阅源？")) deleteMutation.mutate()
              }}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        </TableCell>
      </TableRow>
      <SourceFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        initialData={source}
      />
    </>
  )
}

function SourcesTableContent() {
  const { data } = useSuspenseQuery({
    queryKey: ["sources"],
    queryFn: () => SourcesService.listSources({ skip: 0, limit: 100 }),
  })

  if (data.count === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Rss className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">暂无订阅源</h3>
        <p className="text-muted-foreground">添加一个订阅源开始抓取文章</p>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>名称</TableHead>
          <TableHead>类型</TableHead>
          <TableHead>URL</TableHead>
          <TableHead>状态</TableHead>
          <TableHead>最后抓取</TableHead>
          <TableHead>操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.data.map((source) => (
          <SourceRow key={source.id} source={source} />
        ))}
      </TableBody>
    </Table>
  )
}

function Sources() {
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">订阅源管理</h1>
          <p className="text-muted-foreground">配置文章来源，定时自动抓取</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          新建订阅源
        </Button>
      </div>
      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">加载中...</div>
        }
      >
        <SourcesTableContent />
      </Suspense>
      <SourceFormDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
