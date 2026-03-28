"use client"

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatNumber, getChartColor } from "./utils"

interface DistributionItem {
  name: string
  value: number
  color?: string
}

interface TokenDistributionChartProps {
  data: DistributionItem[]
  title?: string
  isLoading?: boolean
}

export function TokenDistributionChart({
  data,
  title = "Token Distribution",
  isLoading = false,
}: TokenDistributionChartProps) {
  if (isLoading) {
    return <TokenDistributionChartSkeleton />
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map((item, index) => ({
    ...item,
    color: item.color || getChartColor(index),
  }))

  const total = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload?.length) {
                    const data = payload[0].payload as DistributionItem
                    const percentage =
                      total > 0 ? ((data.value / total) * 100).toFixed(1) : "0"
                    return (
                      <div className="rounded-lg border bg-background p-3 shadow-sm">
                        <div className="font-medium">{data.name}</div>
                        <div className="mt-1 text-sm text-muted-foreground">
                          {formatNumber(data.value)} tokens ({percentage}%)
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                formatter={(value, entry: any) => (
                  <span style={{ color: entry.color }}>{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

function TokenDistributionChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="h-5 w-40 animate-pulse rounded bg-muted" />
      </CardHeader>
      <CardContent>
        <div className="flex h-[250px] items-center justify-center">
          <div className="h-[180px] w-[180px] animate-pulse rounded-full bg-muted" />
        </div>
      </CardContent>
    </Card>
  )
}
