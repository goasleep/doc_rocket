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
