import type { ArticleTokenUsage } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { formatDate, formatNumber } from "./utils"

interface TokenUsageBreakdownProps {
  operations: ArticleTokenUsage[]
  totalTokens: number
  totalPromptTokens: number
  totalCompletionTokens: number
  operationCount: number
  isLoading?: boolean
}

export function TokenUsageBreakdown({
  operations,
  totalTokens,
  totalPromptTokens,
  totalCompletionTokens,
  operationCount,
  isLoading = false,
}: TokenUsageBreakdownProps) {
  if (isLoading) {
    return <TokenUsageBreakdownSkeleton />
  }

  if (operations.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Token Usage Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="text-muted-foreground">
              No token usage recorded for this article
            </div>
            <div className="text-sm text-muted-foreground">
              Token usage will appear here after processing
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Token Usage Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatBox label="Total Tokens" value={formatNumber(totalTokens)} />
          <StatBox
            label="Prompt Tokens"
            value={formatNumber(totalPromptTokens)}
          />
          <StatBox
            label="Completion Tokens"
            value={formatNumber(totalCompletionTokens)}
          />
          <StatBox label="Operations" value={formatNumber(operationCount)} />
        </div>

        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Operation</TableHead>
                <TableHead>Model</TableHead>
                <TableHead className="text-right">Prompt</TableHead>
                <TableHead className="text-right">Completion</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="hidden sm:table-cell">Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operations.map((op, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <Badge variant="outline">{op.operation}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {op.model_name}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(op.prompt_tokens)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(op.completion_tokens)}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatNumber(op.total_tokens)}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                    {op.created_at ? formatDate(op.created_at) : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  )
}

function TokenUsageBreakdownSkeleton() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Token Usage Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-lg bg-muted p-3">
              <div className="h-3 w-20 animate-pulse rounded bg-muted-foreground/20" />
              <div className="mt-1 h-6 w-16 animate-pulse rounded bg-muted-foreground/20" />
            </div>
          ))}
        </div>
        <div className="rounded-md border">
          <div className="h-10 animate-pulse bg-muted" />
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-12 animate-pulse border-t bg-muted/50" />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
