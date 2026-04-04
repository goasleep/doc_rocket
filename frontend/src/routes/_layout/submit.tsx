import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { SubmitService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/submit")({
  component: Submit,
  head: () => ({
    meta: [{ title: "手动投稿 - 内容引擎" }],
  }),
})

const textSchema = z.object({
  title: z.string().min(1, "标题不能为空"),
  content: z.string().min(10, "正文至少 10 个字符"),
})

const urlsSchema = z.object({
  urls: z.string().min(1, "请输入至少一个 URL"),
})

function TextSubmitForm() {
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const form = useForm<z.infer<typeof textSchema>>({
    resolver: zodResolver(textSchema),
    defaultValues: { title: "", content: "" },
  })

  const mutation = useMutation({
    mutationFn: (data: z.infer<typeof textSchema>) =>
      SubmitService.submitArticle({
        requestBody: { mode: "text", title: data.title, content: data.content },
      }),
    onSuccess: (result) => {
      showSuccessToast("投稿成功，正在分析...")
      navigate({ to: "/articles/$id", params: { id: result.article_id } })
    },
    onError: () => showErrorToast("投稿失败"),
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
        className="space-y-4"
      >
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>标题</FormLabel>
              <FormControl>
                <Input placeholder="文章标题" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>正文内容</FormLabel>
              <FormControl>
                <Textarea
                  className="min-h-[240px] resize-y"
                  placeholder="粘贴文章正文..."
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  onBlur={field.onBlur}
                  name={field.name}
                  ref={field.ref}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "提交中..." : "提交并分析"}
        </Button>
      </form>
    </Form>
  )
}

function UrlSubmitForm() {
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [urlCount, setUrlCount] = useState(0)

  const form = useForm<z.infer<typeof urlsSchema>>({
    resolver: zodResolver(urlsSchema),
    defaultValues: { urls: "" },
  })

  // 实时解析 URL 数量
  const watchUrls = form.watch("urls")
  useEffect(() => {
    const urls = watchUrls
      .split(/[\n;]+/)
      .map((u) => u.trim().replace(/,$/, ""))
      .filter((u) => u.startsWith("http://") || u.startsWith("https://"))
    // 去重计数
    const uniqueUrls = [...new Set(urls)]
    setUrlCount(uniqueUrls.length)
  }, [watchUrls])

  const mutation = useMutation({
    mutationFn: (data: z.infer<typeof urlsSchema>) =>
      SubmitService.submitUrlsBatch({
        requestBody: { urls: data.urls },
      }),
    onSuccess: (result) => {
      showSuccessToast(result.message)
      navigate({ to: "/articles" })
    },
    onError: (err: any) => {
      const detail = err?.body?.detail
      showErrorToast(detail ?? "提交失败")
    },
  })

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
        className="space-y-4"
      >
        <FormField
          control={form.control}
          name="urls"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                文章 URL 列表
                {urlCount > 0 && (
                  <span className="ml-2 text-sm text-muted-foreground">
                    (已识别 {urlCount} 个有效 URL)
                  </span>
                )}
              </FormLabel>
              <FormControl>
                <Textarea
                  className="min-h-[200px] resize-y font-mono text-sm"
                  placeholder={`https://example.com/article1\nhttps://example.com/article2\nhttps://example.com/article3`}
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  onBlur={field.onBlur}
                  name={field.name}
                  ref={field.ref}
                />
              </FormControl>
              <FormMessage />
              <p className="text-xs text-muted-foreground">
                支持换行、分号或逗号分隔多个 URL
              </p>
            </FormItem>
          )}
        />
        <Button type="submit" disabled={mutation.isPending || urlCount === 0}>
          {mutation.isPending ? "提交中..." : `批量抓取 (${urlCount})`}
        </Button>
      </form>
    </Form>
  )
}

function Submit() {
  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">手动投稿</h1>
        <p className="text-muted-foreground">
          直接粘贴文章内容或提交 URL 进行 AI 分析
        </p>
      </div>
      <Tabs defaultValue="text">
        <TabsList>
          <TabsTrigger value="text">粘贴正文</TabsTrigger>
          <TabsTrigger value="url">URL 抓取</TabsTrigger>
        </TabsList>
        <TabsContent value="text" className="mt-4">
          <TextSubmitForm />
        </TabsContent>
        <TabsContent value="url" className="mt-4">
          <UrlSubmitForm />
        </TabsContent>
      </Tabs>
    </div>
  )
}
