import { BookOpen, ExternalLink, Globe } from "lucide-react"
import type { ComparisonReferenceEmbedded } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface ComparisonReferenceCardProps {
  reference: ComparisonReferenceEmbedded
}

export function ComparisonReferenceCard({
  reference,
}: ComparisonReferenceCardProps) {
  const isExternal = reference.source === "external"
  const title =
    reference.external_title || reference.kb_article_title || "未知标题"
  const url = reference.external_url

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            {isExternal ? (
              <Globe className="h-4 w-4 text-muted-foreground" />
            ) : (
              <BookOpen className="h-4 w-4 text-muted-foreground" />
            )}
            <Badge variant="outline" className="text-xs">
              {isExternal ? "外部参考" : "知识库"}
            </Badge>
          </div>
          {reference.quality_score != null && (
            <div className="flex items-center gap-1 text-sm">
              <span className="font-medium">
                {reference.quality_score.toFixed(0)}
              </span>
              <span className="text-xs text-muted-foreground">分</span>
            </div>
          )}
        </div>
        <CardTitle className="text-sm font-medium">
          {url ? (
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="hover:underline flex items-center gap-1"
            >
              {title}
              <ExternalLink className="h-3 w-3 text-muted-foreground" />
            </a>
          ) : (
            title
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>相似度</span>
          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full"
              style={{ width: `${(reference.similarity_score || 0) * 100}%` }}
            />
          </div>
          <span>{((reference.similarity_score || 0) * 100).toFixed(0)}%</span>
        </div>

        {reference.key_differences && reference.key_differences.length > 0 && (
          <div className="space-y-1">
            <div className="text-xs font-medium text-muted-foreground">
              关键差异
            </div>
            <ul className="space-y-1">
              {reference.key_differences.map((diff, idx) => (
                <li
                  key={idx}
                  className="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <span className="text-blue-500 mt-0.5">•</span>
                  {diff}
                </li>
              ))}
            </ul>
          </div>
        )}

        {reference.advantages && reference.advantages.length > 0 && (
          <div className="space-y-1">
            <div className="text-xs font-medium text-green-600">对方优势</div>
            <ul className="space-y-1">
              {reference.advantages.map((advantage, idx) => (
                <li
                  key={idx}
                  className="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <span className="text-green-500 mt-0.5">+</span>
                  {advantage}
                </li>
              ))}
            </ul>
          </div>
        )}

        {reference.learnings && reference.learnings.length > 0 && (
          <div className="space-y-1">
            <div className="text-xs font-medium text-amber-600">可借鉴之处</div>
            <ul className="space-y-1">
              {reference.learnings.map((learning, idx) => (
                <li
                  key={idx}
                  className="text-sm text-muted-foreground flex items-start gap-2"
                >
                  <span className="text-amber-500 mt-0.5">★</span>
                  {learning}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
