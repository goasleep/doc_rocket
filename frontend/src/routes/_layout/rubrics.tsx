import { useMutation, useQuery, useQueryClient, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Check, Plus, Scale, X } from "lucide-react"
import { Suspense, useState } from "react"

import { RubricsService, type QualityRubricPublic, type RubricDimension } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/rubrics")({
  component: RubricsPage,
})

const dimensionLabels: Record<string, string> = {
  content_depth: "内容深度",
  readability: "可读性",
  originality: "原创性",
  virality_potential: "传播潜力",
}

function DimensionCard({ dimension }: { dimension: RubricDimension }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {dimensionLabels[dimension.name] || dimension.name}
          </CardTitle>
          <Badge variant="outline">权重 {Math.round(dimension.weight * 100)}%</Badge>
        </div>
        <p className="text-sm text-muted-foreground">{dimension.description}</p>
      </CardHeader>
      <CardContent className="pt-0">
        {dimension.criteria && dimension.criteria.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">评分档位</div>
            <div className="space-y-1">
              {dimension.criteria.map((criterion, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground w-20">
                    <span>{criterion.min_score}</span>
                    <span>-</span>
                    <span>{criterion.max_score}</span>
                  </div>
                  <span className="flex-1">{criterion.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function RubricCard({
  rubric,
  isActive,
}: {
  rubric: QualityRubricPublic
  isActive: boolean
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { user } = useAuth()
  const isAdmin = user?.is_superuser
  const [isExpanded, setIsExpanded] = useState(false)

  const activateMutation = useMutation({
    mutationFn: () => RubricsService.activateRubric({ rubricId: rubric.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rubrics"] })
      queryClient.invalidateQueries({ queryKey: ["rubrics", "active"] })
      showSuccessToast("评分标准已激活")
    },
    onError: () => showErrorToast("操作失败"),
  })

  const deleteMutation = useMutation({
    mutationFn: () => RubricsService.deleteRubric({ rubricId: rubric.id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rubrics"] })
      showSuccessToast("评分标准已删除")
    },
    onError: (error: any) => {
      showErrorToast(error?.body?.detail || "删除失败")
    },
  })

  return (
    <Card className={isActive ? "border-primary" : undefined}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <CardTitle className="text-lg">{rubric.name}</CardTitle>
              {isActive && (
                <Badge className="bg-primary text-primary-foreground">
                  <Check className="h-3 w-3 mr-1" />
                  当前启用
                </Badge>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              版本 {rubric.version} · {rubric.dimensions.length} 个维度
            </div>
          </div>
          <div className="flex items-center gap-1">
            {!isActive && isAdmin && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => activateMutation.mutate()}
                disabled={activateMutation.isPending}
              >
                启用
              </Button>
            )}
            {isAdmin && !isActive && (
              <Button
                size="icon"
                variant="ghost"
                onClick={() => {
                  if (confirm("确认删除此评分标准？")) deleteMutation.mutate()
                }}
                disabled={deleteMutation.isPending}
              >
                <X className="h-4 w-4 text-destructive" />
              </Button>
            )}
          </div>
        </div>
        {rubric.description && (
          <p className="text-sm text-muted-foreground mt-2">{rubric.description}</p>
        )}
      </CardHeader>
      <CardContent>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="mb-2"
        >
          {isExpanded ? "收起详情" : "查看详情"}
        </Button>

        {isExpanded && (
          <div className="space-y-4 pt-2">
            <Separator />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {rubric.dimensions.map((dimension, idx) => (
                <DimensionCard key={idx} dimension={dimension} />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CreateRubricDialog() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [version, setVersion] = useState("")
  const [description, setDescription] = useState("")

  const createMutation = useMutation({
    mutationFn: () =>
      RubricsService.createRubric({
        requestBody: {
          name,
          version: version || "1.0",
          description,
          dimensions: [
            {
              name: "content_depth",
              description: "内容深度与信息密度",
              weight: 0.3,
              criteria: [
                { min_score: 0, max_score: 20, description: "浅层内容，缺乏实质信息" },
                { min_score: 21, max_score: 40, description: "基础内容，信息有限" },
                { min_score: 41, max_score: 60, description: "中等深度，有一定信息量" },
                { min_score: 61, max_score: 80, description: "深度内容，信息丰富" },
                { min_score: 81, max_score: 100, description: "极具深度，信息密集且有价值" },
              ],
            },
            {
              name: "readability",
              description: "可读性与表达清晰度",
              weight: 0.25,
              criteria: [
                { min_score: 0, max_score: 20, description: "晦涩难懂，表达混乱" },
                { min_score: 21, max_score: 40, description: "较为晦涩，需要费力理解" },
                { min_score: 41, max_score: 60, description: "基本可读，偶有晦涩" },
                { min_score: 61, max_score: 80, description: "流畅易读，表达清晰" },
                { min_score: 81, max_score: 100, description: "极佳可读性，引人入胜" },
              ],
            },
            {
              name: "originality",
              description: "原创性与独特视角",
              weight: 0.25,
              criteria: [
                { min_score: 0, max_score: 20, description: "完全复制，毫无新意" },
                { min_score: 21, max_score: 40, description: "缺乏原创，观点陈旧" },
                { min_score: 41, max_score: 60, description: "有一定原创元素" },
                { min_score: 61, max_score: 80, description: "观点新颖，有独特视角" },
                { min_score: 81, max_score: 100, description: "极具原创性，开创性观点" },
              ],
            },
            {
              name: "virality_potential",
              description: "传播潜力与话题性",
              weight: 0.2,
              criteria: [
                { min_score: 0, max_score: 20, description: "无传播价值" },
                { min_score: 21, max_score: 40, description: "传播潜力低" },
                { min_score: 41, max_score: 60, description: "有一定传播潜力" },
                { min_score: 61, max_score: 80, description: "高传播潜力，话题性强" },
                { min_score: 81, max_score: 100, description: "爆款潜质，极具传播力" },
              ],
            },
          ],
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rubrics"] })
      showSuccessToast("评分标准已创建")
      setOpen(false)
      setName("")
      setVersion("")
      setDescription("")
    },
    onError: () => showErrorToast("创建失败"),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-1" />
          新建评分标准
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>新建评分标准</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">名称</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：默认评分标准"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="version">版本</Label>
            <Input
              id="version"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="例如：1.0"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">描述</Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="评分标准的简要描述"
            />
          </div>
          <div className="text-xs text-muted-foreground">
            创建后将使用默认的4维度评分体系（内容深度、可读性、原创性、传播潜力）
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setOpen(false)}>
            取消
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!name || createMutation.isPending}
          >
            创建
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function RubricsContent() {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser

  const { data: rubricsData } = useSuspenseQuery({
    queryKey: ["rubrics"],
    queryFn: () => RubricsService.listRubrics({ skip: 0, limit: 100 }),
  })

  const { data: activeRubric } = useQuery({
    queryKey: ["rubrics", "active"],
    queryFn: () => RubricsService.getActiveRubric(),
  })

  const rubrics = rubricsData?.data ?? []
  const activeId = activeRubric?.id

  return (
    <div className="space-y-6">
      {/* Active Rubric Info */}
      {activeRubric && (
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">当前启用的评分标准</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{activeRubric.name}</div>
                <div className="text-sm text-muted-foreground">
                  版本 {activeRubric.version} · {activeRubric.dimensions.length} 个维度
                </div>
              </div>
              <Badge className="bg-primary text-primary-foreground">
                <Check className="h-3 w-3 mr-1" />
                启用中
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">所有评分标准</h2>
          <p className="text-sm text-muted-foreground">
            共 {rubrics.length} 个评分标准
          </p>
        </div>
        {isAdmin && <CreateRubricDialog />}
      </div>

      {/* Rubrics List */}
      <div className="space-y-4">
        {rubrics.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            暂无评分标准
          </div>
        ) : (
          rubrics.map((rubric) => (
            <RubricCard
              key={rubric.id}
              rubric={rubric}
              isActive={rubric.id === activeId}
            />
          ))
        )}
      </div>
    </div>
  )
}

function RubricsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">评分标准</h1>
        <p className="text-muted-foreground">
          管理文章质量评分的评分标准（Rubrics）
        </p>
      </div>
      <Suspense
        fallback={
          <div className="flex justify-center py-12 text-muted-foreground">
            加载中...
          </div>
        }
      >
        <RubricsContent />
      </Suspense>
    </div>
  )
}
