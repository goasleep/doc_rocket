import type { QualityScoreDetail } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

interface QualityScoreDetailCardProps {
  detail: QualityScoreDetail
}

const dimensionLabels: Record<string, string> = {
  content_depth: "内容深度",
  readability: "可读性",
  originality: "原创性",
  virality_potential: "传播潜力",
}

export function QualityScoreDetailCard({
  detail,
}: QualityScoreDetailCardProps) {
  const dimensionLabel = dimensionLabels[detail.dimension] || detail.dimension

  // Determine color based on score
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600"
    if (score >= 60) return "text-amber-600"
    return "text-red-600"
  }

  const getProgressColor = (score: number) => {
    if (score >= 80) return "bg-green-600"
    if (score >= 60) return "bg-amber-600"
    return "bg-red-600"
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium">
            {dimensionLabel}
          </CardTitle>
          <div className="flex items-center gap-2">
            <span
              className={`text-2xl font-bold ${getScoreColor(detail.score)}`}
            >
              {detail.score.toFixed(0)}
            </span>
            <span className="text-xs text-muted-foreground">/100</span>
          </div>
        </div>
        <Progress
          value={detail.score}
          className="h-2"
          // @ts-expect-error - className override for indicator
          indicatorClassName={getProgressColor(detail.score)}
        />
        <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
          <span>权重 {Math.round(detail.weight * 100)}%</span>
          <span>加权 {detail.weighted_score.toFixed(1)}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {detail.reasoning && (
          <div className="text-sm text-muted-foreground">
            {detail.reasoning}
          </div>
        )}

        {detail.standard_matched && (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              符合: {detail.standard_matched}
            </Badge>
          </div>
        )}

        {detail.evidences && detail.evidences.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              评分依据
            </div>
            <div className="space-y-2">
              {detail.evidences.map((evidence, idx) => (
                <div key={idx} className="text-sm bg-muted/50 rounded p-2">
                  <p className="italic text-muted-foreground">
                    "{evidence.quote}"
                  </p>
                  {evidence.context && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {evidence.context}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {detail.improvement_suggestions &&
          detail.improvement_suggestions.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-amber-600">改进建议</div>
              <ul className="space-y-1">
                {detail.improvement_suggestions.map((suggestion, idx) => (
                  <li
                    key={idx}
                    className="text-sm text-muted-foreground flex items-start gap-2"
                  >
                    <span className="text-amber-500 mt-0.5">•</span>
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}
      </CardContent>
    </Card>
  )
}
