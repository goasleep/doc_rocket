"""Tests for subagent isolation functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agents.subagent import SubagentRunner, spawn_subagent
from app.models import AgentConfig


class TestSubagentRunner:
    """Test cases for SubagentRunner class."""

    @pytest.mark.anyio
    async def test_run_creates_agent_and_executes(self, db: None):
        """Test that run creates an agent and executes the task."""
        runner = SubagentRunner()

        # Mock agent config
        mock_config = MagicMock()
        mock_config.role = "writer"
        mock_config.model_config_name = "test-model"
        mock_config.tools = []
        mock_config.skills = []

        # Mock the created agent
        mock_agent = AsyncMock()
        mock_agent.run.return_value = "Final result from subagent"

        with patch("app.core.agents.subagent.AgentConfig.find_one", new_callable=AsyncMock, return_value=mock_config):
            with patch("app.core.agents.subagent.create_agent_for_config", return_value=mock_agent):
                result = await runner.run(
                    agent_role="writer",
                    prompt="Write a story",
                    max_iterations=3,
                )

        assert result == "Final result from subagent"
        mock_agent.run.assert_called_once()

    @pytest.mark.anyio
    async def test_run_handles_errors(self, db: None):
        """Test that run handles agent errors gracefully."""
        runner = SubagentRunner()

        mock_config = MagicMock()
        mock_config.role = "writer"
        mock_config.model_config_name = "test-model"
        mock_config.tools = []
        mock_config.skills = []

        mock_agent = AsyncMock()
        mock_agent.run.side_effect = Exception("Agent failed")

        with patch("app.core.agents.subagent.AgentConfig.find_one", new_callable=AsyncMock, return_value=mock_config):
            with patch("app.core.agents.subagent.create_agent_for_config", return_value=mock_agent):
                result = await runner.run(
                    agent_role="writer",
                    prompt="Write a story",
                )

        assert "[Subagent error:" in result
        assert "Agent failed" in result

    @pytest.mark.anyio
    async def test_get_agent_config_existing(self, db: None):
        """Test getting existing agent config."""
        runner = SubagentRunner()

        mock_config = MagicMock()
        mock_config.role = "editor"
        mock_config.model_config_name = "original-model"

        with patch("app.core.agents.subagent.AgentConfig.find_one", new_callable=AsyncMock, return_value=mock_config):
            result = await runner._get_agent_config("editor", "new-model")

        assert result == mock_config
        assert result.model_config_name == "new-model"  # Should be overridden

    @pytest.mark.anyio
    async def test_get_agent_config_creates_default(self, db: None):
        """Test creating default config when none exists."""
        runner = SubagentRunner()

        with patch("app.core.agents.subagent.AgentConfig.find_one", new_callable=AsyncMock, return_value=None):
            result = await runner._get_agent_config("analyzer", "test-model")

        assert result.name == "subagent-analyzer"
        assert result.role == "analyzer"
        assert result.model_config_name == "test-model"

    @pytest.mark.anyio
    async def test_filter_tools_for_explore(self, db: None):
        """Test that Explore type filters to read-only tools."""
        runner = SubagentRunner()

        mock_config = MagicMock()
        mock_config.name = "test-agent"
        mock_config.role = "analyzer"
        mock_config.model_config_name = "model"
        mock_config.system_prompt = "System prompt"
        mock_config.max_iterations = 5
        mock_config.tools = ["web_search", "fetch_url", "save_draft", "query_articles"]
        mock_config.skills = []

        filtered = runner._filter_tools_for_explore(mock_config)

        # Should only have read-only tools
        assert "save_draft" not in filtered.tools
        assert "web_search" in filtered.tools
        assert "fetch_url" in filtered.tools
        assert "query_articles" in filtered.tools

    def test_get_default_system_prompt(self):
        """Test getting default system prompts for roles."""
        runner = SubagentRunner()

        writer_prompt = runner._get_default_system_prompt("writer")
        assert "content writer" in writer_prompt.lower()

        editor_prompt = runner._get_default_system_prompt("editor")
        assert "editor" in editor_prompt.lower()

        reviewer_prompt = runner._get_default_system_prompt("reviewer")
        assert "reviewer" in reviewer_prompt.lower()

        unknown_prompt = runner._get_default_system_prompt("unknown")
        assert "unknown" in unknown_prompt.lower()


class TestSpawnSubagentTool:
    """Test cases for spawn_subagent tool function."""

    @pytest.mark.anyio
    async def test_spawn_subagent_executes_task(self):
        """Test that spawn_subagent tool executes and formats result."""

        mock_runner = AsyncMock()
        mock_runner.run.return_value = "Research complete: AI trends are..."

        with patch("app.core.agents.subagent.SubagentRunner", return_value=mock_runner):
            result = await spawn_subagent(
                task="Research AI trends",
                agent_role="analyzer",
                agent_type="Explore",
            )

        assert "[Subagent (analyzer/Explore) result]:" in result
        assert "Research complete" in result
        mock_runner.run.assert_called_once()

    @pytest.mark.anyio
    async def test_spawn_subagent_includes_task_in_prompt(self):
        """Test that task is included in the subagent prompt."""

        mock_runner = AsyncMock()
        mock_runner.run.return_value = "Done"

        with patch("app.core.agents.subagent.SubagentRunner", return_value=mock_runner):
            await spawn_subagent(
                task="Specific research task",
                agent_role="analyzer",
            )

        # Check that the prompt includes the task
        call_args = mock_runner.run.call_args
        prompt = call_args.kwargs.get("prompt", "")
        assert "Specific research task" in prompt
        assert "isolated subagent" in prompt.lower()


class TestSubagentIsolation:
    """Tests verifying isolation properties."""

    @pytest.mark.anyio
    async def test_subagent_fresh_context(self, db: None):
        """Test that subagent runs with fresh context."""
        runner = SubagentRunner()

        mock_config = MagicMock()
        mock_config.role = "writer"
        mock_config.model_config_name = ""
        mock_config.tools = []
        mock_config.skills = []

        # Track what prompt the agent receives
        received_prompts = []

        async def capture_run(prompt):
            received_prompts.append(prompt)
            return "Result"

        mock_agent = MagicMock()
        mock_agent.run = capture_run

        with patch("app.core.agents.subagent.AgentConfig.find_one", new_callable=AsyncMock, return_value=mock_config):
            with patch("app.core.agents.subagent.create_agent_for_config", return_value=mock_agent):
                await runner.run(
                    agent_role="writer",
                    prompt="Task for subagent",
                )

        # The subagent should receive the task in its prompt
        assert len(received_prompts) == 1
        assert "Task for subagent" in received_prompts[0]

    def test_agent_type_definitions(self):
        """Test that agent types are properly defined."""
        runner = SubagentRunner()

        assert "Explore" in runner.AGENT_TYPES
        assert "general-purpose" in runner.AGENT_TYPES

        explore_config = runner.AGENT_TYPES["Explore"]
        assert "allowed_tools" in explore_config
        assert "web_search" in explore_config["allowed_tools"]

        general_config = runner.AGENT_TYPES["general-purpose"]
        assert general_config["allowed_tools"] is None  # All tools allowed