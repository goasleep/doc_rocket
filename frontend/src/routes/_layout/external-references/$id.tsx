import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, ExternalLink, Globe } from "lucide-react"
import { Suspense } from "react"

import { ExternalReferencesService, ArticlesService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/_layout/external-references/$id")({
  component: ExternalReferenceDetailPage,
})

function ExternalReferenceDetailContent() {
  const { id } = Route.useParams()

  const { data: ref } = useQuery({
    queryKey: ["external-reference", id],
    queryFn: () =>
      ExternalReferencesService.getExternalReference({ refId: id }),
  })

  if (!ref) {
    return (
      <div className="flex justify-center py-12 text-muted-foreground">
        加载中...
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Link to="/external-references">
              <Button variant="ghost" size="sm" className="gap-1">
                <ArrowLeft className="h-4 w-4" />
                返回列表
              </Button>
            </Link>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <Globe className="h-5 w-5 text-muted-foreground" />
            <Badge variant="outline">{ref.source || "外部来源"}</Badge>
            <Badge variant="secondary">
              被 {ref.referencer_article_ids?.length || 0} 篇文章引用
            </Badge>
          </div>
          <h1 className="text-2xl font-bold">{ref.title}</h1>
          <a
            href={ref.url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-muted-foreground hover:underline flex items-center gap-1 mt-1"
          >
            {ref.url}
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
        <Button variant="outline" size="sm" asChild>
          <a href={ref.url} target="_blank" rel="noreferrer">
            <ExternalLink className="h-4 w-4 mr-1" />
            访问原文
          </a>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">内容摘要</CardTitle>
            </CardHeader>
            <CardContent>
              {ref.content_snippet ? (
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {ref.content_snippet}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground italic">
                  暂无内容摘要
                </p>
              )}
            </CardContent>
          </Card>

          {ref.content && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">完整内容</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm leading-relaxed max-h-[600px] overflow-y-auto whitespace-pre-wrap">
                  {ref.content}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">元数据</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-xs text-muted-foreground">创建时间</div>
                <div className="text-sm">
                  {new Date(ref.created_at).toLocaleString("zh-CN")}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">更新时间</div>
                <div className="text-sm">
                  {new Date(ref.updated_at).toLocaleString("zh-CN")}
                </div>
              </div>
              {ref.fetched_at && (
                <div>
                  <div className="text-xs text-muted-foreground">抓取时间</div>
                  <div className="text-sm">
                    {new Date(ref.fetched_at).toLocaleString("zh-CN")}
                  </div>
                </div>
              )}
              {ref.search_query && (
                <div>
                  <div className="text-xs text-muted-foreground">搜索查询</div>
                  <div className="text-sm">{ref.search_query}</div>
                </div>
              )}
            </CardContent>
          </Card>

          {ref.referencer_article_ids &&
            ref.referencer_article_ids.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">引用此参考的文章</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {ref.referencer_article_ids.map((articleId) => (
                      <ReferencerArticleItem key={articleId} id={articleId} />
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

          {ref.metadata && Object.keys(ref.metadata).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">额外元数据</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40">
                  {JSON.stringify(ref.metadata, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

function ReferencerArticleItem({ id }: { id: string }) {
  const { data: article } = useQuery({
    queryKey: ["article", id],
    queryFn: () => ArticlesService.getArticle({ id }),
    enabled: !!id,
  })

  if (!article) {
    return (
      <div className="text-sm text-muted-foreground py-2">
        加载文章 {id.slice(0, 8)}...
      </div>
    )
  }

  return (
    <Link
      to="/articles/$id"
      params={{ id }}
      className="block p-2 rounded hover:bg-muted transition-colors"
    >
      <div className="text-sm font-medium truncate">{article.title}</div>
      <div className="text-xs text-muted-foreground">
        {new Date(article.created_at).toLocaleDateString("zh-CN")}
      </div>
    </Link>
  )
}

function ExternalReferenceDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-12 text-muted-foreground">
          加载中...
        </div>
      }
    >
      <ExternalReferenceDetailContent />
    </Suspense>
  )
}
