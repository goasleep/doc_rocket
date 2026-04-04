from unittest.mock import patch

from httpx import AsyncClient


@patch("app.api.routes.uploads.QiniuOSSClient.from_settings")
@patch("app.api.routes.uploads.QiniuOSSClient.upload_file")
async def test_upload_image_success(
    mock_upload, mock_from_settings, client: AsyncClient, superuser_token_headers: dict[str, str]
) -> None:
    mock_from_settings.return_value = mock_from_settings
    mock_upload.return_value = "https://cdn.example.com/test.jpg"

    data = b"fake-image-data"
    response = await client.post(
        "/api/v1/uploads/image",
        files={"file": ("test.jpg", data, "image/jpeg")},
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["url"] == "https://cdn.example.com/test.jpg"


async def test_upload_image_unsupported_type(
    client: AsyncClient, superuser_token_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/uploads/image",
        files={"file": ("test.txt", b"not-an-image", "text/plain")},
        headers=superuser_token_headers,
    )
    assert response.status_code == 400


async def test_upload_image_too_large(
    client: AsyncClient, superuser_token_headers: dict[str, str]
) -> None:
    big_data = b"x" * (6 * 1024 * 1024)
    response = await client.post(
        "/api/v1/uploads/image",
        files={"file": ("big.jpg", big_data, "image/jpeg")},
        headers=superuser_token_headers,
    )
    assert response.status_code == 413
