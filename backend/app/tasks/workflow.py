"""Celery task for the multi-agent writing workflow."""
import asyncio
import json
import uuid
from datetime import datetime, timezone


async def _writing_workflow_async(workflow_run_id: str) -> None:
    """Execute the Writer→Editor→Reviewer pipeline.

    Publishes SSE events to Redis channel workflow:{run_id} at each step.
    Sets WorkflowRun.status to 'waiting_human' after Reviewer completes.
    Idempotent: skips runs not in 'pending' status.
    """
    from app.models import AgentConfig, ArticleAnalysis, WorkflowRun
    from app.models.workflow import AgentStep

    run = await WorkflowRun.find_one(WorkflowRun.id == uuid.UUID(workflow_run_id))
    if not run:
        return

    # Idempotency guard
    if run.status not in ("pending",):
        return

    # Mark running and record Celery task ID
    import celery
    current_task = celery.current_task
    run.status = "running"
    if current_task:
        run.celery_task_id = current_task.request.id
    await run.save()

    from app.core.redis_client import sync_redis

    def publish(event_type: str, data: dict) -> None:
        payload = json.dumps({"type": event_type, **data})
        sync_redis.publish(f"workflow:{workflow_run_id}", payload)

    try:
        # Load active agents in workflow order
        agents_configs = await AgentConfig.find(
            AgentConfig.is_active == True  # noqa: E712
        ).sort("+workflow_order").to_list()

        if not agents_configs:
            raise ValueError("No active agent configs found")

        # Build reference context from article analyses
        analyses_context = ""
        if run.input.article_ids:
            analyses = []
            for art_id in run.input.article_ids:
                analysis = await ArticleAnalysis.find_one(
                    ArticleAnalysis.article_id == art_id
                )
                if analysis:
                    analyses.append(analysis)
            if analyses:
                ctx_parts = []
                for a in analyses:
                    ctx_parts.append(
                        f"--- 参考文章分析 ---\n"
                        f"Hook类型: {a.hook_type}\n"
                        f"写作框架: {a.framework}\n"
                        f"情绪触发: {', '.join(a.emotional_triggers)}\n"
                        f"金句: {'; '.join(a.key_phrases[:3])}\n"
                        f"目标受众: {a.target_audience}\n"
                        f"风格: 语气={a.style.tone}, 正式度={a.style.formality}\n"
                    )
                analyses_context = "\n".join(ctx_parts)

        # Include user_feedback from parent run if this is a revision
        feedback_context = ""
        if run.user_feedback:
            feedback_context = f"\n\n用户修改意见：{run.user_feedback}"

        current_content = ""

        for agent_config in agents_configs:
            step = AgentStep(
                agent_id=agent_config.id,
                agent_name=agent_config.name,
                role=agent_config.role,
                status="running",
                started_at=datetime.now(timezone.utc),
            )

            publish("agent_start", {
                "agent": agent_config.name,
                "role": agent_config.role,
                "message": f"{agent_config.name} 开始处理...",
            })

            try:
                from app.core.agents.base import create_agent_for_config

                agent = create_agent_for_config(agent_config)

                if agent_config.role == "writer":
                    step.input = analyses_context + feedback_context
                    result = await agent.run(step.input)
                    current_content = result
                    step.output = result
                elif agent_config.role == "editor":
                    step.input = current_content
                    result = await agent.run(current_content)
                    # Editor returns structured JSON with content + title_candidates
                    try:
                        parsed = json.loads(result)
                        current_content = parsed.get("content", result)
                        step.output = current_content
                        step.title_candidates = parsed.get("title_candidates", [])
                    except json.JSONDecodeError:
                        current_content = result
                        step.output = result
                else:  # reviewer and custom
                    step.input = current_content
                    result = await agent.run(current_content)
                    step.output = result

                step.status = "done"
                step.ended_at = datetime.now(timezone.utc)

                publish("agent_output", {
                    "agent": agent_config.name,
                    "role": agent_config.role,
                    "content": step.output[:500],  # preview only
                    "title_candidates": step.title_candidates,
                })

            except Exception as exc:
                step.status = "failed"
                step.ended_at = datetime.now(timezone.utc)
                step.output = str(exc)
                publish("agent_error", {
                    "agent": agent_config.name,
                    "message": str(exc),
                })
                raise

            run.steps.append(step)
            await run.save()

        # All agents done — update final output and pause for human review
        run.final_output = current_content
        run.status = "waiting_human"
        await run.save()

        publish("workflow_paused", {
            "reason": "waiting_human_review",
            "run_id": workflow_run_id,
            "final_output_preview": current_content[:200],
        })

    except Exception as exc:
        run.status = "failed"
        await run.save()
        publish("workflow_failed", {"error": str(exc)})
        raise


from app.celery_app import celery_app, get_worker_loop


@celery_app.task(name="writing_workflow_task", bind=True)
def writing_workflow_task(self: object, workflow_run_id: str) -> None:  # type: ignore[misc]
    get_worker_loop().run_until_complete(_writing_workflow_async(workflow_run_id))
