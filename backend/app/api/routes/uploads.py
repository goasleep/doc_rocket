from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.qiniu_oss import QiniuOSError, QiniuOSSClient

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

EXT_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


class ImageUploadResponse(BaseModel):
    url: str


@router.post("/image", response_model=ImageUploadResponse)
async def upload_image(
    _current_user: CurrentUser,
    file: UploadFile,
) -> Any:
    """Upload an image file to Qiniu OSS."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit",
        )

    ext = EXT_BY_CONTENT_TYPE.get(file.content_type, "bin")

    try:
        client = QiniuOSSClient.from_settings()
        key = client.generate_key(data, "uploads", ext)
        url = await client.upload_file(data, key)
    except QiniuOSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {"url": url}
