import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Check, Scale } from "lucide-react"
import { Suspense } from "react"

import { type RubricDimension, RubricsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

export const Route = createFileRoute("/_layout/rubrics")({
  component: RubricsPage,
})

const dimensionLabels: Record<string, string> = {
  content_depth: "内容深度",
  readability: "可读性",
  originality: "原创性",
  ai_flavor: "AI味道",
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
          <Badge variant="outline">
            权重 {Math.round(dimension.weight * 100)}%
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{dimension.description}</p>
      </CardHeader>
      <CardContent className="pt-0">
        {dimension.criteria && dimension.criteria.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              评分档位
            </div>
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

function RubricsContent() {
  const { data: activeRubric } = useSuspenseQuery({
    queryKey: ["rubrics", "active"],
    queryFn: () => RubricsService.getActiveRubric(),
  })

  if (!activeRubric) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无评分标准
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Active Rubric Info */}
      <Card className="bg-primary/5 border-primary/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">当前评分标准</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">{activeRubric.name}</div>
              <div className="text-sm text-muted-foreground">
                版本 {activeRubric.version} · {activeRubric.dimensions.length}{" "}
                个维度
              </div>
            </div>
            <Badge className="bg-primary text-primary-foreground">
              <Check className="h-3 w-3 mr-1" />
              启用中
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Dimensions Grid */}
      <div>
        <h2 className="text-lg font-semibold mb-4">评分维度</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {activeRubric.dimensions.map((dimension, idx) => (
            <DimensionCard key={idx} dimension={dimension} />
          ))}
        </div>
      </div>

      {/* Note */}
      <div className="text-sm text-muted-foreground bg-muted p-4 rounded-lg">
        <p>
          评分标准由代码定义，如需修改请更新后端代码中的{" "}
          <code>DEFAULT_RUBRIC_V1</code> 配置。
        </p>
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
          文章质量评分的评分标准（Rubrics）- 代码定义
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
