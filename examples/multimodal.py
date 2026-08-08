"""Vision mode: send an image alongside a text query.

The example generates a small test image with Pillow so it runs anywhere
with no fixture files. Images are accepted as bytes, paths, or paths-as-str,
and are converted to JPEG internally before streaming.
"""

import asyncio
from io import BytesIO

from PIL import Image, ImageDraw

from brave_api import BraveClient


def make_test_image() -> bytes:
    """Render a simple red-square / blue-circle test image."""
    image = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, 200, 200], fill="red")
    draw.ellipse([230, 60, 360, 190], fill="blue")
    draw.text(  # pyright: ignore[reportUnknownMemberType]
        (120, 230), "brave-api", fill="black"
    )
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


async def main() -> None:
    image_bytes = make_test_image()

    async with BraveClient() as client:
        result = await client.ask(
            "what shapes and text are in this image?",
            image=image_bytes,
        )

    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
