"""Async rewrite logic for paragraph-level 去AI味 rewrites.

Note: This is NOT a Celery task. The rewrite-section endpoint calls
_rewrite_section_async() directly (await) because users wait for the
result synchronously before deciding to accept or discard.
"""
import json
import uuid

from app.core.agents.base import create_agent_for_config


async def _rewrite_section_async(
    draft_id: str,
    selected_text: str,
    context: str = "",
) -> str:
    """Rewrite a selected text section using the EditorAgent.

    Returns the rewritten text.
    """
    from app.models import AgentConfig, Draft

    draft = await Draft.find_one(Draft.id == uuid.UUID(draft_id))
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    editor_config = await AgentConfig.find_one(
        AgentConfig.role == "editor",
        AgentConfig.is_active == True,  # noqa: E712
    )

    agent = create_agent_for_config(editor_config)

    prompt = (
        f"请对以下选中的文字进行去AI味处理，使其更自然、口语化，"
        f"保持原意但改变表达方式。\n\n"
        f"上下文：\n{context}\n\n"
        f"需要重写的文字：\n{selected_text}\n\n"
        f"只返回重写后的文字，不要解释。"
    )

    rewritten = await agent.run(prompt)
    # EditorAgent returns JSON; extract just the content field for rewrite
    try:
        data = json.loads(rewritten)
        if isinstance(data, dict) and "content" in data:
            return data["content"].strip()
    except (json.JSONDecodeError, AttributeError):
        pass
    return rewritten.strip()
