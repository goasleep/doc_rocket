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


class BaseAgent:
    """Base class for all content intelligence agents.

    Holds the agent configuration and LLM client.
    Subclasses implement run() with role-specific logic.
    """

    def __init__(self, agent_config: Any | None = None) -> None:
        self.agent_config = agent_config

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

    async def run(self, input_text: str) -> str:
        """Agentic event loop: reason → tool_call → execute → observe → repeat."""
        llm = await self._get_llm()
        system_prompt = await self._build_system_prompt()
        tools_schema = await self._build_tools_schema()

        max_iterations = getattr(self.agent_config, "max_iterations", 5) if self.agent_config else 5
        ctx = AgentRunContext()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ]

        last_content: str = ""
        consecutive_failures: dict[str, int] = {}

        while ctx.iteration_count < max_iterations:
            ctx.iteration_count += 1

            response = await llm.chat(messages, tools=tools_schema)

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
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": tool_calls_payload,
            })

            if response.content:
                last_content = response.content

            # Dispatch each tool call
            from app.core.tools.registry import dispatch_tool
            should_terminate = False

            for tc in response.tool_calls:
                ctx.tools_used.add(tc.name)
                result = await dispatch_tool(tc.name, tc.arguments)

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
    else:
        return BaseAgent(agent_config=agent_config)
