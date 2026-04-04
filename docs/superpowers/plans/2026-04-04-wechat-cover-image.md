# 微信公众号封面图片上传功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为公众号发布功能添加封面图片上传功能，支持双存储（七牛云永久URL + 微信临时media_id），强制上传封面，后端智能裁剪适配。

**Architecture:** 在 Draft 模型新增封面字段，新增上传端点处理图片压缩/裁剪/双上传，修改发布流程检查封面必填，前端在发布对话框添加封面上传UI。

**Tech Stack:** FastAPI + Beanie ODM, Pillow (图片处理), 七牛云 SDK, 微信 MP API, React + TanStack Query

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/draft.py` | 修改 | Draft模型添加封面字段 |
| `backend/app/api/routes/drafts.py` | 修改 | 新增upload-cover端点，修改publish检查封面 |
| `backend/app/core/image.py` | 创建 | 图片处理工具（压缩、裁剪） |
| `backend/pyproject.toml` | 修改 | 添加 Pillow 依赖 |
| `frontend/src/routes/_layout/drafts/$id.tsx` | 修改 | 发布对话框添加封面上传UI |
| `frontend/src/components/DraftEditor/PublishConfirmDialog.tsx` | 修改 | 扩展对话框支持封面上传 |
| `frontend/src/client/services.gen.ts` | 修改 | 添加 uploadCover API 调用 |

---

## Task 1: 添加 Pillow 依赖

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 添加 Pillow 依赖**

在 `[project]` 部分的 `dependencies` 中添加：

```toml
dependencies = [
    # ... existing deps ...
    "pillow>=10.0.0",
]
```

- [ ] **Step 2: 提交**

```bash
git add backend/pyproject.toml
git commit -m "chore: add Pillow dependency for image processing"
```

---

## Task 2: 创建图片处理工具模块

**Files:**
- Create: `backend/app/core/image.py`

- [ ] **Step 1: 创建图片处理模块**

```python
"""Image processing utilities for cover images."""
import io
from typing import BinaryIO

from PIL import Image

# WeChat recommended cover image size
TARGET_WIDTH = 900
TARGET_HEIGHT = 500
TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT  # 1.8 (2.35:1 approx)
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}
OUTPUT_FORMAT = "JPEG"
OUTPUT_QUALITY = 85


class ImageProcessError(Exception):
    """Exception raised for image processing errors."""


def process_cover_image(image_data: bytes) -> bytes:
    """Process uploaded image for WeChat cover.

    Steps:
    1. Validate image format
    2. Resize maintaining aspect ratio (fit within 900x500, then crop center)
    3. Compress to max 2MB
    4. Return processed image bytes

    Args:
        image_data: Raw image bytes

    Returns:
        Processed image bytes in JPEG format

    Raises:
        ImageProcessError: If image format invalid or processing fails
    """
    try:
        img = Image.open(io.BytesIO(image_data))
    except Exception as exc:
        raise ImageProcessError(f"Invalid image file: {exc}") from exc

    # Validate format
    if img.format not in ALLOWED_FORMATS:
        raise ImageProcessError(
            f"Unsupported image format: {img.format}. "
            f"Allowed: {', '.join(ALLOWED_FORMATS)}"
        )

    # Convert to RGB if necessary (for PNG with transparency)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Calculate crop dimensions to match target ratio
    orig_width, orig_height = img.size
    orig_ratio = orig_width / orig_height

    if orig_ratio > TARGET_RATIO:
        # Image is wider than target, crop width
        new_width = int(orig_height * TARGET_RATIO)
        left = (orig_width - new_width) // 2
        img = img.crop((left, 0, left + new_width, orig_height))
    elif orig_ratio < TARGET_RATIO:
        # Image is taller than target, crop height
        new_height = int(orig_width / TARGET_RATIO)
        top = (orig_height - new_height) // 2
        img = img.crop((0, top, orig_width, top + new_height))

    # Resize to target dimensions
    img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)

    # Save with compression
    output = io.BytesIO()
    img.save(output, format=OUTPUT_FORMAT, quality=OUTPUT_QUALITY, optimize=True)
    processed_data = output.getvalue()

    # Check file size
    if len(processed_data) > MAX_FILE_SIZE:
        # Try with lower quality
        output = io.BytesIO()
        img.save(output, format=OUTPUT_FORMAT, quality=60, optimize=True)
        processed_data = output.getvalue()

        if len(processed_data) > MAX_FILE_SIZE:
            raise ImageProcessError(
                f"Image too large after compression: {len(processed_data)} bytes"
            )

    return processed_data


def get_image_info(image_data: bytes) -> dict:
    """Get image info without processing.

    Args:
        image_data: Raw image bytes

    Returns:
        Dict with width, height, format, size
    """
    img = Image.open(io.BytesIO(image_data))
    return {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "size_bytes": len(image_data),
    }
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/core/image.py
git commit -m "feat: add image processing utilities for cover images"
```

---

## Task 3: 修改 Draft 模型添加封面字段

**Files:**
- Modify: `backend/app/models/draft.py`

- [ ] **Step 1: 修改 Draft 模型**

```python
import uuid
from datetime import datetime, timezone

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class EditHistoryEntry(BaseModel):
    content: str
    edited_at: datetime = Field(default_factory=get_datetime_utc)
    note: str = ""


class Draft(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_article_ids: list[uuid.UUID] = Field(default_factory=list)
    workflow_run_id: uuid.UUID | None = None
    title: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    content: str = ""
    status: str = "draft"  # draft | editing | approved
    edit_history: list[EditHistoryEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    # Cover image fields
    cover_image_url: str | None = None      # Qiniu permanent URL
    thumb_media_id: str | None = None       # WeChat temporary media_id

    class Settings:
        name = "drafts"


class DraftPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_article_ids: list[uuid.UUID]
    workflow_run_id: uuid.UUID | None
    title: str
    title_candidates: list[str]
    content: str
    status: str
    edit_history: list[EditHistoryEntry]
    created_at: datetime
    cover_image_url: str | None = None


class DraftsPublic(BaseModel):
    data: list[DraftPublic]
    count: int


class DraftUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None


class RewriteSectionRequest(BaseModel):
    selected_text: str
    context: str = ""


class RewriteSectionResponse(BaseModel):
    rewritten_text: str
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/models/draft.py
git commit -m "feat: add cover image fields to Draft model"
```

---

## Task 4: 新增封面上传端点并修改发布端点

**Files:**
- Modify: `backend/app/api/routes/drafts.py`

- [ ] **Step 1: 导入依赖并添加响应模型**

在文件顶部添加导入：

```python
"""Draft management routes — CRUD, approve, export, rewrite-section, preview, publish."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.image import ImageProcessError, process_cover_image
from app.core.markdown import extract_images_from_markdown, markdown_to_wechat_html
from app.core.qiniu_oss import QiniuOSSClient
from app.core.wechat_mp import WeChatMPClient, WeChatMPError
from app.models import (
    Draft,
    DraftPublic,
    DraftsPublic,
    DraftUpdate,
    EditHistoryEntry,
    PublishHistory,
    RewriteSectionRequest,
    RewriteSectionResponse,
)


class DraftPreviewResponse(BaseModel):
    """Response schema for draft preview."""
    title: str
    html_content: str


class PublishRequest(BaseModel):
    """Request schema for publishing a draft."""
    confirmed: bool = False


class PublishResponse(BaseModel):
    """Response schema for publish operation."""
    success: bool
    publish_id: str | None = None
    article_url: str | None = None
    message: str


class CoverUploadResponse(BaseModel):
    """Response schema for cover image upload."""
    cover_image_url: str
    thumb_media_id: str
```

- [ ] **Step 2: 新增封面上传端点**

在 `router = APIRouter(...)` 之后，现有端点之前添加：

```python
@router.post("/{id}/upload-cover", response_model=CoverUploadResponse)
async def upload_cover_image(
    current_user: CurrentUser,
    id: uuid.UUID,
    file: UploadFile,
) -> Any:
    """Upload cover image for draft.

    Processes the image (resize to 900x500, compress),
    uploads to Qiniu OSS for permanent storage,
    uploads to WeChat MP for thumb_media_id,
    and saves both to the draft.

    Args:
        current_user: Current authenticated user
        id: Draft ID
        file: Image file to upload

    Returns:
        CoverUploadResponse with cover_image_url and thumb_media_id

    Raises:
        HTTPException: If draft not found, image processing fails,
                      or WeChat MP upload fails
    """
    # Get draft
    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: {', '.join(allowed_types)}"
        )

    # Read file
    image_data = await file.read()
    if len(image_data) > 10 * 1024 * 1024:  # 10MB max
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10MB."
        )

    # Process image
    try:
        processed_data = process_cover_image(image_data)
    except ImageProcessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Upload to Qiniu
    try:
        qiniu_client = QiniuOSSClient.from_settings()
        ext = "jpg"  # Output is always JPEG
        key = f"covers/{uuid.uuid4().hex}.{ext}"
        cover_image_url = await qiniu_client.upload_file(processed_data, key)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to upload to Qiniu: {exc}"
        ) from exc

    # Upload to WeChat MP to get thumb_media_id
    try:
        wechat_client = await WeChatMPClient.from_config()
        thumb_media_id = await wechat_client.upload_media(processed_data, "cover.jpg")
    except WeChatMPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to upload to WeChat MP: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"WeChat MP not configured: {exc}"
        ) from exc

    # Save to draft
    draft.cover_image_url = cover_image_url
    draft.thumb_media_id = thumb_media_id
    await draft.save()

    return CoverUploadResponse(
        cover_image_url=cover_image_url,
        thumb_media_id=thumb_media_id,
    )
```

- [ ] **Step 3: 修改发布端点检查封面**

修改 `publish_draft` 函数，在检查 confirmed 之后添加封面检查：

```python
@router.post("/{id}/publish", response_model=PublishResponse)
async def publish_draft(
    current_user: CurrentUser, id: uuid.UUID, body: PublishRequest
) -> Any:
    """Publish draft to WeChat MP.

    Requires confirmed=True to proceed with publishing.
    Creates a PublishHistory record to track the publish attempt.
    """
    if not body.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Publication must be confirmed by setting confirmed=true"
        )

    draft = await Draft.find_one(Draft.id == id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Check cover image is uploaded
    if not draft.thumb_media_id:
        raise HTTPException(
            status_code=400,
            detail="Cover image is required. Please upload a cover image first."
        )

    # Create PublishHistory record with pending status
    publish_history = PublishHistory(
        draft_id=draft.id,
        title=draft.title,
        target_platform="wechat_mp",
        target_name="",  # Will be updated after getting account info
        status="pending",
    )
    await publish_history.insert()

    client: WeChatMPClient | None = None
    failed_image_urls: list[str] = []

    try:
        # Get WeChat MP client from config
        client = await WeChatMPClient.from_config()

        # Get account info for target_name
        try:
            account_info = await client.get_account_info()
            publish_history.target_name = account_info.get("nick_name", "Unknown")
        except WeChatMPError:
            publish_history.target_name = "WeChat MP"

        # Sync Qiniu images to WeChat MP before publishing
        qiniu_domain = settings.QINIU_DOMAIN.rstrip("/")
        if qiniu_domain and draft.content:
            image_urls = extract_images_from_markdown(draft.content)
            qiniu_urls = [url for url in image_urls if url.startswith(qiniu_domain)]
            if qiniu_urls:
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    for raw_url in qiniu_urls:
                        try:
                            response = await http_client.get(raw_url)
                            response.raise_for_status()
                            image_data = response.content
                            filename = (raw_url.split("/")[-1] or "image.jpg").split("?")[0]
                            mp_url = await client.upload_image(image_data, filename)
                            draft.content = draft.content.replace(raw_url, mp_url)
                        except Exception as exc:  # noqa: BLE001
                            logging.warning("Failed to sync Qiniu image %s to WeChat MP: %s", raw_url, exc)
                            failed_image_urls.append(raw_url)

                # Persist updated content with replaced image URLs
                await draft.save()

        # Convert content to HTML
        html_content = markdown_to_wechat_html(draft.content, draft.title)

        # Create draft on WeChat MP with thumb_media_id
        media_id = await client.add_draft(
            title=draft.title,
            content=html_content,
            thumb_media_id=draft.thumb_media_id,
        )

        # Submit for publishing
        publish_id = await client.submit_publish(media_id=media_id)

        # Update PublishHistory with success
        publish_history.status = "success"
        publish_history.publish_id = publish_id
        publish_history.updated_at = datetime.now(timezone.utc)
        await publish_history.save()

        message = "Draft published successfully to WeChat MP"
        if failed_image_urls:
            message += f" (failed to sync {len(failed_image_urls)} image(s))"

        return PublishResponse(
            success=True,
            publish_id=publish_id,
            message=message
        )

    except WeChatMPError as e:
        # Update PublishHistory with failure
        publish_history.status = "failed"
        publish_history.error_message = str(e)
        publish_history.updated_at = datetime.now(timezone.utc)
        await publish_history.save()

        raise HTTPException(
            status_code=502,
            detail=f"WeChat MP API error: {str(e)}"
        )
    except Exception as e:
        # Update PublishHistory with failure
        publish_history.status = "failed"
        publish_history.error_message = str(e)
        publish_history.updated_at = datetime.now(timezone.utc)
        await publish_history.save()

        raise HTTPException(
            status_code=502,
            detail=f"Failed to publish: {str(e)}"
        )
    finally:
        if client is not None:
            await client.close()
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/routes/drafts.py
git commit -m "feat: add cover image upload endpoint and require cover for publish"
```

---

## Task 5: 添加微信 upload_media 方法

**Files:**
- Modify: `backend/app/core/wechat_mp.py`

- [ ] **Step 1: 添加 upload_media 方法**

在 `upload_image` 方法之后添加：

```python
    async def upload_media(self, image_data: bytes, filename: str) -> str:
        """Upload an image as media to WeChat MP (for thumb_media_id).

        This is different from upload_image which returns a URL.
        This method uploads as "media" and returns a media_id for use
        in draft articles as thumb_media_id.

        Args:
            image_data: Raw image bytes
            filename: Name of the image file

        Returns:
            str: Media ID (thumb_media_id) for the uploaded image

        Raises:
            WeChatMPError: If the upload fails
        """
        access_token = await self.get_access_token()

        files = {"media": (filename, image_data, "image/jpeg")}
        response = await self._http_client.post(
            "/cgi-bin/media/upload",
            params={
                "access_token": access_token,
                "type": "thumb",  # thumb type for article cover images
            },
            files=files,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if "errcode" in data and data["errcode"] != 0:
            raise WeChatMPError(
                f"Failed to upload media: {data.get('errmsg', 'Unknown error')}",
                errcode=data["errcode"],
            )

        return str(data["media_id"])
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/core/wechat_mp.py
git commit -m "feat: add upload_media method to WeChatMPClient for thumb_media_id"
```

---

## Task 6: 前端 API 客户端添加 uploadCover 方法

**Files:**
- Modify: `frontend/src/client/services.gen.ts`

- [ ] **Step 1: 找到 DraftsService 并添加方法**

在 `DraftsService` 类中添加：

```typescript
    /**
     * Upload cover image for draft
     * @param data The data for the request.
     * @param data.id Draft ID
     * @param data.formData Image file to upload
     * @returns CoverUploadResponse Cover image uploaded successfully
     * @throws ApiError
     */
    public static uploadCover(data: UploadCoverData): CancelablePromise<UploadCoverResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/drafts/{id}/upload-cover',
            path: {
                id: data.id
            },
            formData: data.formData,
            mediaType: 'multipart/form-data',
        });
    }
```

- [ ] **Step 2: 添加类型定义**

在类型定义文件中添加（通常是同一文件或 nearby）：

```typescript
export type UploadCoverData = {
    id: string;
    formData: {
        file: Blob | File;
    };
};

export type UploadCoverResponse = {
    cover_image_url: string;
    thumb_media_id: string;
};
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/client/services.gen.ts
git commit -m "feat: add uploadCover API client method"
```

---

## Task 7: 修改发布确认对话框组件

**Files:**
- Modify: `frontend/src/components/DraftEditor/PublishConfirmDialog.tsx`

- [ ] **Step 1: 完整替换组件代码**

```typescript
import { useMutation } from "@tanstack/react-query";
import { ImageIcon, Upload, X } from "lucide-react";
import { useState } from "react";

import { DraftsService } from "@/client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import useCustomToast from "@/hooks/useCustomToast";

interface PublishConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  targetName: string;
  isLoading: boolean;
  draftId: string;
  coverImageUrl?: string | null;
  onCoverUploaded: (url: string) => void;
}

export function PublishConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  targetName,
  isLoading,
  draftId,
  coverImageUrl,
  onCoverUploaded,
}: PublishConfirmDialogProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast();
  const [dragOver, setDragOver] = useState(false);

  const uploadCoverMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return DraftsService.uploadCover({
        id: draftId,
        formData: { file },
      });
    },
    onSuccess: (data) => {
      showSuccessToast("封面上传成功");
      onCoverUploaded(data.cover_image_url);
    },
    onError: (error: any) => {
      showErrorToast(error.body?.detail || "封面上传失败");
    },
  });

  const handleFileSelect = (file: File) => {
    if (!file.type.startsWith("image/")) {
      showErrorToast("请选择图片文件");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showErrorToast("图片大小不能超过 10MB");
      return;
    }
    uploadCoverMutation.mutate(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  const hasCover = !!coverImageUrl;
  const canPublish = hasCover && !isLoading && !uploadCoverMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>发布到微信公众号</DialogTitle>
          <DialogDescription>
            确认发布文章到 <strong>{targetName}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Article title */}
          <div className="text-sm">
            <span className="text-muted-foreground">文章标题：</span>
            <span className="font-medium">{title || "（未设置标题）"}</span>
          </div>

          {/* Cover image upload */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              封面图片 <span className="text-red-500">*</span>
            </label>
            <p className="text-xs text-muted-foreground">
              推荐尺寸 900×500 像素，支持 JPG、PNG、GIF 格式
            </p>

            {hasCover ? (
              <div className="relative w-full aspect-[9/5] rounded-lg overflow-hidden border">
                <img
                  src={coverImageUrl}
                  alt="封面预览"
                  className="w-full h-full object-cover"
                />
                <button
                  onClick={() => onCoverUploaded("")}
                  className="absolute top-2 right-2 p-1 bg-black/50 hover:bg-black/70 text-white rounded-full"
                  disabled={uploadCoverMutation.isPending || isLoading}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors duration-200
                  ${dragOver
                    ? "border-primary bg-primary/5"
                    : "border-muted-foreground/25 hover:border-muted-foreground/50"
                  }
                  ${uploadCoverMutation.isPending ? "opacity-50 pointer-events-none" : ""}
                `}
              >
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleInputChange}
                  className="hidden"
                  id="cover-upload"
                  disabled={uploadCoverMutation.isPending}
                />
                <label htmlFor="cover-upload" className="cursor-pointer">
                  <div className="flex flex-col items-center gap-2">
                    {uploadCoverMutation.isPending ? (
                      <>
                        <div className="h-10 w-10 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        <span className="text-sm text-muted-foreground">上传中...</span>
                      </>
                    ) : (
                      <>
                        <ImageIcon className="h-10 w-10 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          点击或拖拽上传封面图片
                        </span>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="mt-2"
                          onClick={(e) => {
                            e.preventDefault();
                            document.getElementById("cover-upload")?.click();
                          }}
                        >
                          <Upload className="h-4 w-4 mr-1" />
                          选择图片
                        </Button>
                      </>
                    )}
                  </div>
                </label>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            取消
          </Button>
          <Button
            onClick={onConfirm}
            disabled={!canPublish}
            className={!hasCover ? "opacity-50 cursor-not-allowed" : ""}
          >
            {isLoading ? "发布中..." : "确认发布"}
          </Button>
        </DialogFooter>

        {!hasCover && (
          <p className="text-xs text-red-500 text-right">
            请先上传封面图片
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/DraftEditor/PublishConfirmDialog.tsx
git commit -m "feat: add cover image upload to publish confirm dialog"
```

---

## Task 8: 修改草稿编辑页面传递封面状态

**Files:**
- Modify: `frontend/src/routes/_layout/drafts/$id.tsx`

- [ ] **Step 1: 修改状态定义**

在 `DraftEditorContent` 函数内，找到 state 定义区域，添加：

```typescript
  const [coverImageUrl, setCoverImageUrl] = useState(draft.cover_image_url || "")
```

- [ ] **Step 2: 同步 draft 数据变化**

在 `useEffect` 或其他适当位置添加（在 `draft` 数据加载后同步封面）：

```typescript
  // Sync cover image when draft data changes
  useEffect(() => {
    setCoverImageUrl(draft.cover_image_url || "")
  }, [draft.cover_image_url])
```

- [ ] **Step 3: 修改发布对话框调用**

找到 `PublishConfirmDialog` 的使用位置，修改为：

```typescript
      {/* Publish Confirm Dialog */}
      <PublishConfirmDialog
        open={publishOpen}
        onClose={() => setPublishOpen(false)}
        onConfirm={handlePublish}
        title={draft?.title || ""}
        targetName={systemConfig?.wechat_mp?.app_id || "微信公众号"}
        isLoading={isPublishing}
        draftId={id}
        coverImageUrl={coverImageUrl}
        onCoverUploaded={setCoverImageUrl}
      />
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/routes/_layout/drafts/$id.tsx
git commit -m "feat: integrate cover image upload in draft editor"
```

---

## Task 9: 安装依赖并测试

- [ ] **Step 1: 安装后端依赖**

```bash
cd backend
uv sync
```

- [ ] **Step 2: 重启服务**

```bash
docker compose restart backend
```

- [ ] **Step 3: 测试封面上传**

1. 打开草稿编辑器
2. 点击"发布到公众号"
3. 验证：未上传封面时发布按钮禁用
4. 上传一张封面图片
5. 验证：封面显示预览，发布按钮可用
6. 点击发布
7. 验证：文章成功发布到微信公众号

- [ ] **Step 4: 提交**

```bash
git commit -m "feat: complete wechat cover image upload feature"
```

---

## 验证清单

- [ ] Draft 模型有 `cover_image_url` 和 `thumb_media_id` 字段
- [ ] `POST /api/v1/drafts/{id}/upload-cover` 端点可用
- [ ] 图片自动裁剪到 900×500 像素
- [ ] 图片上传到七牛云获取永久 URL
- [ ] 图片上传到微信获取 `thumb_media_id`
- [ ] 发布时检查封面是否存在
- [ ] 前端发布对话框有封面上传UI
- [ ] 未上传封面时发布按钮禁用
- [ ] 封面预览正常显示
- [ ] 发布到微信公众号成功
