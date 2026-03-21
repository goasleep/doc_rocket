import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"

import { SystemConfigService, type SystemConfigUpdate } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
          <span className="text-xs text-muted-foreground font-mono">{maskedKey}</span>
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

  const { data: config, isLoading } = useQuery({
    queryKey: ["system-config"],
    queryFn: () => SystemConfigService.getSystemConfig(),
  })

  const { register, handleSubmit, reset } = useForm<SystemConfigUpdate>()

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

  function onSubmit(values: SystemConfigUpdate) {
    // Only send non-empty values
    const payload: SystemConfigUpdate = {}
    if (values.kimi_api_key) payload.kimi_api_key = values.kimi_api_key
    if (values.claude_api_key) payload.claude_api_key = values.claude_api_key
    if (values.openai_api_key) payload.openai_api_key = values.openai_api_key
    updateMutation.mutate(payload)
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
              <label className="text-sm font-medium">默认抓取间隔（分钟）</label>
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
              {config.analysis.default_model_provider} / {config.analysis.default_model_id}
            </div>
            <div>
              <span className="text-muted-foreground">写作模型：</span>
              {config.writing.default_model_provider} / {config.writing.default_model_id}
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
