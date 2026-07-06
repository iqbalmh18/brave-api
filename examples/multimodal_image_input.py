"""
08 — Multimodal Image Input

Send an image alongside a text query (vision mode).
Brave converts images to JPEG internally before sending.
Three attachment methods are shown: argument, Path, and raw bytes.
"""

import asyncio
from pathlib import Path

from brave_api import BraveClient

SAMPLE_IMAGE = Path(__file__).parent / "image.png"


async def main() -> None:
    async with BraveClient() as client:

        # Method 1: pass the image directly to client.conversation()
        print("=== Method 1: image via client.conversation(image=...) ===")
        conv1 = await client.conversation(
            "apa yang ada di gambar ini?",
            image=SAMPLE_IMAGE,
            image_filename="image.png",
            image_mime="image/png",
        )
        result1 = await conv1.collect()
        print(result1.text[:400])

        # Method 2: attach_image() from a Path — MIME is inferred from extension
        print("\n=== Method 2: conv.attach_image(Path) ===")
        conv2 = await client.conversation("describe this image in detail")
        await conv2.attach_image(SAMPLE_IMAGE)
        result2 = await conv2.collect()
        print(result2.text[:400])

        # Method 3: attach_image() from raw bytes
        print("\n=== Method 3: conv.attach_image(bytes) ===")
        image_bytes = SAMPLE_IMAGE.read_bytes()
        conv3 = await client.conversation("apakah ada teks dalam gambar ini?")
        await conv3.attach_image(image_bytes, filename="foto.png", mime="image/png")
        result3 = await conv3.collect()
        print(result3.text[:400])

        print(f"\nhas_image: {conv3.has_image}")


asyncio.run(main())
