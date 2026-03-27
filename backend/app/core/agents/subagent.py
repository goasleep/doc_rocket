"""Subagent isolation for spawning isolated child agents.

Implements true isolation where subagents run with fresh message contexts
and return only final summaries to the parent agent.
"""

from typing import Any

from app.core.agents.base import BaseAgent, create_agent_for_config
from app.models import AgentConfig


class SubagentRunner:
    """Runs subagents with isolated contexts.

    Each subagent gets a fresh message context and returns only
    the final result, preventing parent context bloat.
    """

    # Agent type configurations
    AGENT_TYPES = {
        "Explore": {
            "description": "Read-only agent for exploration tasks",
            "allowed_tools": ["web_search", "fetch_url", "query_articles"],
        },
        "general-purpose": {
            "description": "Full-featured agent with all tools",
            "allowed_tools": None,  # All tools allowed
        },
    }

    async def run(
        self,
        agent_role: str,
        prompt: str,
        max_iterations: int = 5,
        agent_type: str = "general-purpose",
        model_config_name: str | None = None,
    ) -> str:
        """Run a subagent with isolated context.

        Args:
            agent_role: The role of the agent to spawn (writer, editor, reviewer, etc.)
            prompt: The task prompt for the subagent
            max_iterations: Maximum iterations for the subagent loop
            agent_type: Type of subagent ("Explore" or "general-purpose")
            model_config_name: Optional specific model config to use

        Returns:
            Final output from the subagent (summary only, not full trace)
        """
        # Get or create agent config
        agent_config = await self._get_agent_config(agent_role, model_config_name)

        # Filter tools based on agent type
        if agent_type == "Explore":
            agent_config = self._filter_tools_for_explore(agent_config)

        # Create agent instance
        agent = create_agent_for_config(agent_config)

        # Run the agent with isolated context
        # The agent's run() method creates its own fresh messages list
        try:
            result = await agent.run(prompt)
            return result
        except Exception as e:
            return f"[Subagent error: {e}]"

    async def _get_agent_config(
        self,
        agent_role: str,
        model_config_name: str | None = None,
    ) -> AgentConfig:
        """Get or create agent configuration for the subagent."""
        # Try to find existing config for this role
        config = await AgentConfig.find_one(AgentConfig.role == agent_role)

        if config:
            # Override model config if specified
            if model_config_name:
                config.model_config_name = model_config_name
            return config

        # Create a default config for this role
        return AgentConfig(
            name=f"subagent-{agent_role}",
            role=agent_role,
            model_config_name=model_config_name or "",
            system_prompt=self._get_default_system_prompt(agent_role),
            max_iterations=5,
            tools=[],
            skills=[],
        )

    def _filter_tools_for_explore(self, agent_config: AgentConfig) -> AgentConfig:
        """Filter agent config to only allow read-only tools for Explore type."""
        explore_tools = self.AGENT_TYPES["Explore"]["allowed_tools"] or []

        # Create a copy with filtered tools
        filtered_config = AgentConfig(
            name=agent_config.name,
            role=agent_config.role,
            model_config_name=agent_config.model_config_name,
            system_prompt=agent_config.system_prompt,
            max_iterations=agent_config.max_iterations,
            tools=[t for t in (agent_config.tools or []) if t in explore_tools],
            skills=agent_config.skills or [],
        )
        return filtered_config

    def _get_default_system_prompt(self, agent_role: str) -> str:
        """Get default system prompt for a role."""
        prompts = {
            "writer": "You are a skilled content writer. Create high-quality content based on the given task.",
            "editor": "You are a meticulous editor. Review and improve content according to the given task.",
            "reviewer": "You are a critical reviewer. Evaluate content quality and provide constructive feedback.",
            "analyzer": "You are a data analyzer. Analyze information and provide insights.",
            "orchestrator": "You are a workflow orchestrator. Coordinate tasks and delegate appropriately.",
        }
        return prompts.get(agent_role, f"You are a {agent_role} agent. Complete the given task professionally.")


async def spawn_subagent(
    task: str,
    agent_role: str = "general-purpose",
    agent_type: str = "general-purpose",
    max_iterations: int = 5,
    model_config_name: str | None = None,
) -> str:
    """Tool: Spawn an isolated subagent to complete a task.

    This tool creates a fresh agent context that runs independently
    and returns only the final result.

    Args:
        task: The task description for the subagent
        agent_role: The role of agent to spawn (writer, editor, reviewer, analyzer, etc.)
        agent_type: Type of subagent - "Explore" (read-only) or "general-purpose" (full tools)
        max_iterations: Maximum iterations for the subagent (default: 5)
        model_config_name: Optional specific LLM model config to use

    Returns:
        Final output from the subagent

    Example:
        spawn_subagent(
            task="Research the latest AI trends and summarize key findings",
            agent_role="analyzer",
            agent_type="Explore"
        )
    """
    runner = SubagentRunner()

    # Build the prompt with context about isolation
    full_prompt = f"""You are an isolated subagent. Complete the following task and provide your final answer.

Task: {task}

Important: You are running in an isolated context. Your final response will be returned directly to the parent agent.
Be thorough but concise in your response.
"""

    result = await runner.run(
        agent_role=agent_role,
        prompt=full_prompt,
        max_iterations=max_iterations,
        agent_type=agent_type,
        model_config_name=model_config_name,
    )

    return f"[Subagent ({agent_role}/{agent_type}) result]:\n{result}"
