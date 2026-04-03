import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useForm, Controller } from "react-hook-form"
import { useState } from "react"

import { SystemConfigService, type SystemConfigUpdate, type SystemConfigPublic } from "@/client"
import { Button } from "@/components/ui/button"

// Extended types for word cloud filter (not yet in generated client)
type WordCloudFilterConfig = {
  excluded_keywords: string[]
  min_keyword_length: number
  max_keyword_count: number
}

interface ExtendedSystemConfigPublic extends SystemConfigPublic {
  word_cloud_filter?: WordCloudFilterConfig
}

interface ExtendedSystemConfigUpdate extends SystemConfigUpdate {
  word_cloud_filter?: WordCloudFilterConfig
  excluded_keywords?: string[]
  min_keyword_length?: number
  max_keyword_count?: number
}
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import useCustomToast from "@/hooks/useCustomToast"

function ProviderKeyField({
  label,
  maskedKey,
  fieldName,
  register,
}: {
  label: string
  maskedKey?: string | null
  fieldName: string
  register: ReturnType<typeof useForm>["register"]
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">{label}</label>
        {maskedKey && (
          <span className="text-xs text-muted-foreground font-mono">
            {maskedKey}
          </span>
        )}
      </div>
      <Input
        type="password"
        placeholder={maskedKey ? "输入新 Key 以替换..." : "未配置"}
        {...register(fieldName)}
      />
    </div>
  )
}

export function SystemSettings() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [newKeyword, setNewKeyword] = useState("")

  const { data: config, isLoading } = useQuery<ExtendedSystemConfigPublic>({
    queryKey: ["system-config"],
    queryFn: () => SystemConfigService.getSystemConfig() as Promise<ExtendedSystemConfigPublic>,
  })

  const { register, handleSubmit, reset, control, watch, setValue } = useForm<ExtendedSystemConfigUpdate>()

  // Watch excluded keywords for UI updates
  const excludedKeywords = watch("excluded_keywords") || config?.word_cloud_filter?.excluded_keywords || []

  const updateMutation = useMutation({
    mutationFn: (data: SystemConfigUpdate) =>
      SystemConfigService.updateSystemConfig({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system-config"] })
      showSuccessToast("系统配置已保存")
      reset()
    },
    onError: () => showErrorToast("保存失败"),
  })

  function onSubmit(values: ExtendedSystemConfigUpdate) {
    // Only send non-empty values
    const payload: ExtendedSystemConfigUpdate = {}
    if (values.kimi_api_key) payload.kimi_api_key = values.kimi_api_key
    if (values.claude_api_key) payload.claude_api_key = values.claude_api_key
    if (values.openai_api_key) payload.openai_api_key = values.openai_api_key

    // Include word cloud filter config
    const wordCloudFilter = {
      excluded_keywords: values.excluded_keywords || config?.word_cloud_filter?.excluded_keywords || [],
      min_keyword_length: values.min_keyword_length ?? config?.word_cloud_filter?.min_keyword_length ?? 2,
      max_keyword_count: values.max_keyword_count ?? config?.word_cloud_filter?.max_keyword_count ?? 100,
    }
    payload.word_cloud_filter = wordCloudFilter

    updateMutation.mutate(payload as SystemConfigUpdate)
  }

  const addExcludedKeyword = () => {
    if (!newKeyword.trim()) return
    const current = excludedKeywords || []
    if (!current.includes(newKeyword.trim())) {
      setValue("excluded_keywords", [...current, newKeyword.trim()])
    }
    setNewKeyword("")
  }

  const removeExcludedKeyword = (keyword: string) => {
    const current = excludedKeywords || []
    setValue("excluded_keywords", current.filter((k: string) => k !== keyword))
  }

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">加载中...</div>
  }

  if (!config) {
    return <div className="text-sm text-muted-foreground">系统配置未初始化</div>
  }

  return (
    <div className="space-y-6 max-w-xl">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">API Key 管理</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ProviderKeyField
              label="Kimi (Moonshot)"
              maskedKey={config.llm_providers.kimi.api_key_masked}
              fieldName="kimi_api_key"
              register={register}
            />
            <ProviderKeyField
              label="Claude (Anthropic)"
              maskedKey={config.llm_providers.claude.api_key_masked}
              fieldName="claude_api_key"
              register={register}
            />
            <ProviderKeyField
              label="OpenAI"
              maskedKey={config.llm_providers.openai.api_key_masked}
              fieldName="openai_api_key"
              register={register}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">调度器配置</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">
                默认抓取间隔（分钟）
              </label>
              <div className="text-sm text-muted-foreground">
                {config.scheduler.default_interval_minutes} 分钟
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">最大并发抓取数</label>
              <div className="text-sm text-muted-foreground">
                {config.scheduler.max_concurrent_fetches} 个
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">模型默认配置</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <span className="text-muted-foreground">分析模型：</span>
              {config.analysis.default_model_provider} /{" "}
              {config.analysis.default_model_id}
            </div>
            <div>
              <span className="text-muted-foreground">写作模型：</span>
              {config.writing.default_model_provider} /{" "}
              {config.writing.default_model_id}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">词云过滤配置</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">过滤关键词</label>
              <p className="text-xs text-muted-foreground">
                这些关键词将不会出现在词云中
              </p>
              <div className="flex flex-wrap gap-2">
                {(excludedKeywords || []).map((keyword: string) => (
                  <Badge
                    key={keyword}
                    variant="secondary"
                    className="cursor-pointer hover:bg-destructive hover:text-destructive-foreground"
                    onClick={() => removeExcludedKeyword(keyword)}
                  >
                    {keyword} ×
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder="输入关键词..."
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      addExcludedKeyword()
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={addExcludedKeyword}
                >
                  添加
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">最大关键词数量</label>
              <Controller
                name="max_keyword_count"
                control={control}
                defaultValue={config?.word_cloud_filter?.max_keyword_count || 100}
                render={({ field }) => (
                  <Input
                    type="number"
                    min={10}
                    max={500}
                    {...field}
                    onChange={(e) => field.onChange(parseInt(e.target.value))}
                  />
                )}
              />
              <p className="text-xs text-muted-foreground">
                词云中显示的最大关键词数量（10-500）
              </p>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? "保存中..." : "保存配置"}
        </Button>
      </form>
    </div>
  )
}
