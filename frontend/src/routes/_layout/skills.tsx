import { useState, useEffect, Suspense, useCallback } from "react"
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Zap, Plus, Trash2, Edit2, Upload, Link } from "lucide-react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"

import {
  SkillsService,
  type SkillPublic,
  type SkillCreate,
  type SkillUpdate,
  type SkillImportBody,
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
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"

// ---------------------------------------------------------------------------
// Route
// ---------------------------------------------------------------------------

export const Route = createFileRoute("/_layout/skills")({
  component: Skills,
  head: () => ({
    meta: [{ title: "技能库 - 内容引擎" }],
  }),
})

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const createSkillSchema = z.object({
  name: z.string().min(1, "名称不能为空"),
  description: z.string().min(1, "描述不能为空"),
  body: z.string().min(1, "技能内容不能为空"),
})

type CreateSkillFormValues = z.infer<typeof createSkillSchema>

const editSkillSchema = z.object({
  description: z.string().min(1, "描述不能为空"),
  body: z.string().min(1, "技能内容不能为空"),
})

type EditSkillFormValues = z.infer<typeof editSkillSchema>

const importContentSchema = z.object({
  content: z.string().min(1, "请粘贴 SKILL.md 内容"),
})

const importUrlSchema = z.object({
  url: z.string().url("请输入有效的 URL"),
})

type ImportContentFormValues = z.infer<typeof importContentSchema>
type ImportUrlFormValues = z.infer<typeof importUrlSchema>

// ---------------------------------------------------------------------------
// Create dialog
// ---------------------------------------------------------------------------

function CreateSkillDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<CreateSkillFormValues>({
    resolver: zodResolver(createSkillSchema),
    defaultValues: { name: "", description: "", body: "" },
  })

  const mutation = useMutation({
    mutationFn: (data: SkillCreate) =>
      SkillsService.createSkill({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      showSuccessToast("技能已创建")
      onOpenChange(false)
      form.reset()
    },
    onError: () => showErrorToast("操作失败"),
  })

  function onSubmit(values: CreateSkillFormValues) {
    mutation.mutate({
      name: values.name,
      description: values.description,
      body: values.body,
    })
  }

  function handleOpenChange(v: boolean) {
    if (!v) form.reset()
    onOpenChange(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>新建 Skill</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control as any}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>名称</FormLabel>
                  <FormControl>
                    <Input placeholder="技能名称" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control as any}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>描述</FormLabel>
                  <FormControl>
                    <Input placeholder="简短描述此技能的用途" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control as any}
              name="body"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>内容</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="粘贴或编写技能内容（Markdown 格式）"
                      className="min-h-[160px] font-mono text-sm resize-y"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
                取消
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "创建中..." : "创建"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------
// Import dialog
// ---------------------------------------------------------------------------

type ImportMode = "content" | "url"

function ImportSkillDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [mode, setMode] = useState<ImportMode>("content")

  // Focus URL input when switching to URL mode (works around Radix Dialog focus trap)
  useEffect(() => {
    if (mode === "url") {
      const t = setTimeout(() => {
        document.getElementById("skill-import-url-input")?.focus()
      }, 30)
      return () => clearTimeout(t)
    }
  }, [mode])

  const contentForm = useForm<ImportContentFormValues>({
    resolver: zodResolver(importContentSchema),
    defaultValues: { content: "" },
  })

  const urlForm = useForm<ImportUrlFormValues>({
    resolver: zodResolver(importUrlSchema),
    defaultValues: { url: "" },
  })

  const mutation = useMutation({
    mutationFn: (data: SkillImportBody) =>
      SkillsService.importSkill({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      showSuccessToast("技能导入成功")
      onOpenChange(false)
      contentForm.reset()
      urlForm.reset()
    },
    onError: () => showErrorToast("操作失败"),
  })

  function onSubmitContent(values: ImportContentFormValues) {
    mutation.mutate({ content: values.content, url: null })
  }

  function onSubmitUrl(values: ImportUrlFormValues) {
    mutation.mutate({ content: null, url: values.url })
  }

  function handleOpenChange(v: boolean) {
    if (!v) {
      contentForm.reset()
      urlForm.reset()
      setMode("content")
    }
    onOpenChange(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>导入 SKILL.md</DialogTitle>
        </DialogHeader>

        {/* Mode toggle */}
        <div className="flex gap-2 border-b pb-2">
          <button
            type="button"
            onClick={() => setMode("content")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              mode === "content"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            <Upload className="h-3.5 w-3.5" />
            粘贴内容
          </button>
          <button
            type="button"
            onClick={() => setMode("url")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
              mode === "url"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            <Link className="h-3.5 w-3.5" />
            URL 导入
          </button>
        </div>

        {mode === "content" ? (
          <Form {...contentForm}>
            <form onSubmit={contentForm.handleSubmit(onSubmitContent)} className="space-y-4">
              <FormField
                control={contentForm.control as any}
                name="content"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>SKILL.md 内容</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="将 SKILL.md 的内容粘贴到此处..."
                        className="min-h-[200px] font-mono text-sm resize-y"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
                  取消
                </Button>
                <Button type="submit" disabled={mutation.isPending}>
                  {mutation.isPending ? "导入中..." : "导入"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        ) : (
          <Form {...urlForm}>
            <form onSubmit={urlForm.handleSubmit(onSubmitUrl)} className="space-y-4">
              <FormField
                control={urlForm.control as any}
                name="url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>SKILL.md URL</FormLabel>
                    <FormControl>
                      <Input id="skill-import-url-input" placeholder="https://..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
                  取消
                </Button>
                <Button type="submit" disabled={mutation.isPending}>
                  {mutation.isPending ? "导入中..." : "导入"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------
// Edit dialog
// ---------------------------------------------------------------------------

function EditSkillDialog({
  open,
  onOpenChange,
  skill,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  skill: SkillPublic
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<EditSkillFormValues>({
    resolver: zodResolver(editSkillSchema),
    defaultValues: {
      description: skill.description,
      body: skill.body,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: SkillUpdate) =>
      SkillsService.updateSkill({ skillId: skill.id, requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      showSuccessToast("技能已更新")
      onOpenChange(false)
    },
    onError: () => showErrorToast("操作失败"),
  })

  function onSubmit(values: EditSkillFormValues) {
    mutation.mutate({
      description: values.description,
      body: values.body,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>编辑技能</DialogTitle>
        </DialogHeader>
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">名称</p>
          <p className="text-sm font-semibold">{skill.name}</p>
        </div>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control as any}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>描述</FormLabel>
                  <FormControl>
                    <Input placeholder="简短描述此技能的用途" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control as any}
              name="body"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>内容</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="技能内容（Markdown 格式）"
                      className="min-h-[160px] font-mono text-sm resize-y"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                取消
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "保存中..." : "保存"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------
// Skill row
// ---------------------------------------------------------------------------

function SkillRow({
  skill,
  selected,
  onToggle,
  onDelete,
  deleteDisabled,
}: {
  skill: SkillPublic
  selected: boolean
  onToggle: (id: string) => void
  onDelete: (id: string, name: string) => void
  deleteDisabled: boolean
}) {
  const [editOpen, setEditOpen] = useState(false)

  return (
    <>
      <TableRow data-state={selected ? "selected" : undefined}>
        <TableCell>
          <Checkbox checked={selected} onCheckedChange={() => onToggle(skill.id)} />
        </TableCell>
        <TableCell className="font-medium">{skill.name}</TableCell>
        <TableCell className="text-muted-foreground text-sm max-w-48 truncate">
          {skill.description}
        </TableCell>
        <TableCell>
          <span className="uppercase text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
            {skill.source}
          </span>
        </TableCell>
        <TableCell>
          <StatusBadge status={skill.is_active ? "active" : "inactive"} />
        </TableCell>
        <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
          {new Date(skill.created_at).toLocaleString("zh-CN")}
        </TableCell>
        <TableCell>
          <div className="flex gap-1">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setEditOpen(true)}
              title="编辑"
            >
              <Edit2 className="h-4 w-4" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onDelete(skill.id, skill.name)}
              disabled={deleteDisabled}
              title="删除"
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        </TableCell>
      </TableRow>
      <EditSkillDialog open={editOpen} onOpenChange={setEditOpen} skill={skill} />
    </>
  )
}

// ---------------------------------------------------------------------------
// Table content (suspense boundary child)
// ---------------------------------------------------------------------------

function SkillsTableContent() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const { data } = useSuspenseQuery({
    queryKey: ["skills"],
    queryFn: () => SkillsService.listSkills({ skip: 0, limit: 100 }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => SkillsService.deleteSkill({ skillId: id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      showSuccessToast("技能已删除")
    },
    onError: () => showErrorToast("操作失败"),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) =>
      Promise.all(ids.map((id) => SkillsService.deleteSkill({ skillId: id }))),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      showSuccessToast(`已删除 ${selected.size} 个技能`)
      setSelected(new Set())
    },
    onError: () => showErrorToast("批量删除失败"),
  })

  const toggleSelect = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleAll = () => {
    if (selected.size === data.data.length) setSelected(new Set())
    else setSelected(new Set(data.data.map((s) => s.id)))
  }

  const handleDelete = useCallback((id: string, name: string) => {
    if (confirm(`确认删除技能 "${name}"？`)) deleteMutation.mutate(id)
  }, [deleteMutation])

  if (data.count === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-16">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Zap className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">暂无技能</h3>
        <p className="text-muted-foreground">创建或导入一个技能以开始使用</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {selected.size > 0 && (
        <div className="flex items-center gap-3 p-3 bg-muted rounded-md">
          <span className="text-sm">已选 {selected.size} 个</span>
          <Button
            size="sm"
            variant="destructive"
            disabled={bulkDeleteMutation.isPending}
            onClick={() => {
              if (confirm(`确认删除选中的 ${selected.size} 个技能？`))
                bulkDeleteMutation.mutate(Array.from(selected))
            }}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            批量删除
          </Button>
          <Button size="sm" variant="outline" onClick={() => setSelected(new Set())}>
            取消选择
          </Button>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">
              <Checkbox
                checked={data.data.length > 0 && selected.size === data.data.length}
                onCheckedChange={toggleAll}
              />
            </TableHead>
            <TableHead>名称</TableHead>
            <TableHead>描述</TableHead>
            <TableHead>来源</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>创建时间</TableHead>
            <TableHead>操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.data.map((skill) => (
            <SkillRow
              key={skill.id}
              skill={skill}
              selected={selected.has(skill.id)}
              onToggle={toggleSelect}
              onDelete={handleDelete}
              deleteDisabled={deleteMutation.isPending}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page root
// ---------------------------------------------------------------------------

function Skills() {
  const [createOpen, setCreateOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">技能库</h1>
          <p className="text-muted-foreground">管理可供智能体调用的技能</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setImportOpen(true)}>
            <Upload className="h-4 w-4 mr-1" />
            导入 SKILL.md
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            新建 Skill
          </Button>
        </div>
      </div>

      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">加载中...</div>
        }
      >
        <SkillsTableContent />
      </Suspense>

      <CreateSkillDialog open={createOpen} onOpenChange={setCreateOpen} />
      <ImportSkillDialog open={importOpen} onOpenChange={setImportOpen} />
    </div>
  )
}
