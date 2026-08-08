"""Image conversion helpers for multimodal requests."""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO

from PIL import Image

logger = logging.getLogger("brave_api.image")


def _convert_to_jpeg_sync(image_bytes: bytes, max_dimension: int, quality: int) -> bytes | None:
    """Re-encode *image_bytes* as a JPEG no larger than *max_dimension*."""
    try:
        with Image.open(BytesIO(image_bytes)) as opened:
            image: Image.Image = opened.convert("RGB")
            width, height = image.size
            if max(width, height) > max_dimension:
                if width >= height:
                    new_width = max_dimension
                    new_height = int(height * max_dimension / width)
                else:
                    new_height = max_dimension
                    new_width = int(width * max_dimension / height)
                image = image.resize(  # pyright: ignore[reportUnknownMemberType]
                    (new_width, new_height), Image.Resampling.LANCZOS
                )
            buffer = BytesIO()
            image.save(buffer, "JPEG", quality=quality)
            return buffer.getvalue()
    except Exception as exc:
        logger.warning("Failed to convert image to JPEG: %s", exc)
        return None


async def to_jpeg(image_bytes: bytes, max_dimension: int, quality: int) -> bytes | None:
    """Convert an image off the event loop via :func:`asyncio.to_thread`."""
    return await asyncio.to_thread(_convert_to_jpeg_sync, image_bytes, max_dimension, quality)


__all__ = ["to_jpeg"]
