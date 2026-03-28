import { useMemo } from "react"
import { Badge } from "@/components/ui/badge"

interface RoutingEvent {
  timestamp?: string
  from_agent: string
  to_agent: string
  reason?: string
}

interface AgentNode {
  id: string
  label: string
  color: string
  x: number
  y: number
}

interface AgentEdge {
  from: string
  to: string
  reason?: string
  count: number
}

const AGENT_COLORS: Record<string, string> = {
  orchestrator: "#3b82f6", // blue-500
  writer: "#10b981", // emerald-500
  editor: "#f59e0b", // amber-500
  reviewer: "#8b5cf6", // violet-500
  finalize: "#22c55e", // green-500
  error: "#ef4444", // red-500
}

function getAgentColor(agent: string): string {
  const key = agent.toLowerCase()
  for (const [name, color] of Object.entries(AGENT_COLORS)) {
    if (key.includes(name)) return color
  }
  return "#6b7280" // gray-500
}

function getAgentLabel(agent: string): string {
  const labels: Record<string, string> = {
    orchestrator: "协调者",
    writer: "写手",
    editor: "编辑",
    reviewer: "审核",
    finalize: "完成",
    error: "错误",
  }
  const key = agent.toLowerCase()
  for (const [name, label] of Object.entries(labels)) {
    if (key.includes(name)) return label
  }
  return agent
}

export function AgentGraph({ routingLog }: { routingLog: RoutingEvent[] }) {
  const { nodes, edges, iterations } = useMemo(() => {
    if (!routingLog || routingLog.length === 0) {
      return { nodes: [], edges: [], iterations: 0 }
    }

    // Count edge frequencies and collect reasons
    const edgeMap = new Map<string, AgentEdge>()
    const uniqueAgents = new Set<string>()
    let iterationCount = 0

    routingLog.forEach((event) => {
      const from = event.from_agent
      const to = event.to_agent
      uniqueAgents.add(from)
      uniqueAgents.add(to)

      const key = `${from}→${to}`
      const existing = edgeMap.get(key)
      if (existing) {
        existing.count++
      } else {
        edgeMap.set(key, { from, to, reason: event.reason, count: 1 })
      }

      // Count writer→editor cycles as iterations
      if (from === "writer" && to === "editor") {
        iterationCount++
      }
    })

    // Position nodes in a flow layout
    // Orchestrator at top, then writer/editor/reviewer in middle, finalize at bottom
    const agentList = Array.from(uniqueAgents)
    const nodes: AgentNode[] = agentList.map((id) => {
      let x = 200
      let y = 150

      const lowerId = id.toLowerCase()
      if (lowerId.includes("orchestrator")) {
        x = 200
        y = 40
      } else if (lowerId.includes("writer")) {
        x = 100
        y = 120
      } else if (lowerId.includes("editor")) {
        x = 200
        y = 120
      } else if (lowerId.includes("reviewer")) {
        x = 300
        y = 120
      } else if (lowerId.includes("finalize")) {
        x = 200
        y = 200
      } else if (lowerId.includes("error")) {
        x = 320
        y = 40
      }

      return {
        id,
        label: getAgentLabel(id),
        color: getAgentColor(id),
        x,
        y,
      }
    })

    return {
      nodes,
      edges: Array.from(edgeMap.values()),
      iterations: Math.max(0, iterationCount - 1),
    }
  }, [routingLog])

  if (nodes.length === 0) return null

  return (
    <div className="rounded-lg border bg-muted/30 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium">Agent 协作关系图</h4>
        {iterations > 0 && (
          <Badge variant="secondary" className="text-xs">
            修订轮次: {iterations}
          </Badge>
        )}
      </div>

      <div className="relative w-full overflow-x-auto">
        <svg
          viewBox="0 0 400 240"
          className="w-full max-w-md mx-auto"
          style={{ minWidth: "300px" }}
        >
          {/* Arrow marker definition */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="28"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#9ca3af" />
            </marker>
            <marker
              id="arrowhead-active"
              markerWidth="10"
              markerHeight="7"
              refX="28"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#3b82f6" />
            </marker>
          </defs>

          {/* Edges */}
          {edges.map((edge, i) => {
            const fromNode = nodes.find((n) => n.id === edge.from)
            const toNode = nodes.find((n) => n.id === edge.to)
            if (!fromNode || !toNode) return null

            const isReturnPath = edge.from === "editor" && edge.to === "writer"
            const isOrchestratorPath =
              edge.from === "orchestrator" || edge.to === "orchestrator"

            // Calculate curved path for return paths (editor→writer)
            let pathD = ""
            if (isReturnPath) {
              const midX = (fromNode.x + toNode.x) / 2
              const midY = (fromNode.y + toNode.y) / 2 - 40
              pathD = `M ${fromNode.x} ${fromNode.y} Q ${midX} ${midY} ${toNode.x} ${toNode.y}`
            } else {
              pathD = `M ${fromNode.x} ${fromNode.y} L ${toNode.x} ${toNode.y}`
            }

            return (
              <g key={i}>
                <path
                  d={pathD}
                  fill="none"
                  stroke={isOrchestratorPath ? "#3b82f6" : "#9ca3af"}
                  strokeWidth={Math.min(3, 1 + edge.count * 0.5)}
                  strokeDasharray={isReturnPath ? "5,3" : undefined}
                  markerEnd={`url(#${isOrchestratorPath ? "arrowhead-active" : "arrowhead"})`}
                  opacity={0.7}
                />
                {edge.count > 1 && (
                  <text
                    x={(fromNode.x + toNode.x) / 2}
                    y={(fromNode.y + toNode.y) / 2 - (isReturnPath ? 15 : 5)}
                    textAnchor="middle"
                    className="text-xs fill-muted-foreground"
                    style={{ fontSize: "10px" }}
                  >
                    ×{edge.count}
                  </text>
                )}
              </g>
            )
          })}

          {/* Nodes */}
          {nodes.map((node) => (
            <g key={node.id}>
              {/* Node circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r="20"
                fill={node.color}
                stroke="white"
                strokeWidth="2"
                className="drop-shadow-sm"
              />
              {/* Node label (inside circle for short labels) */}
              <text
                x={node.x}
                y={node.y}
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-xs font-medium fill-white"
                style={{ fontSize: "11px" }}
              >
                {node.label}
              </text>
              {/* Node id below */}
              <text
                x={node.x}
                y={node.y + 32}
                textAnchor="middle"
                className="text-xs fill-muted-foreground"
                style={{ fontSize: "10px" }}
              >
                {node.id}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3 text-xs text-muted-foreground justify-center">
        <div className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: AGENT_COLORS.orchestrator }}
          />
          <span>协调者</span>
        </div>
        <div className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: AGENT_COLORS.writer }}
          />
          <span>写手</span>
        </div>
        <div className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: AGENT_COLORS.editor }}
          />
          <span>编辑</span>
        </div>
        <div className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: AGENT_COLORS.reviewer }}
          />
          <span>审核</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-6 h-0.5 bg-blue-500" />
          <span>协调路径</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-6 h-0.5 bg-gray-400" />
          <span>普通路径</span>
        </div>
        <div className="flex items-center gap-1">
          <span
            className="w-6 h-0.5 bg-gray-400 border-dashed"
            style={{ borderTop: "1px dashed #9ca3af", height: 0 }}
          />
          <span>返回修改</span>
        </div>
      </div>
    </div>
  )
}
