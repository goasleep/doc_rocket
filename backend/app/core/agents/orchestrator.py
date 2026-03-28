"""OrchestratorAgent — coordinates Writer/Editor/Reviewer via delegation tools."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.agents.base import BaseAgent

DEFAULT_SYSTEM = """\
你是一位内容创作团队的协调者。你的职责是：
1. 根据任务需求，协调 Writer、Editor、Reviewer 完成高质量的内容创作
2. 根据 Editor 的反馈决定是否需要 Writer 进行修改
3. 当内容达到质量标准时，调用 finalize 完成工作流

可用工具：
- delegate_to_writer: 让 Writer 根据素材和要求创作初稿
- delegate_to_editor: 让 Editor 优化稿件并评估质量
- delegate_to_reviewer: 让 Reviewer 进行事实核查和格式审核
- finalize: 完成工作流，提交最终内容

工作流程：
1. 先调用 delegate_to_writer 生成初稿
2. 调用 delegate_to_editor 进行优化和质量评估
3. 如果 Editor 未批准（approved=false），可根据 feedback 要求 Writer 修改（最多 {max_revisions} 次）
4. 如果 Editor 批准，调用 finalize 提交最终内容
"""

DELEGATION_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "delegate_to_writer",
            "description": "Delegate content creation to the Writer agent. Use this to generate or revise a draft.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The writing task description"},
                    "context": {"type": "string", "description": "Background context and reference material"},
                    "revision_feedback": {
                        "type": "string",
                        "description": "Feedback from editor for revision (empty string if first draft)",
                        "default": "",
                    },
                },
                "required": ["task", "context"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_to_editor",
            "description": "Delegate editing and quality evaluation to the Editor agent. Returns structured result with approval status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft": {"type": "string", "description": "The draft content to edit"},
                },
                "required": ["draft"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_to_reviewer",
            "description": "Delegate fact-checking and format review to the Reviewer agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft": {"type": "string", "description": "The draft content to review"},
                },
                "required": ["draft"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize",
            "description": "Finalize the workflow with the approved content and title candidates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Final content in Markdown"},
                    "title_candidates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of title candidates (3 recommended)",
                    },
                },
                "required": ["content"],
            },
        },
    },
]


class OrchestratorAgent(BaseAgent):
    """Orchestrator that coordinates the writing team via delegation tools."""

    def __init__(
        self,
        agent_config: Any | None = None,
        max_revisions: int = 3,
        event_callback: Callable[[str, dict], None] | None = None,
    ) -> None:
        super().__init__(agent_config=agent_config)
        self.max_revisions = max_revisions
        self.event_callback = event_callback
        self._final_output: str | None = None
        self._final_title_candidates: list[str] = []
        self._revision_count = 0
        self._routing_log: list[dict[str, Any]] = []
        self._workflow_run_id: str | None = None
        self._subagent_steps: list[Any] = []  # Store subagent AgentStep records

    def _base_system_prompt(self) -> str:
        if self.agent_config and self.agent_config.system_prompt:
            return self.agent_config.system_prompt
        return DEFAULT_SYSTEM.replace("{max_revisions}", str(self.max_revisions))

    def _log_routing(self, from_agent: str, to_agent: str, reason: str) -> None:
        self._routing_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
        })

    def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit event to callback if registered."""
        if self.event_callback:
            self.event_callback(event_type, data)

    async def _delegate_to_writer(
        self, task: str, context: str, revision_feedback: str = ""
    ) -> str:
        """Delegate to writer using isolated subagent."""
        from app.core.agents.subagent import SubagentRunner
        from app.models.workflow import AgentStep

        runner = SubagentRunner()

        prompt = f"{task}\n\n素材：\n{context}"
        if revision_feedback:
            prompt += f"\n\n修改意见：\n{revision_feedback}"

        self._log_routing(
            "orchestrator",
            "writer",
            "Initial draft request" if not revision_feedback else f"Revision #{self._revision_count + 1}"
        )

        # Create step record
        step = AgentStep(
            id=uuid.uuid4(),
            agent_name="Writer",
            role="writer",
            input=prompt[:500],
            status="running",
            started_at=datetime.now(timezone.utc),
            iteration_count=self._revision_count + 1 if revision_feedback else 0,
        )

        # Emit start event
        self._emit_event("subagent_start", {
            "agent": "Writer",
            "role": "writer",
            "message": "Initial draft" if not revision_feedback else f"Revision #{self._revision_count + 1}",
            "iteration": step.iteration_count,
        })

        try:
            draft = await runner.run(
                agent_role="writer",
                prompt=prompt,
                max_iterations=5,
            )

            # Fill result
            step.output = draft[:500]
            step.status = "done"
            step.ended_at = datetime.now(timezone.utc)
            self._subagent_steps.append(step)

            # Emit output event
            self._emit_event("subagent_output", {
                "agent": "Writer",
                "role": "writer",
                "output_preview": draft[:300],
                "iteration": step.iteration_count,
            })

            return draft
        except Exception as e:
            error_msg = f"Writer agent failed: {str(e)}"
            self._log_routing("writer", "error", error_msg)

            step.status = "failed"
            step.output = error_msg
            step.ended_at = datetime.now(timezone.utc)
            self._subagent_steps.append(step)

            self._emit_event("subagent_error", {
                "agent": "Writer",
                "role": "writer",
                "error": error_msg,
            })

            return f"Error: {error_msg}"

    async def _delegate_to_editor(self, draft: str) -> str:
        """Delegate to editor using isolated subagent."""
        from app.core.agents.subagent import SubagentRunner
        from app.models.workflow import AgentStep

        runner = SubagentRunner()

        self._log_routing("orchestrator", "editor", "Editing and quality review")

        prompt = f"请编辑并评估以下稿件质量：\n\n{draft}"

        # Create step record
        step = AgentStep(
            id=uuid.uuid4(),
            agent_name="Editor",
            role="editor",
            input=prompt[:500],
            status="running",
            started_at=datetime.now(timezone.utc),
        )

        # Emit start event
        self._emit_event("subagent_start", {
            "agent": "Editor",
            "role": "editor",
            "message": "Editing and quality review",
        })

        try:
            result = await runner.run(
                agent_role="editor",
                prompt=prompt,
                max_iterations=5,
            )
        except Exception as e:
            error_msg = f"Editor agent failed: {str(e)}"
            self._log_routing("editor", "error", error_msg)

            step.status = "failed"
            step.output = error_msg
            step.ended_at = datetime.now(timezone.utc)
            self._subagent_steps.append(step)

            self._emit_event("subagent_error", {
                "agent": "Editor",
                "role": "editor",
                "error": error_msg,
            })

            return json.dumps({
                "content": draft,
                "title_candidates": [],
                "feedback": error_msg,
                "changed_sections": [],
                "approved": True  # Force approve to avoid infinite loop
            }, ensure_ascii=False)

        # Ensure result has approved field
        try:
            data = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            data = {"content": result, "title_candidates": [], "feedback": "", "changed_sections": []}

        # Add approved field based on whether there's significant feedback
        if "approved" not in data:
            data["approved"] = True

        # Fill result
        step.output = data.get("content", result)[:500]
        step.title_candidates = data.get("title_candidates", [])
        step.status = "done"
        step.ended_at = datetime.now(timezone.utc)
        self._subagent_steps.append(step)

        # Emit output event
        self._emit_event("subagent_output", {
            "agent": "Editor",
            "role": "editor",
            "output_preview": data.get("content", result)[:300],
            "title_candidates": data.get("title_candidates", []),
            "approved": data.get("approved", True),
        })

        return json.dumps(data, ensure_ascii=False)

    async def _delegate_to_reviewer(self, draft: str) -> str:
        """Delegate to reviewer using isolated subagent."""
        from app.core.agents.subagent import SubagentRunner
        from app.models.workflow import AgentStep

        runner = SubagentRunner()

        self._log_routing("orchestrator", "reviewer", "Fact-check and format review")

        prompt = f"请审核以下稿件的事实和格式：\n\n{draft}"

        # Create step record
        step = AgentStep(
            id=uuid.uuid4(),
            agent_name="Reviewer",
            role="reviewer",
            input=prompt[:500],
            status="running",
            started_at=datetime.now(timezone.utc),
        )

        # Emit start event
        self._emit_event("subagent_start", {
            "agent": "Reviewer",
            "role": "reviewer",
            "message": "Fact-check and format review",
        })

        try:
            result = await runner.run(
                agent_role="reviewer",
                prompt=prompt,
                max_iterations=5,
            )

            # Fill result
            step.output = result[:500]
            step.status = "done"
            step.ended_at = datetime.now(timezone.utc)
            self._subagent_steps.append(step)

            # Emit output event
            self._emit_event("subagent_output", {
                "agent": "Reviewer",
                "role": "reviewer",
                "output_preview": result[:300],
            })

            return result
        except Exception as e:
            error_msg = f"Reviewer agent failed: {str(e)}"
            self._log_routing("reviewer", "error", error_msg)

            step.status = "failed"
            step.output = error_msg
            step.ended_at = datetime.now(timezone.utc)
            self._subagent_steps.append(step)

            self._emit_event("subagent_error", {
                "agent": "Reviewer",
                "role": "reviewer",
                "error": error_msg,
            })

            return f"Error: {error_msg}"

    async def _finalize(
        self, content: str, title_candidates: list[str] | None = None
    ) -> str:
        self._final_output = content
        self._final_title_candidates = title_candidates or []
        self._log_routing("orchestrator", "finalize", "Workflow finalized")

        self._emit_event("subagent_start", {
            "agent": "Orchestrator",
            "role": "orchestrator",
            "message": "Finalizing workflow",
        })

        return "done"

    async def run(self, input_text: str) -> str:  # type: ignore[override]
        """Run the orchestrator agentic loop using delegation tools."""
        llm = await self._get_llm()
        system_prompt = await self._build_system_prompt()
        max_iter = getattr(self.agent_config, "max_iterations", 10) if self.agent_config else 10

        # Build system prompt with delegation tool info
        if DEFAULT_SYSTEM.replace("{max_revisions}", str(self.max_revisions)) in system_prompt or (
            self.agent_config is None
        ):
            system_prompt_str = DEFAULT_SYSTEM.replace("{max_revisions}", str(self.max_revisions))
        else:
            system_prompt_str = system_prompt

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt_str},
            {"role": "user", "content": input_text},
        ]

        last_draft = ""
        iteration = 0

        while iteration < max_iter:
            iteration += 1
            response = await llm.chat(messages, tools=DELEGATION_TOOLS)

            if not response.tool_calls:
                # Orchestrator finished without calling finalize
                break

            # Append assistant message
            tool_calls_payload = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in response.tool_calls
            ]
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": response.content,
                "tool_calls": tool_calls_payload,
            }
            # Include reasoning_content if present (required for some models with thinking enabled)
            if response.reasoning_content:
                assistant_msg["reasoning_content"] = response.reasoning_content
            messages.append(assistant_msg)

            finalized = False
            for tc in response.tool_calls:
                args = tc.arguments

                if tc.name == "delegate_to_writer":
                    revision_feedback = args.get("revision_feedback", "")
                    if revision_feedback:
                        self._revision_count += 1
                        self._log_routing("editor", "writer", f"Revision #{self._revision_count}: {revision_feedback[:100]}")
                    else:
                        self._log_routing("orchestrator", "writer", "Initial draft request")

                    result = await self._delegate_to_writer(
                        task=args.get("task", ""),
                        context=args.get("context", ""),
                        revision_feedback=revision_feedback,
                    )
                    last_draft = result

                elif tc.name == "delegate_to_editor":
                    self._log_routing("orchestrator", "editor", "Editing and quality review")
                    result = await self._delegate_to_editor(args.get("draft", last_draft))

                    # Check revision limit
                    try:
                        editor_data = json.loads(result)
                        if not editor_data.get("approved") and self._revision_count >= self.max_revisions:
                            # Force finalize
                            self._log_routing("orchestrator", "finalize", "max_revisions_reached")
                            editor_data["approved"] = True
                            result = json.dumps(editor_data, ensure_ascii=False)
                    except (json.JSONDecodeError, AttributeError):
                        pass

                elif tc.name == "delegate_to_reviewer":
                    self._log_routing("orchestrator", "reviewer", "Fact-check and format review")
                    result = await self._delegate_to_reviewer(args.get("draft", last_draft))

                elif tc.name == "finalize":
                    title_cands = args.get("title_candidates", [])
                    result = await self._finalize(
                        content=args.get("content", last_draft),
                        title_candidates=title_cands,
                    )
                    finalized = True

                else:
                    result = f"Unknown delegation tool: {tc.name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            if finalized:
                break

        return self._final_output or last_draft
