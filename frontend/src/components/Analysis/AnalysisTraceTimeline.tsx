import {
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Eye,
  FileText,
  Lightbulb,
  Loader2,
  Wrench,
  XCircle,
} from "lucide-react"
import { useState } from "react"
import type { AnalysisTraceStep } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface AnalysisTraceTimelineProps {
  trace: AnalysisTraceStep[]
}

const stepTypeLabels: Record<string, string> = {
  thought: "思考",
  tool_call: "工具调用",
  observation: "观察",
  conclusion: "结论",
  reflection: "反思",
}

const stepTypeIcons: Record<string, React.ReactNode> = {
  thought: <Brain className="h-4 w-4" />,
  tool_call: <Wrench className="h-4 w-4" />,
  observation: <Eye className="h-4 w-4" />,
  conclusion: <FileText className="h-4 w-4" />,
  reflection: <Lightbulb className="h-4 w-4" />,
}

const stepTypeColors: Record<string, string> = {
  thought: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  tool_call:
    "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
  observation:
    "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  conclusion:
    "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
  reflection: "bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300",
}

interface GroupedSteps {
  parallelGroup: string | null
  steps: AnalysisTraceStep[]
}

function groupStepsByParallelGroup(trace: AnalysisTraceStep[]): GroupedSteps[] {
  const groups: GroupedSteps[] = []
  let currentGroup: GroupedSteps | null = null

  for (const step of trace) {
    const groupId = step.parallel_group || null

    if (currentGroup === null || currentGroup.parallelGroup !== groupId) {
      currentGroup = {
        parallelGroup: groupId,
        steps: [step],
      }
      groups.push(currentGroup)
    } else {
      currentGroup.steps.push(step)
    }
  }

  return groups
}

function TraceStepCard({
  step,
  index,
}: {
  step: AnalysisTraceStep
  index: number
}) {
  const [expanded, setExpanded] = useState(false)
  const stepType = step.step_type || "thought"
  const stepName = step.step_name || `步骤 ${index + 1}`

  return (
    <div className="border rounded-lg overflow-hidden bg-card">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-muted/50 transition-colors text-left"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        )}

        <div
          className={`p-1.5 rounded-md shrink-0 ${stepTypeColors[stepType] || stepTypeColors.thought}`}
        >
          {stepTypeIcons[stepType] || stepTypeIcons.thought}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{stepName}</span>
            <Badge variant="outline" className="text-xs">
              {stepTypeLabels[stepType] || stepType}
            </Badge>
          </div>
          {step.input_summary && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {step.input_summary}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {step.duration_ms != null && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {step.duration_ms}ms
            </span>
          )}
          {step.parsed_ok ? (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          ) : (
            <XCircle className="h-4 w-4 text-destructive" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t bg-muted/30">
          <div className="pt-3 space-y-3">
            {step.input_summary && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  输入
                </div>
                <p className="text-sm">{step.input_summary}</p>
              </div>
            )}

            {step.output_summary && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  输出
                </div>
                <p className="text-sm">{step.output_summary}</p>
              </div>
            )}

            {step.tool_calls && step.tool_calls.length > 0 && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-2">
                  工具调用
                </div>
                <div className="space-y-2">
                  {step.tool_calls.map((toolCall, idx) => (
                    <div key={idx} className="bg-muted rounded p-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Wrench className="h-3 w-3 text-muted-foreground" />
                        <span className="font-mono font-medium">
                          {toolCall.tool_name}
                        </span>
                        {toolCall.success ? (
                          <Badge
                            variant="outline"
                            className="text-xs text-green-600"
                          >
                            成功
                          </Badge>
                        ) : (
                          <Badge variant="destructive" className="text-xs">
                            失败
                          </Badge>
                        )}
                      </div>
                      {toolCall.input_params && (
                        <pre className="mt-1 text-xs text-muted-foreground overflow-auto max-h-20">
                          {JSON.stringify(toolCall.input_params, null, 2)}
                        </pre>
                      )}
                      {toolCall.output_summary && (
                        <div className="mt-1 text-xs text-muted-foreground">
                          {toolCall.output_summary}
                        </div>
                      )}
                      {toolCall.error_message && (
                        <div className="mt-1 text-xs text-destructive">
                          {toolCall.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {step.raw_response && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  原始响应
                </div>
                <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40 whitespace-pre-wrap">
                  {step.raw_response}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function ParallelGroupCard({
  group,
  startIndex,
}: {
  group: GroupedSteps
  startIndex: number
}) {
  const [expanded, setExpanded] = useState(true)

  if (!group.parallelGroup) {
    // Sequential steps - render individually
    return (
      <>
        {group.steps.map((step, idx) => (
          <TraceStepCard
            key={startIndex + idx}
            step={step}
            index={startIndex + idx}
          />
        ))}
      </>
    )
  }

  // Parallel group
  return (
    <div className="border-2 border-dashed border-primary/30 rounded-lg p-3 space-y-2 bg-primary/5">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 text-sm font-medium text-primary"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        <Loader2 className="h-4 w-4" />
        并行分析组: {group.parallelGroup}
        <Badge variant="outline" className="text-xs ml-2">
          {group.steps.length} 个步骤
        </Badge>
      </button>

      {expanded && (
        <div className="space-y-2 pl-4 border-l-2 border-primary/20">
          {group.steps.map((step, idx) => (
            <TraceStepCard
              key={startIndex + idx}
              step={step}
              index={startIndex + idx}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function AnalysisTraceTimeline({ trace }: AnalysisTraceTimelineProps) {
  const [allExpanded, setAllExpanded] = useState(false)

  if (!trace || trace.length === 0) {
    return null
  }

  const groupedSteps = groupStepsByParallelGroup(trace)
  let stepIndex = 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">分析过程追溯</h3>
          <Badge variant="outline">{trace.length} 步</Badge>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setAllExpanded(!allExpanded)}
        >
          {allExpanded ? "全部折叠" : "全部展开"}
        </Button>
      </div>

      <div className="space-y-3">
        {groupedSteps.map((group, groupIdx) => {
          const currentIndex = stepIndex
          stepIndex += group.steps.length
          return (
            <ParallelGroupCard
              key={groupIdx}
              group={group}
              startIndex={currentIndex}
            />
          )
        })}
      </div>
    </div>
  )
}
