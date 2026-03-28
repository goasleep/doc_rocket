"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import { formatNumber, formatDate, chartColors } from "./utils"
import type { TrendDataPoint } from "@/client"

interface TokenTrendChartProps {
  data: TrendDataPoint[]
  days: number
  onDaysChange: (days: number) => void
  isLoading?: boolean
}

export function TokenTrendChart({
  data,
  days,
  onDaysChange,
  isLoading = false,
}: TokenTrendChartProps) {
  if (isLoading) {
    return <TokenTrendChartSkeleton />
  }

  const chartData = data.map((item) => ({
    date: typeof item.date === "string" ? item.date : new Date(item.date).toISOString().split("T")[0],
    displayDate: formatDate(typeof item.date === "string" ? item.date : new Date(item.date).toISOString()),
    tokens: item.total_tokens,
    calls: item.total_calls,
  }))

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Token Usage Trend</CardTitle>
        <Select
          value={days.toString()}
          onValueChange={(value) => onDaysChange(Number.parseInt(value))}
        >
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Select range" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="displayDate"
                tick={{ fontSize: 12 }}
                tickMargin={10}
                minTickGap={30}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => formatNumber(value)}
                width={60}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="rounded-lg border bg-background p-3 shadow-sm">
                        <div className="font-medium">{label}</div>
                        <div className="mt-2 space-y-1 text-sm">
                          <div className="flex items-center gap-2">
                            <div
                              className="h-2 w-2 rounded-full"
                              style={{ backgroundColor: chartColors.primary }}
                            />
                            <span className="text-muted-foreground">Total Tokens:</span>
                            <span className="font-medium">
                              {formatNumber(payload[0].value as number)}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div
                              className="h-2 w-2 rounded-full"
                              style={{ backgroundColor: chartColors.secondary }}
                            />
                            <span className="text-muted-foreground">Calls:</span>
                            <span className="font-medium">
                              {formatNumber(payload[1]?.value as number)}
                            </span>
                          </div>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="tokens"
                name="Total Tokens"
                stroke={chartColors.primary}
                strokeWidth={2}
                dot={{ r: 3, fill: chartColors.primary }}
                activeDot={{ r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="calls"
                name="API Calls"
                stroke={chartColors.secondary}
                strokeWidth={2}
                dot={{ r: 2, fill: chartColors.secondary }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

function TokenTrendChartSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="h-5 w-32 animate-pulse rounded bg-muted" />
        <div className="h-8 w-32 animate-pulse rounded bg-muted" />
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  )
}
