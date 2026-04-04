## 1. Backend Core - Image Generation Interface

- [ ] 1.1 Create `backend/app/core/image_generation/base.py` with `ImageGenerator` abstract interface
- [ ] 1.2 Create `backend/app/core/image_generation/__init__.py` with exports
- [ ] 1.3 Create `backend/app/core/image_generation/placeholder.py` with placeholder implementation

## 2. Backend Core - ImageAgent Implementation

- [ ] 2.1 Create `backend/app/core/agents/image.py` with `ImageAgent` class
- [ ] 2.2 Implement `ImageAgent._get_image_generator()` method
- [ ] 2.3 Implement `ImageAgent.run()` method with prompt optimization
- [ ] 2.4 Add `ImageAgent` to `backend/app/core/agents/__init__.py` exports

## 3. Backend Models - Image Storage

- [ ] 3.1 Create `GeneratedImage` model in `backend/app/models/workflow.py`
- [ ] 3.2 Add `generated_images` field to `WorkflowRun` document
- [ ] 3.3 Update `WorkflowRunPublic` schema to include `generated_images`

## 4. Backend Tools - Image Generation Tool

- [ ] 4.1 Add `generate_image` function to `backend/app/core/tools/builtin.py`
- [ ] 4.2 Register `generate_image` tool in `backend/app/core/tools/registry.py`
- [ ] 4.3 Add tool schema for `generate_image` (prompt, size, style parameters)

## 5. Backend Integration - Workflow Support

- [ ] 5.1 Update `backend/app/tasks/workflow.py` to support ImageAgent in task graph
- [ ] 5.2 Add ImageAgent step handling in `_writing_workflow_task_graph()`
- [ ] 5.3 Test workflow execution with ImageAgent enabled

## 6. Frontend - API Types

- [ ] 6.1 Regenerate frontend client with `pnpm run generate-client`
- [ ] 6.2 Verify `GeneratedImage` type is included in types

## 7. Frontend - Workflow Detail Page

- [ ] 7.1 Add `GeneratedImagesPanel` component in `frontend/src/routes/_layout/workflow.tsx`
- [ ] 7.2 Display images in grid layout with click-to-expand
- [ ] 7.3 Show image metadata (prompt) in modal when clicked

## 8. Frontend - Workflow List

- [ ] 8.1 Add image count indicator in workflow list items
- [ ] 8.2 Show image icon when workflow has generated images

## 9. Testing & Verification

- [ ] 9.1 Build backend Docker image: `docker compose build backend`
- [ ] 9.2 Build frontend: `cd frontend && pnpm run build`
- [ ] 9.3 Test full workflow: `docker compose up -d`
- [ ] 9.4 Verify health checks pass
- [ ] 9.5 Create test ImageAgent config and run workflow

## 10. Documentation

- [ ] 10.1 Add ImageAgent configuration example to CLAUDE.md
- [ ] 10.2 Document image generation provider interface for future integration
