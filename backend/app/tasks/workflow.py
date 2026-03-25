"""Celery task for the multi-agent writing workflow."""
import asyncio
import json
import uuid
from datetime import datetime, timezone


async def _build_analyses_context(run: object) -> str:  # type: ignore[return]
    from app.models import ArticleAnalysis, WorkflowRun
    run = run  # type: WorkflowRun
    if not run.input.article_ids:  # type: ignore[union-attr]
        return ""
    analyses = []
    for art_id in run.input.article_ids:  # type: ignore[union-attr]
        analysis = await ArticleAnalysis.find_one(ArticleAnalysis.article_id == art_id)
        if analysis:
            analyses.append(analysis)
    if not analyses:
        return ""
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
    return "\n".join(ctx_parts)


async def _writing_workflow_linear(run: object, workflow_run_id: str, publish: object) -> None:  # type: ignore[return]
    """Original linear Writer→Editor→Reviewer pipeline."""
    from app.models import AgentConfig, WorkflowRun
    from app.models.workflow import AgentStep
    run = run  # type: WorkflowRun

    agents_configs = await AgentConfig.find(
        AgentConfig.is_active == True  # noqa: E712
    ).sort("+workflow_order").to_list()

    if not agents_configs:
        raise ValueError("No active agent configs found")

    analyses_context = await _build_analyses_context(run)
    feedback_context = ""
    if run.user_feedback:  # type: ignore[union-attr]
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

        publish("agent_start", {  # type: ignore[call-arg,operator]
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

            publish("agent_output", {  # type: ignore[call-arg,operator]
                "agent": agent_config.name,
                "role": agent_config.role,
                "content": step.output[:500],
                "title_candidates": step.title_candidates,
            })

        except Exception as exc:
            step.status = "failed"
            step.ended_at = datetime.now(timezone.utc)
            step.output = str(exc)
            publish("agent_error", {  # type: ignore[call-arg,operator]
                "agent": agent_config.name,
                "message": str(exc),
            })
            raise

        run.steps.append(step)  # type: ignore[union-attr]
        await run.save()  # type: ignore[union-attr]

    # Humanizer step: 去AI味 — use BaseAgent to avoid EditorAgent's JSON output format
    from app.core.agents.base import BaseAgent

    humanizer_config = await AgentConfig.find_one(
        AgentConfig.role == "editor",
        AgentConfig.is_active == True,  # noqa: E712
    )
    humanizer_step = AgentStep(
        agent_name="去AI味处理",
        role="humanizer",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    publish("agent_start", {  # type: ignore[call-arg,operator]
        "agent": "去AI味处理",
        "role": "humanizer",
        "message": "正在进行去AI味处理...",
    })
    try:
        humanizer = BaseAgent(agent_config=humanizer_config)
        humanize_prompt = (
            f"请对以下文章进行去AI味处理，使其更自然、更有人情味，"
            f"避免AI腔调，保持原意但改变表达方式，让读者感觉是人写的。\n\n"
            f"文章内容：\n{current_content}\n\n"
            f"只返回处理后的文章，不要解释。"
        )
        current_content = await humanizer.run(humanize_prompt)
        humanizer_step.output = current_content
        humanizer_step.status = "done"
        humanizer_step.ended_at = datetime.now(timezone.utc)
        publish("agent_output", {  # type: ignore[call-arg,operator]
            "agent": "去AI味处理",
            "role": "humanizer",
            "content": current_content[:500],
            "title_candidates": [],
        })
    except Exception as exc:
        humanizer_step.status = "failed"
        humanizer_step.ended_at = datetime.now(timezone.utc)
        humanizer_step.output = str(exc)
        publish("agent_error", {  # type: ignore[call-arg,operator]
            "agent": "去AI味处理",
            "message": str(exc),
        })
        # Non-fatal: keep current_content unchanged if humanizer fails
    run.steps.append(humanizer_step)  # type: ignore[union-attr]
    await run.save()  # type: ignore[union-attr]

    run.final_output = current_content  # type: ignore[union-attr]
    run.status = "waiting_human"  # type: ignore[union-attr]
    await run.save()  # type: ignore[union-attr]

    publish("workflow_paused", {  # type: ignore[call-arg,operator]
        "reason": "waiting_human_review",
        "run_id": workflow_run_id,
        "final_output_preview": current_content[:200],
    })


async def _writing_workflow_orchestrator(run: object, workflow_run_id: str, publish: object) -> None:  # type: ignore[return]
    """OrchestratorAgent-driven workflow."""
    from app.models import AgentConfig, WorkflowRun
    from app.models.workflow import AgentStep, RoutingEvent
    from app.core.agents.orchestrator import OrchestratorAgent
    run = run  # type: WorkflowRun

    analyses_context = await _build_analyses_context(run)
    feedback_context = ""
    if run.user_feedback:  # type: ignore[union-attr]
        feedback_context = f"\n\n用户修改意见：{run.user_feedback}"

    # Build orchestrator input
    topic = run.input.topic or "请根据参考素材创作一篇高质量文章"  # type: ignore[union-attr]
    orchestrator_input = f"任务：{topic}\n\n{analyses_context}{feedback_context}"

    # Load orchestrator agent config if exists
    orch_cfg = await AgentConfig.find_one(
        AgentConfig.role == "orchestrator",
        AgentConfig.is_active == True,  # noqa: E712
    )
    orch_agent = OrchestratorAgent(agent_config=orch_cfg)

    publish("agent_start", {  # type: ignore[call-arg,operator]
        "agent": "Orchestrator",
        "role": "orchestrator",
        "message": "Orchestrator 开始协调写作团队...",
    })

    try:
        result = await orch_agent.run(orchestrator_input)

        # Record routing log
        for entry in orch_agent._routing_log:
            run.routing_log.append(RoutingEvent(  # type: ignore[union-attr]
                timestamp=datetime.fromisoformat(entry["timestamp"]),
                from_agent=entry["from_agent"],
                to_agent=entry["to_agent"],
                reason=entry["reason"],
            ))
            publish("routing_decision", {  # type: ignore[call-arg,operator]
                "from_agent": entry["from_agent"],
                "to_agent": entry["to_agent"],
                "reason": entry["reason"],
            })

        # Record orchestrator messages (the loop messages)
        run.iteration_count = orch_agent._revision_count  # type: ignore[union-attr]

        # Final output
        final_content = orch_agent._final_output or result
        title_candidates = orch_agent._final_title_candidates

        # Create a summary AgentStep
        step = AgentStep(
            agent_name="Orchestrator",
            role="orchestrator",
            input=orchestrator_input[:500],
            output=final_content[:500],
            title_candidates=title_candidates,
            status="done",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            iteration_count=orch_agent._revision_count,
        )
        run.steps.append(step)  # type: ignore[union-attr]

        run.final_output = final_content  # type: ignore[union-attr]
        run.status = "waiting_human"  # type: ignore[union-attr]
        await run.save()  # type: ignore[union-attr]

        publish("agent_output", {  # type: ignore[call-arg,operator]
            "agent": "Orchestrator",
            "role": "orchestrator",
            "content": final_content[:500],
            "title_candidates": title_candidates,
        })

        publish("workflow_paused", {  # type: ignore[call-arg,operator]
            "reason": "waiting_human_review",
            "run_id": workflow_run_id,
            "final_output_preview": final_content[:200],
        })

    except Exception as exc:
        error_msg = str(exc)
        publish("agent_error", {  # type: ignore[call-arg,operator]
            "agent": "Orchestrator",
            "message": error_msg,
        })
        # Save error to WorkflowRun before re-raising
        run.status = "failed"  # type: ignore[union-attr]
        run.error_message = error_msg[:500]  # type: ignore[union-attr]
        await run.save()  # type: ignore[union-attr]
        raise


async def _writing_workflow_async(workflow_run_id: str) -> None:
    """Execute the writing workflow (linear or orchestrator-driven).

    Publishes SSE events to Redis channel workflow:{run_id} at each step.
    Sets WorkflowRun.status to 'waiting_human' after completion.
    Idempotent: skips runs not in 'pending' status.
    """
    from app.models import TaskRun, WorkflowRun

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

    # Update TaskRun to running
    task_run = await TaskRun.find_one(TaskRun.workflow_run_id == uuid.UUID(workflow_run_id))
    if task_run:
        task_run.status = "running"
        task_run.started_at = datetime.now(timezone.utc)
        task_run.celery_task_id = run.celery_task_id
        await task_run.save()

    from app.core.redis_client import sync_redis

    def publish(event_type: str, data: dict) -> None:  # type: ignore[type-arg]
        payload = json.dumps({"type": event_type, **data})
        sync_redis.publish(f"workflow:{workflow_run_id}", payload)

    try:
        if run.use_orchestrator:
            await _writing_workflow_orchestrator(run, workflow_run_id, publish)
        else:
            await _writing_workflow_linear(run, workflow_run_id, publish)

        # Mark TaskRun as done
        if task_run:
            task_run.status = "done"
            task_run.ended_at = datetime.now(timezone.utc)
            await task_run.save()

    except Exception as exc:
        run.status = "failed"
        await run.save()
        publish("workflow_failed", {"error": str(exc)})

        # Mark TaskRun as failed
        if task_run:
            task_run.status = "failed"
            task_run.error_message = str(exc)[:500]
            await task_run.save()

        raise


from app.celery_app import celery_app, get_worker_loop


@celery_app.task(
    name="writing_workflow_task",
    bind=True,
    soft_time_limit=600,
    time_limit=660,
)
def writing_workflow_task(self: object, workflow_run_id: str) -> None:  # type: ignore[misc]
    get_worker_loop().run_until_complete(_writing_workflow_async(workflow_run_id))
