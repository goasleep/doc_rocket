import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  BookOpen,
  CheckCircle,
  Cloud,
  Lightbulb,
  PieChart,
  RefreshCw,
  TrendingUp,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import {
  type DistributionItem,
  type InsightSnapshotPublic,
  InsightsService,
  type QualityScoreBucket,
  type WordCloudItem,
} from "@/client"

// Extended type for AI flavor distribution (not yet in generated client)
interface ExtendedInsightSnapshotPublic
  extends Omit<InsightSnapshotPublic, "ai_flavor_distribution"> {
  ai_flavor_distribution?: QualityScoreBucket[]
}

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export const Route = createFileRoute("/_layout/insights")({
  component: InsightsPage,
  head: () => ({
    meta: [{ title: "知识洞察 - 内容引擎" }],
  }),
})

// Metric Card Component
function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  loading,
}: {
  title: string
  value: string | number
  description?: string
  icon: React.ElementType
  loading?: boolean
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <>
            <div className="text-2xl font-bold">{value}</div>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

// Word Cloud Chart Component
function WordCloudChart({
  data,
  title,
  loading,
}: {
  data: WordCloudItem[]
  title: string
  loading?: boolean
}) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<any>(null)
  const echartsModule = useRef<any>(null)

  useEffect(() => {
    if (loading || !data.length || !chartRef.current) return

    const initChart = async () => {
      if (!echartsModule.current) {
        const echarts = await import("echarts")
        await import("echarts-wordcloud")
        echartsModule.current = echarts
      }

      if (chartInstance.current) {
        chartInstance.current.dispose()
      }

      const chart = echartsModule.current.init(chartRef.current)
      chartInstance.current = chart

      const option = {
        tooltip: {
          show: true,
          formatter: (params: any) => {
            return `${params.name}<br/>频次: ${params.value}<br/>平均质量分: ${params.data.avgScore}`
          },
        },
        series: [
          {
            type: "wordCloud",
            shape: "circle",
            left: "center",
            top: "center",
            width: "95%",
            height: "95%",
            right: null,
            bottom: null,
            sizeRange: [12, 60],
            rotationRange: [-45, 45],
            rotationStep: 45,
            gridSize: 8,
            drawOutOfBound: false,
            layoutAnimation: true,
            textStyle: {
              fontFamily: "sans-serif",
              fontWeight: "bold",
              color: () => {
                const colors = [
                  "#5470c6",
                  "#91cc75",
                  "#fac858",
                  "#ee6666",
                  "#73c0de",
                  "#3ba272",
                  "#fc8452",
                  "#9a60b4",
                  "#ea7ccc",
                ]
                return colors[Math.floor(Math.random() * colors.length)]
              },
            },
            emphasis: {
              focus: "self",
              textStyle: {
                textShadowBlur: 10,
                textShadowColor: "#333",
              },
            },
            data: data.map((item) => ({
              name: item.name,
              value: item.value,
              avgScore: item.avg_score,
            })),
          },
        ],
      }

      chart.setOption(option)

      const handleResize = () => chart.resize()
      window.addEventListener("resize", handleResize)

      return () => {
        window.removeEventListener("resize", handleResize)
        chart.dispose()
      }
    }

    initChart()
  }, [data, loading])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            暂无数据
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={chartRef} className="h-[300px] w-full" />
      </CardContent>
    </Card>
  )
}

// Pie Chart Component
function PieChartComponent({
  data,
  title,
  loading,
}: {
  data: DistributionItem[]
  title: string
  loading?: boolean
}) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<any>(null)

  useEffect(() => {
    if (loading || !data.length || !chartRef.current) return

    const initChart = async () => {
      const echarts = await import("echarts")

      if (chartInstance.current) {
        chartInstance.current.dispose()
      }

      const chart = echarts.init(chartRef.current)
      chartInstance.current = chart

      const option = {
        tooltip: {
          trigger: "item",
          formatter: "{b}: {c} ({d}%)",
        },
        legend: {
          orient: "vertical",
          right: 10,
          top: "center",
        },
        series: [
          {
            type: "pie",
            radius: ["40%", "70%"],
            center: ["40%", "50%"],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: "#fff",
              borderWidth: 2,
            },
            label: {
              show: false,
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 14,
                fontWeight: "bold",
              },
            },
            data: data.map((item) => ({
              name: item.name,
              value: item.value,
            })),
          },
        ],
      }

      chart.setOption(option)

      const handleResize = () => chart.resize()
      window.addEventListener("resize", handleResize)

      return () => {
        window.removeEventListener("resize", handleResize)
        chart.dispose()
      }
    }

    initChart()
  }, [data, loading])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[250px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[250px] flex items-center justify-center text-muted-foreground">
            暂无数据
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={chartRef} className="h-[250px] w-full" />
      </CardContent>
    </Card>
  )
}

// Bar Chart Component
function BarChartComponent({
  data,
  title,
  loading,
}: {
  data: DistributionItem[]
  title: string
  loading?: boolean
}) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<any>(null)

  useEffect(() => {
    if (loading || !data.length || !chartRef.current) return

    const initChart = async () => {
      const echarts = await import("echarts")

      if (chartInstance.current) {
        chartInstance.current.dispose()
      }

      const chart = echarts.init(chartRef.current)
      chartInstance.current = chart

      const option = {
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
        },
        grid: {
          left: "3%",
          right: "4%",
          bottom: "3%",
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: data.map((item) => item.name),
          axisLabel: {
            interval: 0,
            rotate: 30,
          },
        },
        yAxis: {
          type: "value",
        },
        series: [
          {
            type: "bar",
            data: data.map((item) => item.value),
            itemStyle: {
              color: "#5470c6",
              borderRadius: [4, 4, 0, 0],
            },
          },
        ],
      }

      chart.setOption(option)

      const handleResize = () => chart.resize()
      window.addEventListener("resize", handleResize)

      return () => {
        window.removeEventListener("resize", handleResize)
        chart.dispose()
      }
    }

    initChart()
  }, [data, loading])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[250px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[250px] flex items-center justify-center text-muted-foreground">
            暂无数据
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={chartRef} className="h-[250px] w-full" />
      </CardContent>
    </Card>
  )
}

// Histogram Chart Component
function HistogramChart({
  data,
  title,
  loading,
}: {
  data: QualityScoreBucket[]
  title: string
  loading?: boolean
}) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<any>(null)

  useEffect(() => {
    if (loading || !data.length || !chartRef.current) return

    const initChart = async () => {
      const echarts = await import("echarts")

      if (chartInstance.current) {
        chartInstance.current.dispose()
      }

      const chart = echarts.init(chartRef.current)
      chartInstance.current = chart

      const option = {
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: "{b}: {c} 篇文章",
        },
        grid: {
          left: "3%",
          right: "4%",
          bottom: "3%",
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: data.map((item) => item.range),
        },
        yAxis: {
          type: "value",
        },
        series: [
          {
            type: "bar",
            data: data.map((item) => item.count),
            itemStyle: {
              color: (params: any) => {
                const colors = [
                  "#ee6666",
                  "#fac858",
                  "#91cc75",
                  "#73c0de",
                  "#5470c6",
                ]
                return colors[params.dataIndex] || "#5470c6"
              },
              borderRadius: [4, 4, 0, 0],
            },
          },
        ],
      }

      chart.setOption(option)

      const handleResize = () => chart.resize()
      window.addEventListener("resize", handleResize)

      return () => {
        window.removeEventListener("resize", handleResize)
        chart.dispose()
      }
    }

    initChart()
  }, [data, loading])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[250px] w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={chartRef} className="h-[250px] w-full" />
      </CardContent>
    </Card>
  )
}

// Suggestion Cloud Component
function SuggestionCloud({
  data,
  loading,
}: {
  data: { dimension: string; keywords: WordCloudItem[] }[]
  loading?: boolean
}) {
  const [activeDimension, setActiveDimension] = useState<string>("")

  useEffect(() => {
    if (data.length && !activeDimension) {
      setActiveDimension(data[0].dimension)
    }
  }, [data, activeDimension])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">改进建议词云</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">改进建议词云</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            暂无数据
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">改进建议词云</CardTitle>
        <CardDescription>按维度查看高频改进关键词</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activeDimension} onValueChange={setActiveDimension}>
          <TabsList className="mb-4 flex-wrap h-auto">
            {data.map((item) => (
              <TabsTrigger key={item.dimension} value={item.dimension}>
                {item.dimension}
              </TabsTrigger>
            ))}
          </TabsList>
          {data.map((item) => (
            <TabsContent key={item.dimension} value={item.dimension}>
              <WordCloudChart data={item.keywords} title="" loading={loading} />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  )
}

// Main Page Component
function InsightsPage() {
  const queryClient = useQueryClient()
  const [isRefreshing, setIsRefreshing] = useState(false)

  const { data: snapshot, isLoading } =
    useQuery<ExtendedInsightSnapshotPublic | null>({
      queryKey: ["insights", "latest"],
      queryFn: async () => {
        try {
          return await InsightsService.getLatestSnapshot()
        } catch (error: any) {
          if (error.status === 404) {
            return null
          }
          throw error
        }
      },
    })

  const refreshMutation = useMutation({
    mutationFn: () => InsightsService.refreshSnapshot(),
    onSuccess: (data) => {
      toast.success("快照刷新任务已启动", {
        description: `任务ID: ${data.task_run_id}`,
      })
      setIsRefreshing(true)
      // Poll for task completion
      const checkInterval = setInterval(() => {
        queryClient.invalidateQueries({ queryKey: ["insights", "latest"] })
      }, 5000)

      // Stop polling after 5 minutes
      setTimeout(() => {
        clearInterval(checkInterval)
        setIsRefreshing(false)
      }, 300000)
    },
    onError: (error: any) => {
      if (error.status === 429) {
        toast.error("刷新任务正在进行中", {
          description: "请稍后再试",
        })
      } else {
        toast.error("启动刷新任务失败", {
          description: error.message || "未知错误",
        })
      }
      setIsRefreshing(false)
    },
  })

  const handleRefresh = () => {
    refreshMutation.mutate()
  }

  const overview = snapshot?.overview
  const generatedAt = snapshot?.created_at
    ? new Date(snapshot.created_at).toLocaleString("zh-CN")
    : null

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">知识洞察</h1>
          <p className="text-sm text-muted-foreground">
            基于全库文章分析数据的聚合洞察与可视化
          </p>
        </div>
        <div className="flex items-center gap-3">
          {generatedAt && (
            <span className="text-sm text-muted-foreground">
              数据生成于: {generatedAt}
            </span>
          )}
          <Button
            onClick={handleRefresh}
            disabled={isRefreshing || refreshMutation.isPending}
            className="gap-2"
          >
            <RefreshCw
              className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
            />
            {isRefreshing ? "刷新中..." : "手动刷新"}
          </Button>
        </div>
      </div>

      {/* Overview Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="文章总数"
          value={overview?.total_articles ?? 0}
          description="知识库中的全部文章"
          icon={BookOpen}
          loading={isLoading}
        />
        <MetricCard
          title="已分析文章"
          value={overview?.analyzed_count ?? 0}
          description={`覆盖率: ${((overview?.coverage_rate ?? 0) * 100).toFixed(1)}%`}
          icon={CheckCircle}
          loading={isLoading}
        />
        <MetricCard
          title="平均质量分"
          value={overview?.avg_quality_score?.toFixed(1) ?? 0}
          description="所有分析文章的平均分"
          icon={TrendingUp}
          loading={isLoading}
        />
        <MetricCard
          title="分析覆盖率"
          value={`${((overview?.coverage_rate ?? 0) * 100).toFixed(1)}%`}
          description="已分析文章占比"
          icon={PieChart}
          loading={isLoading}
        />
      </div>

      {/* No Data State */}
      {!isLoading && !snapshot && (
        <Card className="py-12">
          <CardContent className="flex flex-col items-center justify-center text-center">
            <Cloud className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">暂无洞察数据</h3>
            <p className="text-sm text-muted-foreground mb-4">
              还没有生成过洞察快照，点击上方按钮手动刷新或等待定时任务
            </p>
            <Button
              onClick={handleRefresh}
              disabled={refreshMutation.isPending}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              立即生成
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Charts Grid */}
      {(isLoading || snapshot) && (
        <>
          {/* Word Clouds */}
          <div className="grid gap-4 md:grid-cols-2">
            <WordCloudChart
              data={snapshot?.keyword_cloud ?? []}
              title="关键词词云"
              loading={isLoading}
            />
            <WordCloudChart
              data={snapshot?.emotional_trigger_cloud ?? []}
              title="情绪触发词云"
              loading={isLoading}
            />
          </div>

          {/* Distributions */}
          <div className="grid gap-4 md:grid-cols-3">
            <PieChartComponent
              data={snapshot?.framework_distribution ?? []}
              title="文章框架分布"
              loading={isLoading}
            />
            <PieChartComponent
              data={snapshot?.hook_type_distribution ?? []}
              title="钩子类型分布"
              loading={isLoading}
            />
            <BarChartComponent
              data={snapshot?.topic_distribution ?? []}
              title="主题分布"
              loading={isLoading}
            />
          </div>

          {/* AI Flavor & Quality Distribution */}
          <div className="grid gap-4 md:grid-cols-2">
            <HistogramChart
              data={snapshot?.ai_flavor_distribution ?? []}
              title="AI味道分布（越高越自然）"
              loading={isLoading}
            />
            <HistogramChart
              data={snapshot?.quality_score_distribution ?? []}
              title="质量分数分布"
              loading={isLoading}
            />
          </div>

          {/* Suggestion Cloud */}
          <div className="grid gap-4">
            <SuggestionCloud
              data={snapshot?.suggestion_aggregation ?? []}
              loading={isLoading}
            />
          </div>
        </>
      )}

      {/* Info Card */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Lightbulb className="h-5 w-5 text-yellow-500 mt-0.5" />
            <div className="text-sm text-muted-foreground">
              <p className="font-medium text-foreground mb-1">关于知识洞察</p>
              <p>
                洞察数据通过定时任务每日自动更新（凌晨2点），您也可以随时点击"手动刷新"生成最新快照。
                快照生成可能需要几分钟时间，取决于文章数量。词云中的颜色代表不同的质量分区间。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
