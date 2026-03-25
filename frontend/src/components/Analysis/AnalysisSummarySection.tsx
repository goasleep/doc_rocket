import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, FileText } from "lucide-react"

interface AnalysisSummarySectionProps {
  summary: string
  improvementSuggestions: string[]
  rubricVersion?: string
  analysisDurationMs?: number
}

export function AnalysisSummarySection({
  summary,
  improvementSuggestions,
  rubricVersion,
  analysisDurationMs,
}: AnalysisSummarySectionProps) {
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m${Math.floor((ms % 60000) / 1000)}s`
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">分析总结</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              {rubricVersion && (
                <Badge variant="outline" className="text-xs">
                  评分标准: {rubricVersion}
                </Badge>
              )}
              {analysisDurationMs != null && (
                <Badge variant="secondary" className="text-xs">
                  耗时: {formatDuration(analysisDurationMs)}
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {summary}
          </p>
        </CardContent>
      </Card>

      {improvementSuggestions.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-amber-500" />
              <CardTitle className="text-base">改进建议</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {improvementSuggestions.map((suggestion, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
                    {idx + 1}
                  </div>
                  <p className="text-sm text-muted-foreground pt-0.5">{suggestion}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
