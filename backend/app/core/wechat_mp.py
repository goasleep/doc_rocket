"""WeChat MP (Official Account) API client."""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.encryption import decrypt_value
from app.models.system_config import SystemConfig


class WeChatMPError(Exception):
    """Exception raised for WeChat MP API errors."""

    def __init__(self, message: str, errcode: int | None = None) -> None:
        super().__init__(message)
        self.errcode = errcode


class WeChatMPClient:
    """Client for WeChat MP (Official Account) API.

    Provides methods to interact with WeChat MP API including:
    - Access token management with caching
    - Account information retrieval
    - Image upload
    - Draft management
    - Publishing
    """

    BASE_URL = "https://api.weixin.qq.com"
    TOKEN_EXPIRES_IN = 7200  # 2 hours in seconds
    TOKEN_BUFFER_SECONDS = 300  # 5 minutes buffer before expiry

    def __init__(self, app_id: str, app_secret: str) -> None:
        """Initialize the WeChat MP client.

        Args:
            app_id: WeChat MP App ID
            app_secret: WeChat MP App Secret (plaintext)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._http_client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=30.0)

    @classmethod
    async def from_config(cls) -> "WeChatMPClient":
        """Create a WeChatMPClient from SystemConfig.

        Retrieves the WeChat MP configuration from the database,
        decrypts the app secret, and returns a configured client.

        Returns:
            WeChatMPClient: Configured client instance

        Raises:
            WeChatMPError: If WeChat MP is not configured or enabled
        """
        config = await SystemConfig.find_one()
        if not config:
            raise WeChatMPError("SystemConfig not found")

        wechat_config = config.wechat_mp
        if not wechat_config.enabled:
            raise WeChatMPError("WeChat MP is not enabled")

        if not wechat_config.app_id:
            raise WeChatMPError("WeChat MP App ID is not configured")

        if not wechat_config.app_secret_encrypted:
            raise WeChatMPError("WeChat MP App Secret is not configured")

        app_secret = decrypt_value(wechat_config.app_secret_encrypted)
        return cls(app_id=wechat_config.app_id, app_secret=app_secret)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.aclose()

    async def __aenter__(self) -> "WeChatMPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def get_access_token(self) -> str:
        """Get a valid access token, fetching a new one if necessary.

        The token is cached and only refreshed when it's about to expire
        (5 minutes before expiry).

        Returns:
            str: Valid access token

        Raises:
            WeChatMPError: If the token request fails
        """
        now = datetime.now(timezone.utc)

        # Check if we have a valid cached token
        if (
            self._access_token
            and self._token_expires_at
            and now
            < (self._token_expires_at - timedelta(seconds=self.TOKEN_BUFFER_SECONDS))
        ):
            return self._access_token

        # Fetch new token
        response = await self._http_client.get(
            "/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
            },
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if "errcode" in data and data["errcode"] != 0:
            raise WeChatMPError(
                f"Failed to get access token: {data.get('errmsg', 'Unknown error')}",
                errcode=data["errcode"],
            )

        self._access_token = str(data["access_token"])
        expires_in = int(data.get("expires_in", self.TOKEN_EXPIRES_IN))
        self._token_expires_at = now + timedelta(seconds=expires_in)

        return self._access_token

    async def validate_credentials(self) -> dict[str, Any]:
        """Validate the App ID and App Secret by fetching an access token.

        Returns:
            dict: Response containing access_token and expires_in if successful

        Raises:
            WeChatMPError: If credentials are invalid
        """
        response = await self._http_client.get(
            "/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
            },
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if "errcode" in data and data["errcode"] != 0:
            raise WeChatMPError(
                f"Invalid credentials: {data.get('errmsg', 'Unknown error')}",
                errcode=data["errcode"],
            )

        # Update cached token
        self._access_token = str(data["access_token"])
        expires_in = int(data.get("expires_in", self.TOKEN_EXPIRES_IN))
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )

        return data

    async def get_account_info(self, token: str | None = None) -> dict[str, Any]:
        """Get WeChat MP account information.

        Args:
            token: Optional access token. If not provided, will fetch one.

        Returns:
            dict: Account information

        Raises:
            WeChatMPError: If the request fails
        """
        access_token = token or await self.get_access_token()

        response = await self._http_client.get(
            "/cgi-bin/account/getaccountbasicinfo",
            params={"access_token": access_token},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if "errcode" in data and data["errcode"] != 0:
            raise WeChatMPError(
                f"Failed to get account info: {data.get('errmsg', 'Unknown error')}",
                errcode=data["errcode"],
            )

        return data

    async def upload_image(self, image_data: bytes, filename: str) -> str:
        """Upload an image to WeChat MP.

        Args:
            image_data: Raw image bytes
            filename: Name of the image file

        Returns:
            str: URL of the uploaded image

        Raises:
            WeChatMPError: If the upload fails
        """
        access_token = await self.get_access_token()

        files = {"media": (filename, image_data, "image/jpeg")}
        response = await self._http_client.post(
            "/cgi-bin/media/uploadimg",
            params={"access_token": access_token},
            files=files,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if "errcode" in data and data["errcode"] != 0:
            raise WeChatMPError(
                f"Failed to upload image: {data.get('errmsg', 'Unknown error')}",
                errcode=data["errcode"],
            )

        return str(data["url"])

    async def add_draft(
        self,
        title: str,
        content: str,
        author: str = "",
        digest: str = "",
        content_source_url: str = "",
        thumb_media_id: str = "",
        need_open_comment: int = 0,
        only_fans_can_comment: int = 0,
        pic_crop_235_1: str = "",
        pic_crop_1_1: str = "",
    ) -> str:
        """Add a new draft article.

        Args:
            title: Article title (up to 64 bytes)
            content: Article content (HTML format, up to 100,000 characters)
            author: Author name (up to 16 bytes)
            digest: Article summary (up to 120 bytes)
            content_source_url: Source URL for original content
            thumb_media_id: Thumbnail image media ID
            need_open_comment: Whether to enable comments (0=disable, 1=enable)
            only_fans_can_comment: Whether only fans can comment (0=no, 1=yes)
            pic_crop_235_1: Crop coordinates for 2.35:1 aspect ratio thumbnail
            pic_crop_1_1: Crop coordinates for 1:1 aspect ratio thumbnail

        Returns:
            str: Media ID of the created draft

        Raises:
            WeChatMPError: If the draft creation fails
        """
        access_token = await self.get_access_token()

        article = {
            "title": title,
            "content": content,
            "author": author,
            "digest": digest,
            "content_source_url": content_source_url,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": need_open_comment,
            "only_fans_can_comment": only_fans_can_comment,
        }

        # Add optional fields if provided
        if pic_crop_235_1:
            article["pic_crop_235_1"] = pic_crop_235_1
        if pic_crop_1_1:
            article["pic_crop_1_1"] = pic_crop_1_1

        payload = {"articles": [article]}

        response = await self._http_client.post(
            "/draft/add",
            params={"access_token": access_token},
            json=payload,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if "errcode" in data and data["errcode"] != 0:
            raise WeChatMPError(
                f"Failed to add draft: {data.get('errmsg', 'Unknown error')}",
                errcode=data["errcode"],
            )

        return str(data["media_id"])

    async def submit_publish(self, media_id: str) -> str:
        """Submit a draft for publishing.

        Args:
            media_id: Media ID of the draft to publish

        Returns:
            str: Publish ID for tracking the publish status

        Raises:
            WeChatMPError: If the publish submission fails
        """
        access_token = await self.get_access_token()

        payload = {"media_id": media_id}

        response = await self._http_client.post(
            "/freepublish/submit",
            params={"access_token": access_token},
            json=payload,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if "errcode" in data and data["errcode"] != 0:
            raise WeChatMPError(
                f"Failed to submit publish: {data.get('errmsg', 'Unknown error')}",
                errcode=data["errcode"],
            )

        return str(data["publish_id"])

    async def get_publish_status(self, publish_id: str) -> dict[str, Any]:
        """Get the status of a publish request.

        Args:
            publish_id: Publish ID returned by submit_publish

        Returns:
            dict: Publish status information including:
                - publish_id: The publish ID
                - publish_status: Status code (0=success, 1=publishing, 2=failed, 3=deleted)
                - article_id: Article ID (if published successfully)
                - article_detail: Article details including article_url
                - fail_idx: Array of failed article indices (if partially failed)

        Raises:
            WeChatMPError: If the status request fails
        """
        access_token = await self.get_access_token()

        payload = {"publish_id": publish_id}

        response = await self._http_client.post(
            "/freepublish/get",
            params={"access_token": access_token},
            json=payload,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if "errcode" in data and data["errcode"] != 0:
            raise WeChatMPError(
                f"Failed to get publish status: {data.get('errmsg', 'Unknown error')}",
                errcode=data["errcode"],
            )

        return data
