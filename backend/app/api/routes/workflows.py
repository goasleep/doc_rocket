"""Writing workflow routes — trigger, monitor (SSE), approve, reject, abort."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser
from app.core.redis_client import workflow_event_stream
from app.tasks.workflow import writing_workflow_task
from app.models import (
    Draft,
    WorkflowApprove,
    WorkflowReject,
    WorkflowRun,
    WorkflowRunCreate,
    WorkflowRunPublic,
    WorkflowRunsPublic,
    Message,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/", response_model=WorkflowRunsPublic)
async def list_workflows(
    current_user: CurrentUser, skip: int = 0, limit: int = 50
) -> Any:
    import asyncio
    count, runs = await asyncio.gather(
        WorkflowRun.count(),
        WorkflowRun.find_all().sort("-created_at").skip(skip).limit(limit).to_list(),
    )
    return WorkflowRunsPublic(data=runs, count=count)


@router.post("/", response_model=WorkflowRunPublic, status_code=202)
async def trigger_workflow(current_user: CurrentUser, body: WorkflowRunCreate) -> Any:
    from app.models import Article, SystemConfig, TaskRun
    from app.models.workflow import WorkflowInput

    sys_config = await SystemConfig.find_one()
    use_orchestrator = sys_config.orchestrator.enabled if sys_config and sys_config.orchestrator else False

    run = WorkflowRun(
        type=body.type,
        input=WorkflowInput(article_ids=body.article_ids, topic=body.topic),
        status="pending",
        created_by=current_user.id,
        use_orchestrator=use_orchestrator,
    )
    await run.insert()

    task = writing_workflow_task.delay(str(run.id))
    run.celery_task_id = task.id
    await run.save()

    # Create TaskRun linked to this WorkflowRun
    if body.article_ids:
        first_article = await Article.find_one(Article.id == body.article_ids[0])
        task_run = TaskRun(
            task_type="workflow",
            entity_type="article",
            entity_id=body.article_ids[0],
            entity_name=first_article.title if first_article else None,
            workflow_run_id=run.id,
            status="pending",
        )
    else:
        task_run = TaskRun(
            task_type="workflow",
            entity_type=None,
            entity_id=None,
            entity_name=(body.topic or "")[:100] if body.topic else None,
            workflow_run_id=run.id,
            status="pending",
        )
    await task_run.insert()

    return run


@router.get("/{id}", response_model=WorkflowRunPublic)
async def get_workflow(current_user: CurrentUser, id: uuid.UUID) -> Any:
    run = await WorkflowRun.find_one(WorkflowRun.id == id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.get("/{id}/stream")
async def workflow_stream(id: uuid.UUID, current_user: CurrentUser) -> StreamingResponse:
    """SSE endpoint — streams workflow events from Redis pub/sub."""
    run = await WorkflowRun.find_one(WorkflowRun.id == id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    return StreamingResponse(
        workflow_event_stream(str(id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{id}/approve", response_model=WorkflowRunPublic)
async def approve_workflow(
    current_user: CurrentUser, id: uuid.UUID, body: WorkflowApprove
) -> Any:
    run = await WorkflowRun.find_one(WorkflowRun.id == id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    if run.status != "waiting_human":
        raise HTTPException(status_code=400, detail="Workflow is not awaiting human review")

    # Extract title_candidates from Editor step
    title_candidates: list[str] = []
    for step in run.steps:
        if step.role == "editor" and step.title_candidates:
            title_candidates = step.title_candidates
            break

    # Create Draft
    draft = Draft(
        source_article_ids=list(run.input.article_ids),
        workflow_run_id=run.id,
        title=body.selected_title,
        title_candidates=title_candidates,
        content=run.final_output or "",
        status="draft",
    )
    await draft.insert()

    run.status = "done"
    await run.save()

    return run


@router.post("/{id}/reject", response_model=WorkflowRunPublic)
async def reject_workflow(
    current_user: CurrentUser, id: uuid.UUID, body: WorkflowReject
) -> Any:
    run = await WorkflowRun.find_one(WorkflowRun.id == id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    if run.status != "waiting_human":
        raise HTTPException(status_code=400, detail="Workflow is not awaiting human review")

    run.status = "failed"
    await run.save()

    # Create child WorkflowRun for revision
    child = WorkflowRun(
        type=run.type,
        input=run.input,
        status="pending",
        parent_run_id=run.id,
        user_feedback=body.feedback,
        created_by=current_user.id,
    )
    await child.insert()

    task = writing_workflow_task.delay(str(child.id))
    child.celery_task_id = task.id
    await child.save()

    return child


@router.post("/{id}/abort", response_model=Message)
async def abort_workflow(current_user: CurrentUser, id: uuid.UUID) -> Any:
    run = await WorkflowRun.find_one(WorkflowRun.id == id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    if run.celery_task_id:
        from app.celery_app import celery_app
        celery_app.control.revoke(run.celery_task_id, terminate=True)

    run.status = "failed"
    await run.save()

    return Message(message="Workflow aborted")
