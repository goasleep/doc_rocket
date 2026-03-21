"""Base agent class and factory function."""
from typing import Any


class BaseAgent:
    """Base class for all content intelligence agents.

    Holds the agent configuration and LLM client.
    Subclasses implement run() with role-specific logic.
    """

    def __init__(self, agent_config: Any | None = None) -> None:
        self.agent_config = agent_config

    async def _get_llm(self) -> Any:
        from app.core.llm.factory import get_llm_client

        if self.agent_config:
            return await get_llm_client(
                provider=self.agent_config.model_provider,
                model_id=self.agent_config.model_id,
            )
        # Fallback: use system default
        from app.models import SystemConfig
        config = await SystemConfig.find_one()
        provider = "kimi"
        model = "moonshot-v1-32k"
        if config:
            provider = config.writing.default_model_provider
            model = config.writing.default_model_id
        return await get_llm_client(provider=provider, model_id=model)

    def _system_prompt(self) -> str:
        if self.agent_config and self.agent_config.system_prompt:
            return self.agent_config.system_prompt
        return "你是一位专业的内容创作助手。"

    async def run(self, input_text: str) -> str:
        """Execute agent logic. Override in subclasses."""
        llm = await self._get_llm()
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": input_text},
        ]
        return await llm.chat(messages)


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
    else:
        return BaseAgent(agent_config=agent_config)
