"""
examples/file_upload.py
=======================
Demonstrates file and image upload, including reading back image scales.

Run:
    python examples/file_upload.py
"""

from __future__ import annotations

from plone_client import PloneClient

import struct
import zlib


def _make_tiny_png() -> bytes:
    """Generate a minimal valid 1x1 red PNG entirely in memory."""

    def chunk(name: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + name + data
        return c + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"  # filter byte + RGB pixel
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def main() -> None:
    with PloneClient() as client:
        # ── Upload a PDF (bytes) ─────────────────────────────────────
        fake_pdf = b"%PDF-1.4 1 0 obj<</Type /Catalog>>endobj"
        file_obj = client.files.upload(
            "/",
            "sample.pdf",
            fake_pdf,
            content_type="application/pdf",
            title="Sample PDF",
        )
        pdf_path = file_obj["@id"].replace(client.config.base_url, "")
        print(f"Uploaded PDF: {pdf_path}")

        # ── Download it back ─────────────────────────────────────────
        raw = client.files.download(pdf_path, field="file")
        print(f"Downloaded {len(raw)} bytes")

        # ── Upload an image (bytes) ───────────────────────────────────
        img_data = _make_tiny_png()
        img_obj = client.files.upload(
            "/",
            "photo.png",
            img_data,
            content_type="image/png",
            title="Test Photo",
        )
        img_path = img_obj["@id"].replace(client.config.base_url, "")
        print(f"Uploaded image: {img_path}")

        # ── List image scales ─────────────────────────────────────────
        scales = client.files.image_scales(img_path)
        print(f"Available scales: {list(scales.keys())}")

        # ── Get a specific scale ───────────────────────────────────────
        if "preview" in scales:
            scale_info = client.files.image_scale(img_path, "image", "preview")
            print(
                f"Preview scale: {scale_info.get('width')}x{scale_info.get('height')}"
            )

        # ── Clean up ─────────────────────────────────────────────────
        client.content.delete(pdf_path)
        client.content.delete(img_path)
        print("Cleaned up")


if __name__ == "__main__":
    main()
