"""Qiniu OSS client for async file uploads."""
import asyncio
from typing import Self

from qiniu import Auth, put_data

from app.core.config import settings


class QiniuOSError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class QiniuOSSClient:
    def __init__(self, access_key: str, secret_key: str, bucket: str, domain: str) -> None:
        self.auth = Auth(access_key, secret_key)
        self.bucket = bucket
        self.domain = domain.rstrip("/")

    @classmethod
    def from_settings(cls) -> Self:
        if not settings.QINIU_ACCESS_KEY or not settings.QINIU_SECRET_KEY:
            raise QiniuOSError("Qiniu OSS credentials are not configured")
        if not settings.QINIU_BUCKET:
            raise QiniuOSError("Qiniu OSS bucket is not configured")
        if not settings.QINIU_DOMAIN:
            raise QiniuOSError("Qiniu OSS domain is not configured")
        return cls(
            access_key=settings.QINIU_ACCESS_KEY,
            secret_key=settings.QINIU_SECRET_KEY,
            bucket=settings.QINIU_BUCKET,
            domain=settings.QINIU_DOMAIN,
        )

    def _upload_sync(self, data: bytes, key: str) -> str:
        token = self.auth.upload_token(self.bucket, key)
        ret, info = put_data(token, key, data)
        if info.status_code != 200 or not ret:
            raise QiniuOSError(f"Qiniu upload failed: {info}")
        return f"{self.domain}/{key}"

    async def upload_file(self, data: bytes, filename: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._upload_sync, data, filename)
