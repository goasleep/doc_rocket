"""Base agent class, AgentRunContext, and factory function."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AgentRunContext:
    """Tracks state for a single agent run."""
    iteration_count: int = 0
    tools_used: set[str] = field(default_factory=set)
    skills_activated: set[str] = field(default_factory=set)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    compressed_count: int = 0  # Track how many times compression occurred


@dataclass
class AgentContext:
    """Context for tracking token usage and entity information."""
    entity_type: str = ""  # "article", "workflow", "task", "draft"
    entity_id: str | None = None  # UUID as string
    operation: str = ""  # "refine", "analyze", "rewrite", "chat"


class BaseAgent:
    """Base class for all content intelligence agents.

    Holds the agent configuration and LLM client.
    Subclasses implement run() with role-specific logic.
    """

    def __init__(self, agent_config: Any | None = None) -> None:
        self.agent_config = agent_config
        self.bg_manager: Any | None = None  # Initialized lazily

    async def _get_llm(self) -> Any:
        from app.core.llm.factory import get_llm_client_by_config_name

        config_name = getattr(self.agent_config, "model_config_name", "") if self.agent_config else ""
        if config_name:
            return await get_llm_client_by_config_name(config_name)

        # Fallback: use the first active LLMModelConfig
        from app.models import LLMModelConfig
        first = await LLMModelConfig.find_one(LLMModelConfig.is_active == True)  # noqa: E712
        if first:
            return await get_llm_client_by_config_name(first.name)

        raise RuntimeError("No LLM model config found. Please add one in the model config page.")

    def _base_system_prompt(self) -> str:
        if self.agent_config and self.agent_config.system_prompt:
            return self.agent_config.system_prompt
        return "你是一位专业的内容创作助手。"

    async def _build_system_prompt(self) -> str:
        """Build system prompt with optional skill catalog appended."""
        base = self._base_system_prompt()

        if not self.agent_config:
            return base

        skill_names: list[str] = getattr(self.agent_config, "skills", [])
        if not skill_names:
            return base

        from app.models import Skill
        skills = await Skill.find(
            Skill.name.in_(skill_names),  # type: ignore[attr-defined]
            Skill.is_active == True,  # noqa: E712
        ).to_list()

        if not skills:
            return base

        catalog_parts = ["<available_skills>"]
        for skill in skills:
            catalog_parts.append(f'  <skill name="{skill.name}">{skill.description}</skill>')
        catalog_parts.append("</available_skills>")
        catalog_parts.append("\nTo use a skill, call the load_skill(name) tool.")

        return base + "\n\n" + "\n".join(catalog_parts)

    async def _build_tools_schema(self) -> list[dict[str, Any]] | None:
        """Build OpenAI tool definitions from AgentConfig.tools, filtered by DB + registry."""
        if not self.agent_config:
            return None

        tool_names: list[str] = getattr(self.agent_config, "tools", [])
        if not tool_names:
            return None

        from app.models import Tool
        from app.core.tools.registry import TOOL_REGISTRY

        db_tools = await Tool.find(
            Tool.name.in_(tool_names),  # type: ignore[attr-defined]
            Tool.is_active == True,  # noqa: E712
        ).to_list()

        definitions: list[dict[str, Any]] = []
        for tool in db_tools:
            if tool.name not in TOOL_REGISTRY:
                continue
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            })

        return definitions if definitions else None

    async def _check_and_compress(
        self,
        messages: list[dict[str, Any]],
        llm: Any,
        workflow_run_id: str | None = None,
        force: bool = False,
    ) -> bool:
        """Check if compression is needed and perform it.

        Returns True if compression was performed.
        """
        from app.core.agents.compression import ContextCompressor

        compressor = ContextCompressor()

        if not force and not compressor.should_compress(messages):
            return False

        # Use microcompact for first compression, full compact for subsequent
        if len(messages) > 20:
            compressed, transcript_id = await compressor.compact(messages, llm, workflow_run_id)
            messages.clear()
            messages.extend(compressed)
        else:
            # Just microcompact for smaller contexts
            compressed = compressor.microcompact(messages)
            messages.clear()
            messages.extend(compressed)

        return True

    async def run(self, input_text: str, context: AgentContext | None = None) -> str:
        """Agentic event loop: reason → tool_call → execute → observe → repeat."""
        from app.core.agents.background import BackgroundTaskManager

        llm = await self._get_llm()
        self._last_llm = llm  # Store for token usage recording
        system_prompt = await self._build_system_prompt()
        tools_schema = await self._build_tools_schema()

        max_iterations = getattr(self.agent_config, "max_iterations", 5) if self.agent_config else 5
        ctx = AgentRunContext()

        # Initialize background task manager
        self.bg_manager = BackgroundTaskManager()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ]

        last_content: str = ""
        consecutive_failures: dict[str, int] = {}

        while ctx.iteration_count < max_iterations:
            ctx.iteration_count += 1

            # Check for context compression before LLM call
            workflow_run_id = getattr(self, "_current_workflow_run_id", None)
            compressed = await self._check_and_compress(messages, llm, workflow_run_id)
            if compressed:
                ctx.compressed_count += 1

            # Check for background task notifications
            if self.bg_manager:
                notifications = self.bg_manager.drain_notifications()
                if notifications:
                    notification_msg = self.bg_manager.format_notifications(notifications)
                    if notification_msg:
                        messages.append({
                            "role": "system",
                            "content": notification_msg,
                        })

            response = await llm.chat(messages, tools=tools_schema)

            # Record token usage if context is provided
            if context:
                await self._record_token_usage(response, context)

            if not response.tool_calls:
                # Final answer
                return response.content or last_content

            # Append assistant message with tool calls
            tool_calls_payload = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": str(tc.arguments)},
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

            if response.content:
                last_content = response.content

            # Dispatch each tool call
            from app.core.tools.registry import dispatch_tool
            should_terminate = False

            for tc in response.tool_calls:
                ctx.tools_used.add(tc.name)

                # Special handling for background_run to track the task
                if tc.name == "background_run" and self.bg_manager:
                    # First dispatch to create the Celery task
                    result = await dispatch_tool(tc.name, tc.arguments, context={
                        "messages": messages,
                        "workflow_run_id": workflow_run_id,
                    })

                    # Extract task_id from result and register with manager
                    import re
                    task_id_match = re.search(r"Task ID: ([a-f0-9-]+)", result)
                    if task_id_match:
                        task_id = task_id_match.group(1)
                        command = tc.arguments.get("command", "unknown")
                        await self.bg_manager.submit(task_id, command)
                        result += f"\n[Task registered with agent. You'll be notified when it completes.]"
                else:
                    result = await dispatch_tool(tc.name, tc.arguments, context={
                        "messages": messages,
                        "workflow_run_id": workflow_run_id,
                    })

                # Track failures for circuit breaker
                is_error = result.startswith(f"Tool '{tc.name}' error:") or result.startswith(f"Tool '{tc.name}' is not available")
                if is_error:
                    consecutive_failures[tc.name] = consecutive_failures.get(tc.name, 0) + 1
                    if consecutive_failures[tc.name] >= 3:
                        result += f"\n[Circuit breaker: '{tc.name}' failed 3 consecutive times. Terminating loop.]"
                        should_terminate = True
                else:
                    consecutive_failures[tc.name] = 0

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            if should_terminate:
                break

        # max_iterations reached or circuit breaker triggered
        return last_content

    async def _record_token_usage(
        self,
        response: Any,
        context: AgentContext,
    ) -> None:
        """Record token usage after an LLM call.

        Args:
            response: The ChatResponse from the LLM call
            context: The AgentContext containing entity and operation info
        """
        import uuid

        from app.services.token_usage import TokenUsageService

        # Get agent config info
        agent_config_id = None
        agent_config_name = ""
        if self.agent_config:
            agent_config_id = getattr(self.agent_config, "id", None)
            agent_config_name = getattr(self.agent_config, "name", "")

        # Get model name from LLM client
        model_name = ""
        if hasattr(self, "_last_llm") and self._last_llm:
            model_name = getattr(self._last_llm, "model_name", "")

        # Extract usage data
        usage = getattr(response, "usage", None)
        if usage:
            prompt_tokens = getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "completion_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", 0)
            usage_missing = False
        else:
            prompt_tokens = completion_tokens = total_tokens = 0
            usage_missing = True

        # Parse entity_id as UUID if provided
        entity_id_uuid = None
        if context.entity_id:
            try:
                entity_id_uuid = uuid.UUID(context.entity_id)
            except ValueError:
                pass

        # Parse agent_config_id as UUID if needed
        agent_id_uuid = None
        if agent_config_id:
            try:
                if isinstance(agent_config_id, str):
                    agent_id_uuid = uuid.UUID(agent_config_id)
                else:
                    agent_id_uuid = agent_config_id
            except ValueError:
                pass

        await TokenUsageService.record_usage(
            agent_config_id=agent_id_uuid,
            agent_config_name=agent_config_name,
            model_name=model_name,
            entity_type=context.entity_type,
            entity_id=entity_id_uuid,
            operation=context.operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            usage_missing=usage_missing,
        )


def create_agent_for_config(agent_config: Any) -> "BaseAgent":
    """Instantiate the right agent subclass based on agent_config.role."""
    if agent_config is None:
        return BaseAgent()

    role = agent_config.role

    if role == "writer":
        from app.core.agents.writer import WriterAgent
        return WriterAgent(agent_config=agent_config)
    elif role == "editor":
        from app.core.agents.editor import EditorAgent
        return EditorAgent(agent_config=agent_config)
    elif role == "reviewer":
        from app.core.agents.reviewer import ReviewerAgent
        return ReviewerAgent(agent_config=agent_config)
    elif role == "orchestrator":
        from app.core.agents.orchestrator import OrchestratorAgent
        return OrchestratorAgent(agent_config=agent_config)
    elif role == "analyzer":
        from app.core.agents.react_analyzer import ReactAnalyzerAgent
        return ReactAnalyzerAgent(agent_config=agent_config)
    elif role == "refiner":
        from app.core.agents.refiner import RefinerAgent
        return RefinerAgent(agent_config=agent_config)
    else:
        return BaseAgent(agent_config=agent_config)
